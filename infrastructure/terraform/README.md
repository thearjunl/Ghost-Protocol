# GhostProtocol Terraform Infrastructure

This directory contains Terraform configuration to automatically provision all AWS infrastructure required for GhostProtocol.

## What Gets Created

- **CloudTrail**: Multi-region trail with S3 storage and log file validation
- **S3 Buckets**: 
  - CloudTrail logs bucket with lifecycle policies
  - Athena query results bucket
- **Athena**: 
  - Workgroup for query execution
  - Database for CloudTrail logs
  - Glue catalog table with partition projection
- **IAM**:
  - Application role with least-privilege permissions
  - Policy for IAM scanning, CloudTrail querying, and quarantine operations
  - EC2 instance profile

## Prerequisites

1. **Terraform** installed (>= 1.0)
   ```bash
   # macOS
   brew install terraform
   
   # Windows
   choco install terraform
   
   # Linux
   wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
   unzip terraform_1.6.0_linux_amd64.zip
   sudo mv terraform /usr/local/bin/
   ```

2. **AWS CLI** configured with credentials
   ```bash
   aws configure
   ```

3. **AWS Permissions**: Your AWS user/role needs permissions to create:
   - S3 buckets
   - CloudTrail trails
   - Athena workgroups and databases
   - Glue catalog tables
   - IAM roles and policies

## Quick Start

### 1. Configure Variables

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and update:
- `cloudtrail_bucket_name` - Must be globally unique
- `athena_results_bucket_name` - Must be globally unique
- Other variables as needed

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Review the Plan

```bash
terraform plan
```

Review the resources that will be created.

### 4. Apply Configuration

```bash
terraform apply
```

Type `yes` when prompted to create the resources.

### 5. Save Outputs

```bash
terraform output > outputs.txt
```

Use these outputs to configure your `.env` file:

```bash
# From Terraform outputs
ATHENA_DATABASE=<athena_database_name>
ATHENA_OUTPUT_BUCKET=s3://<athena_results_bucket_name>/results/
AWS_DEFAULT_REGION=<aws_region>
```

## Configuration Options

### Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `aws_region` | AWS region | `us-east-1` | No |
| `project_name` | Project name prefix | `ghostprotocol` | No |
| `environment` | Environment name | `prod` | No |
| `cloudtrail_bucket_name` | CloudTrail S3 bucket | - | Yes |
| `athena_results_bucket_name` | Athena results bucket | - | Yes |
| `enable_cloudtrail` | Create CloudTrail trail | `true` | No |
| `cloudtrail_retention_days` | Log retention period | `90` | No |

### Using Existing CloudTrail

If you already have CloudTrail configured:

```hcl
enable_cloudtrail = false
```

Then manually update the Glue table location to point to your existing CloudTrail bucket.

## Outputs

After applying, Terraform provides these outputs:

- `cloudtrail_bucket_name` - CloudTrail logs bucket
- `athena_results_bucket_name` - Athena results bucket
- `athena_workgroup_name` - Athena workgroup
- `athena_database_name` - Athena database name
- `app_role_arn` - IAM role ARN for the application
- `instance_profile_name` - EC2 instance profile name

## Cost Estimation

Approximate monthly costs (us-east-1):

- **CloudTrail**: $2.00 per 100,000 events
- **S3 Storage**: $0.023 per GB (first 50 TB)
- **Athena**: $5.00 per TB of data scanned
- **Glue Catalog**: Free for first million objects

Typical monthly cost: **$10-50** depending on usage.

## Maintenance

### Update Infrastructure

```bash
# Pull latest changes
git pull

# Review changes
terraform plan

# Apply updates
terraform apply
```

### Destroy Infrastructure

⚠️ **Warning**: This will delete all resources including CloudTrail logs!

```bash
terraform destroy
```

## Troubleshooting

### Bucket Name Already Exists

S3 bucket names must be globally unique. Update your `terraform.tfvars`:

```hcl
cloudtrail_bucket_name = "ghostprotocol-cloudtrail-prod-YOUR-UNIQUE-ID"
athena_results_bucket_name = "ghostprotocol-athena-results-prod-YOUR-UNIQUE-ID"
```

### Permission Denied

Ensure your AWS credentials have sufficient permissions. Required actions:
- `s3:CreateBucket`, `s3:PutBucketPolicy`
- `cloudtrail:CreateTrail`, `cloudtrail:StartLogging`
- `athena:CreateWorkGroup`, `athena:CreateDataCatalog`
- `glue:CreateDatabase`, `glue:CreateTable`
- `iam:CreateRole`, `iam:CreatePolicy`, `iam:AttachRolePolicy`

### State Lock Issues

If using remote state with locking and you encounter a lock error:

```bash
terraform force-unlock <LOCK_ID>
```

## Remote State (Recommended for Teams)

For production use, store Terraform state in S3 with DynamoDB locking:

```hcl
terraform {
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "ghostprotocol/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}
```

## Security Best Practices

1. **Never commit** `terraform.tfvars` with sensitive data
2. **Enable** S3 bucket encryption (enabled by default)
3. **Use** IAM roles instead of access keys when possible
4. **Enable** CloudTrail log file validation (enabled by default)
5. **Review** IAM policies regularly for least privilege

## Support

For issues or questions:
1. Check the [main README](../../README.md)
2. Review Terraform documentation: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
3. Open an issue on GitHub
