locals {
  project_root = abspath("${path.module}/../../..")
  package_path = abspath("${path.module}/${var.lambda_package_path}")

  syndicate_api = one([
    for resource in values(jsondecode(file("${local.project_root}/backend/restaurant-backend-app/deployment_resources.json"))) :
    resource if try(resource.resource_type, "") == "api_gateway"
  ])

  existing_routes = flatten([
    for path, definition in local.syndicate_api.resources : [
      for method, config in definition : {
        path               = path
        method             = lower(method)
        authorization_type = config.authorization_type
      } if method != "enable_cors" && path != "/guest/group/{groupReservationId}/sessions"
    ]
  ])

  additional_routes = [
    {
      path               = "/guest/groups/{groupReservationId}/sessions"
      method             = "get"
      authorization_type = "cognito_authorizer"
    },
    {
      path               = "/reservations/{reservationId}/guest-session-id"
      method             = "get"
      authorization_type = "cognito_authorizer"
    },
    {
      path               = "/group-reservations/{groupReservationId}/submit"
      method             = "post"
      authorization_type = "cognito_authorizer"
    }
  ]

  routes = concat(local.existing_routes, local.additional_routes)

  openapi_paths = {
    for path in distinct([for route in local.routes : route.path]) :
    path => merge(
      {
        for route in local.routes : route.method => {
          parameters = [
            for parameter in regexall("\\{([^}]+)\\}", route.path) : {
              name     = parameter[0]
              in       = "path"
              required = true
              type     = "string"
            }
          ]
          security = route.authorization_type == "cognito_authorizer" ? [{ CognitoAuthorizer = [] }] : []
          responses = {
            "200" = {
              description = "Lambda proxy response"
            }
          }
          "x-amazon-apigateway-integration" = {
            type                = "aws_proxy"
            httpMethod          = "POST"
            passthroughBehavior = "when_no_match"
            uri                 = aws_lambda_function.api.invoke_arn
          }
        } if route.path == path
      },
      {
        options = {
          consumes = ["application/json"]
          produces = ["application/json"]
          responses = {
            "200" = {
              description = "CORS preflight response"
              headers = {
                "Access-Control-Allow-Headers" = { type = "string" }
                "Access-Control-Allow-Methods" = { type = "string" }
                "Access-Control-Allow-Origin"  = { type = "string" }
              }
            }
          }
          "x-amazon-apigateway-integration" = {
            type                = "mock"
            passthroughBehavior = "when_no_match"
            requestTemplates    = { "application/json" = "{\"statusCode\": 200}" }
            responses = {
              default = {
                statusCode = "200"
                responseParameters = {
                  "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
                  "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,PUT,PATCH,DELETE,OPTIONS'"
                  "method.response.header.Access-Control-Allow-Origin"  = "'*'"
                }
              }
            }
          }
        }
      }
    )
  }

  api_body = {
    swagger = "2.0"
    info = {
      title   = var.api_name
      version = "1.0"
    }
    schemes = ["https"]
    paths   = local.openapi_paths
    securityDefinitions = {
      CognitoAuthorizer = {
        type                           = "apiKey"
        name                           = "Authorization"
        in                             = "header"
        "x-amazon-apigateway-authtype" = "cognito_user_pools"
        "x-amazon-apigateway-authorizer" = {
          type         = "cognito_user_pools"
          providerARNs = [var.cognito_user_pool_arn]
        }
      }
    }
  }
}

resource "aws_iam_role" "api_lambda" {
  name = "${var.api_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "api_lambda_logs" {
  role       = aws_iam_role.api_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "api_permissions" {
  count = length(keys(var.lambda_permissions)) == 0 ? 0 : 1

  name   = "${var.api_name}-lambda-app-permissions"
  role   = aws_iam_role.api_lambda.id
  policy = jsonencode(var.lambda_permissions)
}

resource "aws_lambda_function" "api" {
  function_name    = var.lambda_function_name
  role             = aws_iam_role.api_lambda.arn
  runtime          = "dotnet10"
  handler          = "APIHandler::APIHandler.Function::FunctionHandler"
  filename         = local.package_path
  source_code_hash = filebase64sha256(local.package_path)
  memory_size      = 128
  timeout          = 100

  environment {
    variables = merge(var.lambda_environment, {
      REGION = var.aws_region
    })
  }

  depends_on = [aws_iam_role_policy_attachment.api_lambda_logs]
  tags       = var.tags
}

resource "aws_api_gateway_rest_api" "api" {
  name              = var.api_name
  body              = jsonencode(local.api_body)
  put_rest_api_mode = "overwrite"
  tags              = var.tags
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*/*"
}

resource "aws_api_gateway_deployment" "api" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  triggers = {
    redeployment = sha1(jsonencode(local.api_body))
  }

  depends_on = [aws_lambda_permission.api_gateway]

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "api" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  deployment_id = aws_api_gateway_deployment.api.id
  stage_name    = var.api_stage_name
  tags          = var.tags
}
