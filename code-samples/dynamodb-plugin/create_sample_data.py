"""
Sample data generator for DynamoDB Plugin API for Amazon Q Business

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
"""

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
if __name__ == "__main__":
    print("Starting sample data creation...")
    create_sample_policies(50)  # Create 50 sample policies
    print("Sample data creation complete!")