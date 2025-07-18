# DynamoDB Plugin for Amazon Q Business

<!--
MIT No Attribution

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
-->

This sample demonstrates how to build a DynamoDB plugin for Amazon Q Business, allowing natural language queries against your DynamoDB data. This guide covers best practices learned during the development of a DynamoDB open schema API.

## Prerequisites

Before implementing this plugin, ensure you have:

1. **AWS Account**: Active AWS account with permissions to create:
   - DynamoDB tables
   - Lambda functions
   - API Gateway APIs
   - IAM roles
   - SQS queues

2. **Amazon Q Business**: Access to Amazon Q Business and permissions to create plugins

3. **Development Environment**:
   - AWS CLI installed and configured
   - Python 3.9 or later
   - Basic understanding of DynamoDB, Lambda, and API Gateway

4. **Sample Data**: This sample is designed for insurance policy data, but you can adapt it for your own data model

## Overview

The DynamoDB plugin enables Amazon Q Business to:
- Query data stored in DynamoDB tables
- Perform filtering and analytics on your data
- Execute CRUD operations through natural language requests
- Integrate DynamoDB data with other data sources

## Best Practices for DynamoDB Plugins

### 1. API Design

- **RESTful Endpoints**: Design clear, consistent endpoints following REST principles
- **Comprehensive Filtering**: Support rich query parameters for flexible data access
- **Pagination**: Always implement pagination to handle large datasets efficiently
- **Error Handling**: Provide meaningful error responses with appropriate HTTP status codes
- **OpenAPI Specification**: Document your API thoroughly with OpenAPI 3.0

### 2. DynamoDB Table Design

- **Partition Key Selection**: Choose partition keys that distribute data evenly
- **Sort Key Usage**: Leverage sort keys for range queries and filtering
- **Secondary Indexes**: Create GSIs/LSIs for common query patterns
- **Item Size Management**: Keep items under 400KB and consider denormalization
- **Attribute Naming**: Use consistent naming conventions for attributes

### 3. Lambda Implementation

- **Connection Pooling**: Reuse DynamoDB connections across invocations
- **Error Handling**: Implement robust error handling with appropriate status codes
- **Input Validation**: Validate all input parameters before processing
- **Logging**: Include detailed logging for troubleshooting
- **Performance Optimization**: Minimize cold starts and optimize query patterns

### 4. Security Best Practices

- **IAM Roles**: Follow least privilege principle for all roles
- **API Gateway Authorization**: Implement proper authorization mechanisms
- **Input Sanitization**: Validate and sanitize all user inputs
- **Encryption**: Enable encryption at rest and in transit
- **Monitoring**: Set up CloudWatch alarms for security events

### 5. Q Business Integration

- **OpenAPI Schema**: Provide a detailed OpenAPI schema for Q Business
- **Natural Language Mapping**: Design your API to support natural language queries
- **Response Formatting**: Structure responses to be easily interpreted by Q Business
- **Cross-System Correlation**: Enable Q Business to correlate data across systems
- **Testing Scenarios**: Develop comprehensive test scenarios for Q Business queries

## Project Structure

```
├── cloudformation-template.yaml    # Infrastructure as Code
├── lambda.py                       # Lambda function code
├── dynamodb-plugin-openapi.yaml  # OpenAPI specification for Q Business
├── README.md                       # This guide
└── .gitignore                      # Git ignore patterns
```

## Implementation Steps

### 1. Set Up DynamoDB Table

The CloudFormation template (`cloudformation-template.yaml`) included in this sample creates a DynamoDB table with the necessary structure and Global Secondary Indexes:

```yaml
Resources:
  PolicyDataTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub 'policy-data-${Environment}'
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: policy_id
          AttributeType: S
        - AttributeName: state
          AttributeType: S
        - AttributeName: policy_status
          AttributeType: S
      KeySchema:
        - AttributeName: policy_id
          KeyType: HASH
      GlobalSecondaryIndexes:
        - IndexName: StateIndex
          KeySchema:
            - AttributeName: state
              KeyType: HASH
          Projection:
            ProjectionType: ALL
        - IndexName: PolicyStatusIndex
          KeySchema:
            - AttributeName: policy_status
              KeyType: HASH
          Projection:
            ProjectionType: ALL
```

### 1.1 Populate the DynamoDB Table with Sample Data

After deploying the CloudFormation stack, you'll need to populate the DynamoDB table with sample data. Here's a Python script to create sample insurance policy data:

```python
import boto3
import uuid
import random
from datetime import datetime, timedelta
import json

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = 'policy-data-dev'  # Replace with your actual table name from CloudFormation output
table = dynamodb.Table(table_name)

# Sample data parameters
states = ['California', 'Illinois']
policy_types = ['Liability', 'Collision', 'Comprehensive', 'Full Coverage']
vehicle_types = ['Motorcycle', 'SUV', 'Sedan', 'Truck']
policy_statuses = ['Active', 'Lapsed', 'Cancelled']
risk_ratings = ['Low', 'Medium', 'High']
compliance_values = ['TRUE', 'FALSE']

# Generate random date within range
def random_date(start_date, end_date):
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randrange(days_between)
    return (start_date + timedelta(days=random_days)).strftime('%Y-%m-%d')

# Create sample policies
def create_sample_policies(count=50):
    for i in range(count):
        policy = {
            'policy_id': str(uuid.uuid4()),
            'customer_id': str(uuid.uuid4()),
            'agent_id': str(uuid.uuid4()),
            'policy_type': random.choice(policy_types),
            'vehicle_type': random.choice(vehicle_types),
            'policy_status': random.choice(policy_statuses),
            'premium_amount': f"${random.randint(500, 3000)}",
            'deductible': f"${random.choice([250, 500, 1000, 2000])}",
            'coverage_limit': f"${random.randint(25000, 250000)}",
            'state': random.choice(states),
            'risk_rating': random.choice(risk_ratings),
            'start_date': random_date(datetime.now() - timedelta(days=365*2), datetime.now()),
            'end_date': random_date(datetime.now(), datetime.now() + timedelta(days=365*2)),
            'last_updated': datetime.now().strftime('%Y-%m-%d'),
            'notes': f"Sample policy {i+1}",
            'is_compliant': random.choice(compliance_values),
            'product_version': f"v{random.randint(1, 3)}.{random.randint(0, 9)}"
        }
        
        # Write to DynamoDB
        table.put_item(Item=policy)
        print(f"Created policy {i+1}/{count}")

# Run the function to create sample data
create_sample_policies(50)  # Create 50 sample policies
print("Sample data creation complete!")
```

Save this script as `create_sample_data.py` and run it after deploying the CloudFormation stack:

```bash
python create_sample_data.py
```

Remember to update the `table_name` variable with the actual table name from your CloudFormation stack output.

### 2. Create Lambda Function

```python
import json
import boto3
import logging
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('policy-data')

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    logger.info(f"Event: {json.dumps(event)}")
    
    # Get HTTP method and path
    http_method = event.get('httpMethod', '')
    path = event.get('path', '')
    
    # Route request based on method and path
    if http_method == 'GET':
        if path == '/items':
            return get_items(event)
        elif path.startswith('/items/') and len(path.split('/')) == 3:
            item_id = path.split('/')[-1]
            return get_item(item_id)
    elif http_method == 'POST' and path == '/items':
        return create_item(event)
    # Add other routes as needed
    
    # Default response for unhandled routes
    return {
        'statusCode': 404,
        'body': json.dumps({'error': 'Not Found'})
    }

def get_items(event):
    # Extract query parameters for filtering
    query_params = event.get('queryStringParameters', {}) or {}
    
    # Build filter expression based on query parameters
    filter_expression = None
    for key, value in query_params.items():
        if key not in ['limit', 'offset']:  # Skip pagination params
            if filter_expression is None:
                filter_expression = Attr(key).eq(value)
            else:
                filter_expression = filter_expression & Attr(key).eq(value)
    
    # Handle pagination
    limit = int(query_params.get('limit', 100))
    offset = int(query_params.get('offset', 0))
    
    # Execute query
    try:
        if filter_expression:
            response = table.scan(
                FilterExpression=filter_expression,
                Limit=limit
            )
        else:
            response = table.scan(Limit=limit)
        
        # Apply offset manually (DynamoDB doesn't support offset directly)
        items = response.get('Items', [])[offset:offset+limit]
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'items': items,
                'count': len(items),
                'total': response.get('Count', 0)
            }, cls=DecimalEncoder)
        }
    except Exception as e:
        logger.error(f"Error getting items: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

# Implement other handler functions (get_item, create_item, etc.)
```

### 3. Set Up API Gateway

```yaml
  ApiGateway:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: DynamoDBPluginAPI
      Description: API for DynamoDB Plugin for Q Business
      EndpointConfiguration:
        Types:
          - REGIONAL

  # Define resources and methods
  ApiGatewayRootResource:
    Type: AWS::ApiGateway::Resource
    Properties:
      RestApiId: !Ref ApiGateway
      ParentId: !GetAtt ApiGateway.RootResourceId
      PathPart: items
```

### 4. Create OpenAPI Specification

```yaml
openapi: 3.0.0
info:
  title: DynamoDB Plugin API
  version: 1.0.0
  description: API for accessing DynamoDB data from Amazon Q Business
paths:
  /items:
    get:
      summary: List items with filtering
      parameters:
        - name: state
          in: query
          schema:
            type: string
        # Add other filter parameters
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  items:
                    type: array
                    items:
                      $ref: '#/components/schemas/Item'
                  count:
                    type: integer
                  total:
                    type: integer
    post:
      summary: Create new item
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Item'
      responses:
        '201':
          description: Item created
```

### 5. Configure Q Business Integration

1. Deploy your CloudFormation stack
2. Get the API Gateway URL from stack outputs
3. In the Q Business console:
   - Create a new plugin
   - Upload your OpenAPI specification
   - Configure the API endpoint
   - Test with sample queries

## Advanced Query Capabilities

Your DynamoDB plugin should support these query patterns:

### Filtering Parameters

- **Exact Match**: `state=California`
- **Range Queries**: `premium_min=1000&premium_max=2000`
- **Date Ranges**: `start_date_from=2024-01-01&start_date_to=2024-12-31`
- **Boolean Filters**: `is_compliant=true`
- **Pagination**: `limit=10&offset=0`

### Advanced Search Endpoint

Implement a `/items/search` endpoint for complex queries:

```json
{
  "filters": {
    "policy_types": ["Liability", "Collision"],
    "compliance": false,
    "premium_range": [1000, 2000]
  },
  "sort": {"field": "end_date", "order": "asc"},
  "pagination": {"limit": 100, "offset": 0}
}
```

### Statistics Endpoint

Implement a `/items/stats` endpoint for aggregations:

```json
{
  "total_items": 400,
  "by_state": {
    "California": 220,
    "Illinois": 180
  },
  "by_status": {
    "Active": 300,
    "Lapsed": 80,
    "Cancelled": 20
  }
}
```

## Testing Your Plugin

### Direct API Testing

```bash
# Test basic filtering
curl "https://your-api-url/prod/items?state=California&policy_status=Active"

# Test advanced search
curl -X POST "https://your-api-url/prod/items/search" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "policy_types": ["Liability"],
      "compliance": false
    },
    "sort": {"field": "end_date", "order": "asc"}
  }'
```

### Q Business Query Testing

Test your plugin with natural language queries:

```
"How many active policies do we have in California?"
"Show me all high-risk policies that are currently lapsed"
"What's the average premium for SUV policies?"
```

## Monitoring and Optimization

- **CloudWatch Logs**: Monitor Lambda and API Gateway logs
- **DynamoDB Metrics**: Track read/write capacity utilization
- **Performance Tuning**: Optimize query patterns and indexes
- **Cost Optimization**: Use on-demand capacity for unpredictable workloads

## Deployment Guide

This sample includes everything you need to deploy the DynamoDB plugin. Follow these steps:

### 1. Clone the Repository

Clone this repository to your local machine:

```bash
git clone <repository-url>
cd amazon-q-business-samples/code-samples/dynamodb-plugin
```

### 2. Deploy the CloudFormation Stack

Use the provided deployment script to create all necessary AWS resources:

```bash
# Make the script executable
chmod +x deploy.sh

# Deploy with default parameters
./deploy.sh

# Or deploy with custom parameters
./deploy.sh my-stack-name prod Q-Insurance-Comp-Analyzer us-east-1
```

The script will:
- Create a Lambda deployment package
- Deploy the CloudFormation stack with all resources
- Update the Lambda function code
- Display the API endpoint URL

### 3. Populate the DynamoDB Table

Use the provided Python script to create sample data:

```bash
# Update the table name in the script with your actual table name
# from the CloudFormation output
nano create_sample_data.py

# Run the script
python create_sample_data.py
```

### 4. Test the API

Test the API using curl or any API testing tool:

```bash
# Test the root endpoint
curl https://your-api-url/prod/

# Test listing items
curl https://your-api-url/prod/items

# Test filtering
curl "https://your-api-url/prod/items?state=California&policy_status=Active"
```

### 5. Configure Amazon Q Business Plugin

1. In the Amazon Q Business console, create a new plugin
2. Upload the `dynamodb-plugin-openapi.yaml` file as the OpenAPI schema
3. Configure the API endpoint using the URL from the deployment output
4. Test the plugin with natural language queries

## Customizing for Your Data Model

This sample is designed for insurance policy data, but you can adapt it for your own data model:

1. Modify the DynamoDB table structure in `cloudformation-template.yaml`
2. Update the data model in `dynamodb-plugin-openapi.yaml`
3. Adjust the Lambda function in `lambda.py` to handle your data model
4. Create a custom script to populate your DynamoDB table with relevant sample data

## Conclusion

By following these best practices, you can build a robust DynamoDB plugin for Amazon Q Business that enables natural language querying of your data. This approach provides a powerful way to make your DynamoDB data accessible through conversational interfaces.

---

**Ready for Amazon Q Business Integration! 🚀**