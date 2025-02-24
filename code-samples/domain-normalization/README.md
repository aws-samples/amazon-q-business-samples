# Domain Normalization Function

## Overview
This Lambda function manages domain normalization for Amazon Q Business by synchronizing user identities between ServiceNow and Amazon Q Business. It helps organizations maintain consistent user identification when their ServiceNow domain differs from their corporate Identity Provider (IdP) domain. This function can be extended to any other Amazon Q Business compatible connector, by adding an identity retrieval function and the appropriate configuration for that connector to gain authorized access. In addition to this, you can also adjust single users only by passing in a different input.

## Features
- Extracts role IDs from Amazon Q Business sync job logs
- Queries ServiceNow API to retrieve user information
- Updates existing user aliases in Amazon Q Business
- Creates new users with normalized domains when they don't exist
- Handles domain transformation between local and global domain patterns
- Comprehensive error handling and logging


## Prerequisites

1. AWS Lambda execution role with appropriate permissions
2. Access to Amazon Q Business application (and appropriately configured)
3. ServiceNow instance with API access
4. AWS Secrets Manager secret containing ServiceNow credentials
5. AWS CLI installed and configured
6. Python 3.9 or later

## Deployment Steps

1. Clone the repository via [sparse-checkout method](/sparse-checkout.md)
    - For sparse-checkout path, use `code-samples/domain-normalization`

2. Create a zip file containing the Lambda function:
   ```bash
   zip deployment-package.zip domain-normalization.py
    ```
3. Reference the parameters file named parameters.json, and update the parameter values to match your deployment:
```json
[
    {
      "ParameterKey": "ApplicationId",
      "ParameterValue": "your-q-application-id"
    },
    {
      "ParameterKey": "DataSourceId",
      "ParameterValue": "your-datasource-id"
    },
    {
      "ParameterKey": "IndexId",
      "ParameterValue": "your-index-id"
    },
    {
      "ParameterKey": "ServiceNowHost",
      "ParameterValue": "your-instance.service-now.com"
    },
    {
      "ParameterKey": "ServiceNowUsername",
      "ParameterValue": "your-api-username"
    },
    {
      "ParameterKey": "ServiceNowSecretName",
      "ParameterValue": "your-secret-name"
    },
    {
      "ParameterKey": "GlobalDomain",
      "ParameterValue": "global.domain"
    },
    {
      "ParameterKey": "S3BucketName",
      "ParameterValue": "domain-normalization-bucket"
    }
  ]
```
4. Create new S3 bucket, and upload the deployment-package.zip file:
```bash
# Create S3 bucket (replace with your desired bucket name)
aws s3 mb s3://domain-normalization-bucket

# Upload deployment package
aws s3 cp deployment-package.zip s3://domain-normalization-bucket/deployment-package.zip
```
5. Create a new secret for the ServiceNow credentials
```bash
aws secretsmanager create-secret \
    --name your-secret-name \
    --description "ServiceNow credentials for Q Business domain normalization" \
    --secret-string "{\"username\":\"your-api-username\",\"password\":\"your-servicenow-password\"}"
```
Note: Before deploying, please check:

1. You have created the S3Bucket and uploaded the python code, and S3 bucket name is unique across all AWS accounts
2. You have adjusted the placeholders for the environment variables and parameters required in the yaml file 
You have created the ServiceNow credentials, within AWS Secrets Manager
3. Ensure your AWS account has the necessary permissions to create IAM roles and Lambda functions
4. Make sure you're creating the S3 bucket in the same region as your CloudFormation stack

The template creates all necessary IAM permissions and sets up CloudWatch Logs for monitoring the function's execution.


5. Deploy the CloudFormation stack:
```bash
aws cloudformation create-stack \
  --stack-name domain-normalization \
  --template-body file://template.yaml \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_IAM
```

## Required IAM Policy (created automatically - reference only)
The Lambda function requires an execution role with the following policy:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams",
                "logs:GetLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:${AWS_REGION}:${ACCOUNT_ID}:log-group:/aws/qbusiness/${APPLICATION_ID}:*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "qbusiness:UpdateUser",
                "qbusiness:CreateUser",
                "qbusiness:ListDataSourceSyncJobs"
            ],
            "Resource": [
                "arn:aws:qbusiness:${AWS_REGION}:${ACCOUNT_ID}:application/${APPLICATION_ID}"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": [
                "arn:aws:secretsmanager:${AWS_REGION}:${ACCOUNT_ID}:secret:${SECRET_NAME}"
            ]
        }
    ]
}
```

## Environment Variables (reference)
```bash
 - APPLICATION_ID         # Amazon Q Business application ID
 - DATA_SOURCE_ID         # Amazon Q Business data source ID
 - INDEX_ID               # Amazon Q Business index ID
 - SERVICENOW_HOST        # ServiceNow instance hostname (no trailing slash or http prefix)
 - SERVICENOW_USERNAME    # ServiceNow API username
 - SERVICENOW_SECRET_NAME # AWS Secrets Manager secret name for ServiceNow password
 - GLOBAL_DOMAIN          # Corporate IdP domain (e.g.,corporate.com)
```
## Function Flow

 1. Retrieves the latest sync job ID from Amazon Q Business
 2. Finds associated CloudWatch log streams
 3. Extracts role IDs from log messages
 4. Queries ServiceNow for user information
 5. Updates or creates user aliases in Amazon Q Business
 6. Transforms email domains during the process

## Input Event Structures
This project has the ability to perform the alias update in bulk by obtaining user information from ServiceNow, or you can pass in single users only for maintence. 

For single users, you can utilise the following input example:
```json
{
    "user_email" : "user@amazon.dev"
}
```

For bulk change on a single ServiceNow datasource sync, please use the following:
```json
{
    "sync_job_run_id": "optional-sync-job-id"
}
```

If no sync_job_run_id is provided, the function will use the latest sync job. If this doesn't align to a ServiceNow connector, the function will ignore any updates to be made.

## Invoking the Function

You can invoke the Lambda function using the AWS CLI, AWS Console, or programmatically. The function supports three invocation patterns:

Using AWS CLI:
   ```bash
   # Process a specific user
   aws lambda invoke \
     --function-name [your function name] \
     --payload '{"user_email": "user@amazon.dev"}' \
     response.json

   # Invoke with specific sync job ID
   aws lambda invoke \
     --function-name [your function name] \
     --payload '{"sync_job_run_id": "your-sync-job-id"}' \
     response.json

   # Invoke with no specific sync job (uses latest)
   aws lambda invoke \
     --function-name [your function name] \
     --payload '{}' \
     response.json

   # View the response
   cat response.json
```

## Response structure (example)
```json
{
    "statusCode": 200,
    "body": {
        "sync_job_run_id": "job-id",
        "log_stream_name": "stream-name",
        "role_ids": ["role-id-1", "role-id-2"],
        "role_count": 2,
        "member_count_update": 10,
        "members": ["user@corporate.com","user1@corporate.com"],
        "configuration": {
            "applicationId": "app-id",
            "dataSourceId": "ds-id",
            "indexId": "index-id"
        }
    }
}
```

## Error Handling
 - Returns 400 status code for validation errors
 - Returns 404 status code when resources are not found
 - Returns 500 status code for unexpected errors
 - Comprehensive logging for troubleshooting

## Dependencies
 - boto3
 - Python 3.x
 - AWS SDK
 - SSL support for ServiceNow API calls

## Security Considerations
 - Uses AWS Secrets Manager for credential management
 - Implements SSL verification for API calls
 - Requires appropriate IAM permissions
 - Validates all input parameters

## Logging
 - Detailed CloudWatch logging
 - Tracks processing progress
 - Records successful updates and errors
 - Includes timing information for operations

## Best Practices
 - Implements pagination for log processing
 - Handles API rate limiting
 - Includes comprehensive error handling
 - Uses environment variables for configuration
 - Implements proper exception handling

## Variable Placeholders
Replace the following placeholders in the IAM policy:
 - ${AWS_REGION}: AWS region where the resources are deployed
 - ${ACCOUNT_ID}: Your AWS account ID
 - ${APPLICATION_ID}: Your Amazon Q Business application ID
 - ${SECRET_NAME}: Name of the secret in AWS Secrets Manager

## Cleanup Steps

To avoid ongoing charges and clean up resources created by this project, follow these steps in order:

1. Delete the CloudFormation stack:
```bash
# Delete the stack and wait for completion
aws cloudformation delete-stack \
 --stack-name domain-normalization

# Optional: Wait for delete to complete
aws cloudformation wait stack-delete-complete \
  --stack-name domain-normalization
```

2. Empty and delete the S3 bucket:
 
- Empty the bucket first
```bash
aws s3 rm s3://domain-normalization-bucket --recursive
```
 - Delete the bucket
 ```bash
aws s3 rb s3://domain-normalization-bucket
```
3. Delete the ServiceNow credentials from Secrets Manager:
```bash
aws secretsmanager delete-secret \
  --secret-id your-secret-name \
  --force-delete-without-recovery
```
4. Verify cleanup:
```bash
# Verify stack deletion
aws cloudformation list-stacks \
  --query 'StackSummaries[?StackName==`domain-normalization`]'

# Verify bucket deletion
aws s3 ls | grep domain-normalization-bucket

# Verify secret deletion
aws secretsmanager list-secrets \
  --query 'SecretList[?Name==`your-secret-name`]'
```

Note:
 - Make sure to replace your-secret-name with your actual secret name
 - The cleanup process will remove all resources created by this project
 - Some resources might take a few minutes to delete completely
 - If the stack deletion fails, check the CloudFormation console for error messages
 - Ensure you have the necessary permissions to delete all resources
 - If you're using the resources in other projects, verify before deletion

## License:
This library is licensed under the MIT-0 License. See the [LICENSE](/LICENSE) file. 