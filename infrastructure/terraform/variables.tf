variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "ghostprotocol"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "cloudtrail_bucket_name" {
  description = "S3 bucket name for CloudTrail logs (must be globally unique)"
  type        = string
}

variable "athena_results_bucket_name" {
  description = "S3 bucket name for Athena query results (must be globally unique)"
  type        = string
}

variable "enable_cloudtrail" {
  description = "Whether to create a new CloudTrail trail"
  type        = bool
  default     = true
}

variable "cloudtrail_retention_days" {
  description = "Number of days to retain CloudTrail logs"
  type        = number
  default     = 90
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "GhostProtocol"
    ManagedBy   = "Terraform"
    Purpose     = "NHI Security Auditing"
  }
}
