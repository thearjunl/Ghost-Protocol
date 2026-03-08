"""AI-powered IAM Policy Analyzer using LangChain + Ollama.

Connects to a local Ollama instance running llama3 to compare an IAM role's
current permissions against its actual CloudTrail usage. Generates a
least-privilege replacement policy and a numeric risk score (1-100).
"""

import json
import logging
from typing import Any

from langchain_community.llms import Ollama
from langchain.prompts import ChatPromptTemplate

from config import OLLAMA_BASE_URL

logger = logging.getLogger("ghostprotocol.analyzer")

SYSTEM_PROMPT = """\
You are an IAM Policy Expert specialising in the Principle of Least Privilege.

You will receive:
1. **Current Policy Actions** — a JSON list of IAM actions the role is currently allowed to perform.
2. **Used Actions** — a JSON list of IAM actions the role actually invoked in the last 30 days.

Your tasks:
A. Identify every action in the Current Policy that was NOT used (over-privileged permissions).
B. Produce a NEW, strictly scoped IAM policy JSON document that contains ONLY the Used Actions. \
   Use the standard AWS IAM policy format with Version, Statement, Effect, Action, and Resource fields. \
   Set Resource to "*" unless a more specific scope is obvious.
C. Calculate a **Risk Score** from 1 to 100:
   - 1  = perfectly scoped (zero unused permissions)
   - 100 = wildcard admin with near-zero actual usage
   The score should be roughly: (unused_count / total_allowed_count) * 100, \
   but weight wildcard actions (e.g. "*") and admin actions higher.

Respond ONLY with valid JSON in this exact shape (no markdown fences):
{{
  "risk_score": <int 1-100>,
  "unused_actions": [<list of unused action strings>],
  "recommended_policy": {{<valid IAM policy JSON>}},
  "summary": "<one-paragraph explanation of the risk and recommendation>"
}}
"""

USER_TEMPLATE = """\
Current Policy Actions:
{current_policy}

Used Actions:
{used_actions}
"""


def generate_least_privilege_policy(
    current_policy: list[str] | dict,
    used_actions: list[str],
) -> dict[str, Any]:
    """Analyse the gap between allowed and used IAM actions via Ollama/llama3.

    Args:
        current_policy: List of allowed IAM action strings, or a policy dict.
        used_actions:   List of IAM action strings actually observed in CloudTrail.

    Returns:
        Dict with keys: risk_score, unused_actions, recommended_policy, summary.
    """
    # Normalise input
    if isinstance(current_policy, dict):
        # Extract action strings from a policy document
        actions = []
        for stmt in current_policy.get("Statement", []):
            act = stmt.get("Action", [])
            if isinstance(act, str):
                act = [act]
            actions.extend(act)
        current_policy = actions

    llm = Ollama(
        model="llama3",
        base_url=OLLAMA_BASE_URL,
        temperature=0.1,   # low temp for deterministic policy output
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_TEMPLATE),
    ])

    chain = prompt | llm

    logger.info(
        "Invoking Ollama analysis — %d allowed actions, %d used actions",
        len(current_policy),
        len(used_actions),
    )

    raw_response = chain.invoke({
        "current_policy": json.dumps(current_policy, indent=2),
        "used_actions": json.dumps(used_actions, indent=2),
    })

    # Parse the LLM JSON response
    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError:
        logger.error("LLM returned invalid JSON — attempting extraction")
        # Try to find JSON block in the response
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1
        if start != -1 and end > start:
            result = json.loads(raw_response[start:end])
        else:
            raise ValueError("Could not parse LLM response as JSON")

    # Validate / clamp risk score
    score = int(result.get("risk_score", 50))
    result["risk_score"] = max(1, min(100, score))

    logger.info("Analysis complete — risk score: %d", result["risk_score"])
    return result
