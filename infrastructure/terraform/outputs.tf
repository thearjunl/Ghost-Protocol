output "cloudtrail_bucket_name" {
  description = "Name of the CloudTrail S3 bucket"
  value       = var.enable_cloudtrail ? aws_s3_bucket.cloudtrail[0].id : null
}

output "cloudtrail_bucket_arn" {
  description = "ARN of the CloudTrail S3 bucket"
  value       = var.enable_cloudtrail ? aws_s3_bucket.cloudtrail[0].arn : null
}

output "athena_results_bucket_name" {
  description = "Name of the Athena results S3 bucket"
  value       = aws_s3_bucket.athena_results.id
}

output "athena_results_bucket_arn" {
  description = "ARN of the Athena results S3 bucket"
  value       = aws_s3_bucket.athena_results.arn
}

output "athena_workgroup_name" {
  description = "Name of the Athena workgroup"
  value       = aws_athena_workgroup.ghostprotocol.name
}

output "athena_database_name" {
  description = "Name of the Athena database"
  value       = aws_athena_database.cloudtrail.name
}

output "app_role_arn" {
  description = "ARN of the GhostProtocol application IAM role"
  value       = aws_iam_role.ghostprotocol_app.arn
}

output "app_role_name" {
  description = "Name of the GhostProtocol application IAM role"
  value       = aws_iam_role.ghostprotocol_app.name
}

output "instance_profile_name" {
  description = "Name of the EC2 instance profile"
  value       = aws_iam_instance_profile.ghostprotocol_app.name
}

output "instance_profile_arn" {
  description = "ARN of the EC2 instance profile"
  value       = aws_iam_instance_profile.ghostprotocol_app.arn
}

output "cloudtrail_trail_arn" {
  description = "ARN of the CloudTrail trail"
  value       = var.enable_cloudtrail ? aws_cloudtrail.main[0].arn : null
}
