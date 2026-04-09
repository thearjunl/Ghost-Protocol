"""Health check module for GhostProtocol dependencies.

Provides comprehensive health checks for:
- Supabase database connectivity
- AWS credentials and permissions
- Ollama/LLM availability
- Athena query capability
"""

import logging
from typing import Dict, Any
from datetime import datetime

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from supabase import Client

from config import (
    SUPABASE_URL,
    SUPABASE_KEY,
    AWS_DEFAULT_REGION,
    OLLAMA_BASE_URL,
    ATHENA_DATABASE,
    ATHENA_OUTPUT_BUCKET,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
)
from database import get_client as get_supabase_client

logger = logging.getLogger("ghostprotocol.health")


def check_supabase() -> Dict[str, Any]:
    """Check Supabase database connectivity."""
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return {
                "status": "unhealthy",
                "message": "Supabase credentials not configured",
                "details": None
            }
        
        client = get_supabase_client()
        
        # Try a simple query
        result = client.table('identities').select('arn').limit(1).execute()
        
        return {
            "status": "healthy",
            "message": "Supabase connection successful",
            "details": {
                "url": SUPABASE_URL,
                "table_accessible": True
            }
        }
    except Exception as e:
        logger.error(f"Supabase health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Supabase connection failed: {str(e)}",
            "details": None
        }


def check_aws_credentials() -> Dict[str, Any]:
    """Check AWS credentials and basic permissions."""
    try:
        sts = boto3.client('sts', region_name=AWS_DEFAULT_REGION)
        identity = sts.get_caller_identity()
        
        return {
            "status": "healthy",
            "message": "AWS credentials valid",
            "details": {
                "account_id": identity['Account'],
                "arn": identity['Arn'],
                "user_id": identity['UserId'],
                "region": AWS_DEFAULT_REGION
            }
        }
    except NoCredentialsError:
        return {
            "status": "unhealthy",
            "message": "AWS credentials not found",
            "details": None
        }
    except ClientError as e:
        return {
            "status": "unhealthy",
            "message": f"AWS credentials invalid: {e}",
            "details": None
        }
    except Exception as e:
        logger.error(f"AWS credentials check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"AWS check failed: {str(e)}",
            "details": None
        }


def check_iam_permissions() -> Dict[str, Any]:
    """Check IAM read permissions."""
    try:
        iam = boto3.client('iam', region_name=AWS_DEFAULT_REGION)
        
        # Try to list roles (limited to 1)
        response = iam.list_roles(MaxItems=1)
        
        return {
            "status": "healthy",
            "message": "IAM read permissions verified",
            "details": {
                "can_list_roles": True
            }
        }
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        return {
            "status": "unhealthy",
            "message": f"IAM permissions insufficient: {error_code}",
            "details": {
                "error_code": error_code,
                "required_permissions": ["iam:ListRoles", "iam:GetRole"]
            }
        }
    except Exception as e:
        logger.error(f"IAM permissions check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"IAM check failed: {str(e)}",
            "details": None
        }


def check_athena() -> Dict[str, Any]:
    """Check Athena configuration and connectivity."""
    try:
        if not ATHENA_OUTPUT_BUCKET:
            return {
                "status": "unhealthy",
                "message": "Athena output bucket not configured",
                "details": None
            }
        
        athena = boto3.client('athena', region_name=AWS_DEFAULT_REGION)
        
        # Try a simple query to validate setup
        query = f"SHOW DATABASES"
        
        response = athena.start_query_execution(
            QueryString=query,
            ResultConfiguration={'OutputLocation': ATHENA_OUTPUT_BUCKET}
        )
        
        execution_id = response['QueryExecutionId']
        
        # Check query status
        status_response = athena.get_query_execution(QueryExecutionId=execution_id)
        state = status_response['QueryExecution']['Status']['State']
        
        return {
            "status": "healthy",
            "message": "Athena connectivity verified",
            "details": {
                "database": ATHENA_DATABASE,
                "output_bucket": ATHENA_OUTPUT_BUCKET,
                "test_query_state": state
            }
        }
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        return {
            "status": "unhealthy",
            "message": f"Athena check failed: {error_code}",
            "details": {
                "error_code": error_code,
                "required_permissions": ["athena:StartQueryExecution", "athena:GetQueryExecution"]
            }
        }
    except Exception as e:
        logger.error(f"Athena health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Athena check failed: {str(e)}",
            "details": None
        }


def check_llm() -> Dict[str, Any]:
    """Check LLM provider availability."""
    try:
        if LLM_PROVIDER == "ollama":
            import httpx
            
            if not OLLAMA_BASE_URL:
                return {
                    "status": "unhealthy",
                    "message": "Ollama base URL not configured",
                    "details": None
                }
            
            # Check if Ollama is running
            response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                
                return {
                    "status": "healthy",
                    "message": "Ollama is running",
                    "details": {
                        "provider": "ollama",
                        "base_url": OLLAMA_BASE_URL,
                        "available_models": model_names,
                        "llama3_available": any('llama3' in m for m in model_names)
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": f"Ollama returned status {response.status_code}",
                    "details": None
                }
                
        elif LLM_PROVIDER == "openai":
            if not OPENAI_API_KEY:
                return {
                    "status": "unhealthy",
                    "message": "OpenAI API key not configured",
                    "details": None
                }
            
            return {
                "status": "healthy",
                "message": "OpenAI configured",
                "details": {
                    "provider": "openai",
                    "api_key_set": True
                }
            }
            
        elif LLM_PROVIDER == "anthropic":
            if not ANTHROPIC_API_KEY:
                return {
                    "status": "unhealthy",
                    "message": "Anthropic API key not configured",
                    "details": None
                }
            
            return {
                "status": "healthy",
                "message": "Anthropic configured",
                "details": {
                    "provider": "anthropic",
                    "api_key_set": True
                }
            }
        else:
            return {
                "status": "unhealthy",
                "message": f"Unknown LLM provider: {LLM_PROVIDER}",
                "details": None
            }
            
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"LLM check failed: {str(e)}",
            "details": None
        }


def get_comprehensive_health() -> Dict[str, Any]:
    """Run all health checks and return comprehensive status."""
    checks = {
        "supabase": check_supabase(),
        "aws_credentials": check_aws_credentials(),
        "iam_permissions": check_iam_permissions(),
        "athena": check_athena(),
        "llm": check_llm(),
    }
    
    # Determine overall status
    all_healthy = all(check["status"] == "healthy" for check in checks.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": checks
    }
