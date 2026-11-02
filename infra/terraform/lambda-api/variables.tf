variable "aws_region" {
  description = "AWS region for the Lambda and API Gateway."
  type        = string
  default     = "us-west-2"
}

variable "lambda_package_path" {
  description = "Path to the API handler deployment ZIP, relative to this module or absolute."
  type        = string
  default     = "../../../backend/restaurant-backend-app/artifacts/api-handler.zip"
}

variable "cognito_user_pool_arn" {
  description = "ARN of the Cognito user pool used by protected API routes."
  type        = string
}

variable "lambda_environment" {
  description = "Environment variables required by the API handler and its existing AWS resources."
  type        = map(string)
  default     = {}
}

variable "lambda_permissions" {
  description = "Optional least-privilege IAM policy document for the app's existing DynamoDB, S3, SQS, and Cognito resources."
  type        = any
  default     = {}
}

variable "lambda_function_name" {
  description = "Lambda function name. Must not already be managed by AWS Syndicate."
  type        = string
  default     = "api-handler"
}

variable "api_name" {
  description = "Name of the REST API."
  type        = string
  default     = "restaurant-backend-api"
}

variable "api_stage_name" {
  description = "Deployed API Gateway stage name."
  type        = string
  default     = "develop"
}

variable "tags" {
  description = "Tags applied to supported resources."
  type        = map(string)
  default     = {}
}
