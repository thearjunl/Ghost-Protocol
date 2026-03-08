"""GhostProtocol configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

AWS_DEFAULT_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

ATHENA_DATABASE: str = os.getenv("ATHENA_DATABASE", "cloudtrail_logs")
ATHENA_OUTPUT_BUCKET: str = os.getenv("ATHENA_OUTPUT_BUCKET", "")

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
