# Terraform Lambda and API Gateway

This standalone Terraform module packages the existing .NET API handler as an
AWS Lambda function and imports the routes declared in
`backend/restaurant-backend-app/deployment_resources.json` into an API Gateway
REST API. It also adds the three group pre-order routes implemented for the
workshop assignment and configures Cognito authorization according to the
Syndicate route definitions.

The module uses local Terraform state and does not create an S3 state bucket.
It does not run Syndicate and must not manage a Lambda function that Syndicate
already owns with the same name.

## Prerequisites

- AWS CLI authenticated to the intended account.
- Terraform 1.10 or later.
- .NET 10 SDK.
- The app's existing Cognito user pool and its dependencies (DynamoDB tables,
  S3 buckets, and SQS queue) already provisioned.

This module provisions only the API handler Lambda, its execution role and
API Gateway. Provide the Cognito pool ARN, the handler's environment variables,
and a least-privilege IAM policy for the existing application resources. The
Lambda will not be functional if those dependencies or permissions are absent.

## Build the Lambda package

From the repository root:

```bash
dotnet tool install --global Amazon.Lambda.Tools
mkdir -p backend/restaurant-backend-app/artifacts
cd backend/restaurant-backend-app/dnapp/lambdas/api-handler
dotnet lambda package --configuration Release --framework net10.0 \
  --output-package ../../../artifacts/api-handler.zip
cd ../../../../..
```

The package path can be overridden with the Terraform variable
`lambda_package_path`.

## Configure and inspect Terraform

Create a local `terraform.tfvars` file in this directory (it is git-ignored):

```hcl
cognito_user_pool_arn = "arn:aws:cognito-idp:us-west-2:123456789012:userpool/us-west-2_example"

lambda_environment = {
  REGION                              = "us-west-2"
  COGNITO_USER_POOL_ID                = "us-west-2_example"
  COGNITO_USER_POOL_CLIENT_ID         = "exampleclientid"
  reports_queue_name                  = "restaurant-reports-queue"
  OrderIndexReservationId             = "GSI_ReservationId"
  notificationsTable                  = "Notifications"
  FEEDBACK_TABLE_NAME                 = "Feedback"
  locationsTable                      = "Locations"
  WaiterListTableName                 = "Waiters"
  tablesTable                         = "Tables"
  dishesTable                         = "Dishes"
  reservationsTable                   = "Reservations"
  reportsTable                        = "Reports"
  reportsHistoryTable                 = "ReportsHistory"
  profileImagesTable                  = "ProfileImages"
  notificationsUserIdIndex            = "UserIdIndex"
  reservationsCustomerIdGlobalIndex   = "GSI_UserId"
  reservationsWaiterIdGlobalIndex     = "GSI_WaiterId"
  reservationsTableGlobalIndex        = "GSI_ByTableId"
  waitersGlobalIndex                  = "locationId-index"
  imagesBucketName                    = "restaurant-backend-dev-images-123456789012"
  profileImagesBucketName             = "restaurant-backend-dev-profile-images-123456789012"
  ordersTable                         = "Orders"
  feedbackGlobalIndex                 = "locationId-createdAt-index"
  groupReservationsTable              = "GroupReservations"
  guestSessionTable                   = "GuestSessions"
  tableLocationIdIndex                = "locationId-tableNumber-index"
}
```

Replace example Cognito and account values with resources in your account.
Set `lambda_permissions` to an IAM policy granting only the operations this
app needs on those resources. Do not copy broad wildcard permissions into a
production account.

These commands initialize and validate the local module and show the proposed
changes. `terraform plan` does not create resources, but may make read-only AWS
API calls and can fail if the account's organization policies deny access:

```bash
cd infra/terraform/lambda-api
terraform init
terraform fmt -check
terraform validate
terraform plan
```

Do not run `terraform apply` unless you have explicitly decided to deploy and
reviewed any possible AWS charges. Lambda/API Gateway requests, CloudWatch Logs,
and the app's data services can incur charges.

## Outputs

- `api_base_url`: deployed REST API stage URL.
- `lambda_function_name`: API handler function name.
- `api_gateway_id`: REST API ID.
