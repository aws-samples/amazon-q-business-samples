#!/bin/bash
# Deployment script for DynamoDB Plugin API

# MIT No Attribution
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

set -e

# Default values
STACK_NAME="dynamodb-plugin-stack"
ENVIRONMENT="dev"
Q_BUSINESS_APP_NAME="Q-Insurance-Comp-Analyzer"
REGION="us-east-1"

# Parse command line arguments
if [ $# -ge 1 ]; then
    STACK_NAME=$1
fi

if [ $# -ge 2 ]; then
    ENVIRONMENT=$2
fi

if [ $# -ge 3 ]; then
    Q_BUSINESS_APP_NAME=$3
fi

if [ $# -ge 4 ]; then
    REGION=$4
fi

echo "Deploying DynamoDB Plugin API with the following parameters:"
echo "Stack Name: $STACK_NAME"
echo "Environment: $ENVIRONMENT"
echo "Q Business App Name: $Q_BUSINESS_APP_NAME"
echo "Region: $REGION"

# Create deployment package for Lambda
echo "Creating Lambda deployment package..."
zip -r lambda.zip lambda.py

# Deploy CloudFormation stack
echo "Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file cloudformation-template.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        Environment=$ENVIRONMENT \
        QBusinessAppName=$Q_BUSINESS_APP_NAME \
        ApiStageName=prod \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $REGION

# Get Lambda function name from stack outputs
LAMBDA_FUNCTION=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='LambdaFunction'].OutputValue" \
    --output text \
    --region $REGION)

# Update Lambda function code
echo "Updating Lambda function code..."
aws lambda update-function-code \
    --function-name $LAMBDA_FUNCTION \
    --zip-file fileb://lambda.zip \
    --region $REGION

# Clean up
echo "Cleaning up..."
rm lambda.zip

# Get API endpoint from stack outputs
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
    --output text \
    --region $REGION)

echo ""
echo "Deployment completed successfully!"
echo "API Endpoint: $API_ENDPOINT"
echo ""
echo "To test the API, run:"
echo "curl $API_ENDPOINT/"
echo ""
echo "To configure Amazon Q Business, use the following URL:"
echo "$API_ENDPOINT"
echo ""
echo "And upload the dynamodb-plugin-openapi.yaml file as the OpenAPI schema."