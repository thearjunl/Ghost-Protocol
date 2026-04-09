# IAM role for GhostProtocol application
resource "aws_iam_role" "ghostprotocol_app" {
  name = "${var.project_name}-app-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${var.project_name}-app-role-${var.environment}"
  })
}

# IAM policy for GhostProtocol application
resource "aws_iam_policy" "ghostprotocol_app" {
  name        = "${var.project_name}-app-policy-${var.environment}"
  description = "Policy for GhostProtocol application to scan IAM and query CloudTrail"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "IAMReadAccess"
        Effect = "Allow"
        Action = [
          "iam:ListRoles",
          "iam:GetRole",
          "iam:ListAttachedRolePolicies",
          "iam:GetPolicy",
          "iam:GetPolicyVersion",
          "iam:ListRolePolicies",
          "iam:GetRolePolicy"
        ]
        Resource = "*"
      },
      {
        Sid    = "IAMQuarantineAccess"
        Effect = "Allow"
        Action = [
          "iam:CreatePolicy",
          "iam:PutRolePermissionsBoundary",
          "iam:DeleteRolePermissionsBoundary"
        ]
        Resource = "*"
      },
      {
        Sid    = "AthenaQueryAccess"
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StopQueryExecution",
          "athena:GetWorkGroup"
        ]
        Resource = [
          "arn:aws:athena:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:workgroup/${aws_athena_workgroup.ghostprotocol.name}"
        ]
      },
      {
        Sid    = "GlueReadAccess"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetPartitions"
        ]
        Resource = [
          "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:catalog",
          "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:database/${aws_athena_database.cloudtrail.name}",
          "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/${aws_athena_database.cloudtrail.name}/*"
        ]
      },
      {
        Sid    = "S3AthenaResultsAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.athena_results.arn,
          "${aws_s3_bucket.athena_results.arn}/*"
        ]
      },
      {
        Sid    = "S3CloudTrailReadAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = var.enable_cloudtrail ? [
          aws_s3_bucket.cloudtrail[0].arn,
          "${aws_s3_bucket.cloudtrail[0].arn}/*"
        ] : []
      },
      {
        Sid    = "STSAccess"
        Effect = "Allow"
        Action = [
          "sts:GetCallerIdentity"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${var.project_name}-app-policy-${var.environment}"
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "ghostprotocol_app" {
  role       = aws_iam_role.ghostprotocol_app.name
  policy_arn = aws_iam_policy.ghostprotocol_app.arn
}

# Instance profile for EC2 (if deploying on EC2)
resource "aws_iam_instance_profile" "ghostprotocol_app" {
  name = "${var.project_name}-app-profile-${var.environment}"
  role = aws_iam_role.ghostprotocol_app.name

  tags = merge(var.tags, {
    Name = "${var.project_name}-app-profile-${var.environment}"
  })
}
