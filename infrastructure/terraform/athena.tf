# S3 bucket for Athena query results
resource "aws_s3_bucket" "athena_results" {
  bucket = var.athena_results_bucket_name

  tags = merge(var.tags, {
    Name = "${var.project_name}-athena-results-${var.environment}"
  })
}

# Block public access to Athena results bucket
resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy for Athena results
resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  rule {
    id     = "delete-old-results"
    status = "Enabled"

    expiration {
      days = 30
    }
  }
}

# Athena workgroup
resource "aws_athena_workgroup" "ghostprotocol" {
  name = "${var.project_name}-workgroup-${var.environment}"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-workgroup-${var.environment}"
  })
}

# Athena database for CloudTrail
resource "aws_athena_database" "cloudtrail" {
  name   = "${var.project_name}_cloudtrail_${var.environment}"
  bucket = aws_s3_bucket.athena_results.bucket

  comment = "Database for querying CloudTrail logs"
}

# Glue catalog table for CloudTrail logs
resource "aws_glue_catalog_table" "cloudtrail_logs" {
  count         = var.enable_cloudtrail ? 1 : 0
  name          = "cloudtrail_logs"
  database_name = aws_athena_database.cloudtrail.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL              = "TRUE"
    "projection.enabled"  = "true"
    "projection.timestamp.type" = "date"
    "projection.timestamp.range" = "2020/01/01,NOW"
    "projection.timestamp.format" = "yyyy/MM/dd"
    "projection.timestamp.interval" = "1"
    "projection.timestamp.interval.unit" = "DAYS"
    "storage.location.template" = "s3://${var.cloudtrail_bucket_name}/AWSLogs/${data.aws_caller_identity.current.account_id}/CloudTrail/$${AWS::Region}/$${timestamp}"
  }

  storage_descriptor {
    location      = "s3://${var.cloudtrail_bucket_name}/AWSLogs/${data.aws_caller_identity.current.account_id}/CloudTrail/${data.aws_region.current.name}/"
    input_format  = "com.amazon.emr.cloudtrail.CloudTrailInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hive.hcatalog.data.JsonSerDe"

      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "eventversion"
      type = "string"
    }

    columns {
      name = "useridentity"
      type = "struct<type:string,principalid:string,arn:string,accountid:string,invokedby:string,accesskeyid:string,userName:string,sessioncontext:struct<attributes:struct<mfaauthenticated:string,creationdate:string>,sessionissuer:struct<type:string,principalId:string,arn:string,accountId:string,userName:string>>>"
    }

    columns {
      name = "eventtime"
      type = "string"
    }

    columns {
      name = "eventsource"
      type = "string"
    }

    columns {
      name = "eventname"
      type = "string"
    }

    columns {
      name = "awsregion"
      type = "string"
    }

    columns {
      name = "sourceipaddress"
      type = "string"
    }

    columns {
      name = "useragent"
      type = "string"
    }

    columns {
      name = "errorcode"
      type = "string"
    }

    columns {
      name = "errormessage"
      type = "string"
    }

    columns {
      name = "requestparameters"
      type = "string"
    }

    columns {
      name = "responseelements"
      type = "string"
    }

    columns {
      name = "additionaleventdata"
      type = "string"
    }

    columns {
      name = "requestid"
      type = "string"
    }

    columns {
      name = "eventid"
      type = "string"
    }

    columns {
      name = "resources"
      type = "array<struct<arn:string,accountid:string,type:string>>"
    }

    columns {
      name = "eventtype"
      type = "string"
    }

    columns {
      name = "apiversion"
      type = "string"
    }

    columns {
      name = "readonly"
      type = "string"
    }

    columns {
      name = "recipientaccountid"
      type = "string"
    }

    columns {
      name = "serviceeventdetails"
      type = "string"
    }

    columns {
      name = "sharedeventid"
      type = "string"
    }

    columns {
      name = "vpcendpointid"
      type = "string"
    }
  }

  partition_keys {
    name = "timestamp"
    type = "string"
  }
}
