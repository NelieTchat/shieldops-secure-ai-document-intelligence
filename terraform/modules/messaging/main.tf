locals {
  s3_bucket_name = element(split(":", var.s3_bucket_arn), 5)
}

# --- Dead-letter queue ---
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name}-${var.environment}-dlq"
  kms_master_key_id         = var.kms_key_id
  message_retention_seconds = var.message_retention_seconds
  tags                      = var.tags
}

# --- Main queue, consumed by the Ingestion Service ---
resource "aws_sqs_queue" "this" {
  name                       = "${var.name}-${var.environment}"
  kms_master_key_id          = var.kms_key_id
  visibility_timeout_seconds = var.visibility_timeout_seconds
  message_retention_seconds  = var.message_retention_seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = var.tags
}

# --- Allow EventBridge to publish to the queue ---
data "aws_iam_policy_document" "queue_policy" {
  statement {
    sid       = "AllowEventBridgeSend"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.this.arn]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.s3_upload.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "this" {
  queue_url = aws_sqs_queue.this.id
  policy    = data.aws_iam_policy_document.queue_policy.json
}

# --- EventBridge rule: catch S3 upload events for this bucket ---
resource "aws_cloudwatch_event_rule" "s3_upload" {
  name        = "${var.name}-${var.environment}-s3-upload"
  description = "Matches new object uploads to the ShieldOps documents bucket (ADR 0007)"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [local.s3_bucket_name]
      }
    }
  })

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "sqs" {
  rule      = aws_cloudwatch_event_rule.s3_upload.name
  target_id = "shieldops-ingestion-queue"
  arn       = aws_sqs_queue.this.arn
}