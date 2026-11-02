output "api_base_url" {
  description = "Base URL of the deployed API Gateway stage."
  value       = aws_api_gateway_stage.api.invoke_url
}

output "lambda_function_name" {
  description = "Name of the deployed API handler Lambda function."
  value       = aws_lambda_function.api.function_name
}

output "api_gateway_id" {
  description = "ID of the REST API."
  value       = aws_api_gateway_rest_api.api.id
}
