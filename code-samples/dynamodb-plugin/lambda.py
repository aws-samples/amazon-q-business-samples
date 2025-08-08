"""
DynamoDB Plugin API for Amazon Q Business
This Lambda function implements a RESTful API for managing insurance policy data in DynamoDB,
designed to work seamlessly with Amazon Q Business for natural language queries.

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

import json
import boto3
import os
import logging
import time
import re
import uuid
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS X-Ray if available
try:
    from aws_xray_sdk.core import patch_all
    patch_all()
    logger.info("AWS X-Ray initialized")
except ImportError:
    logger.info("AWS X-Ray SDK not available")

# Initialize DynamoDB with connection pooling
region = os.environ.get("AWS_REGION", "us-east-1")
dynamodb_client = boto3.client('dynamodb', region_name=region, config=boto3.config.Config(
    max_pool_connections=100
))
dynamodb = boto3.resource('dynamodb', region_name=region, config=boto3.config.Config(
    max_pool_connections=100
))
table_name = os.environ.get("TABLE_NAME", "policy-data")
table = dynamodb.Table(table_name)

# Simple in-memory cache with TTL
cache = {}
cache_ttl = {}
DEFAULT_CACHE_TTL = 60  # seconds#
 Constants for validation
VALID_STATES = ['California', 'Illinois']
VALID_POLICY_TYPES = ['Liability', 'Collision', 'Comprehensive', 'Full Coverage']
VALID_VEHICLE_TYPES = ['Motorcycle', 'SUV', 'Sedan', 'Truck']
VALID_POLICY_STATUSES = ['Active', 'Lapsed', 'Cancelled']
VALID_RISK_RATINGS = ['Low', 'Medium', 'High']
VALID_COMPLIANCE_VALUES = ['TRUE', 'FALSE']
UUID_PATTERN = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
VERSION_PATTERN = r'^v\d+\.\d+$'
DATE_PATTERN = r'^\d{4}-\d{2}-\d{2}$'

###################
# Cache Functions #
###################

def get_cached_item(key, ttl=DEFAULT_CACHE_TTL):
    """Get item from cache if it exists and hasn't expired"""
    now = time.time()
    if key in cache and cache_ttl.get(key, 0) > now:
        logger.info(f"Cache hit for key: {key}")
        return cache[key]
    logger.info(f"Cache miss for key: {key}")
    return None

def set_cached_item(key, value, ttl=DEFAULT_CACHE_TTL):
    """Store item in cache with expiration time"""
    cache[key] = value
    cache_ttl[key] = time.time() + ttl
    logger.info(f"Cached item with key: {key}, TTL: {ttl}s")

def invalidate_cache(key=None):
    """Invalidate specific cache key or entire cache"""
    if key:
        if key in cache:
            del cache[key]
            del cache_ttl[key]
            logger.info(f"Invalidated cache for key: {key}")
    else:
        cache.clear()
        cache_ttl.clear()
        logger.info("Invalidated entire cache")

###################
# Helper Classes  #
###################

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert DynamoDB Decimal types to JSON"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)#
##################
# Error Handling  #
###################

def create_error_response(status_code, error_message, error_code, headers, path=""):
    """Create standardized error response matching OpenAPI schema"""
    error_id = str(uuid.uuid4())
    logger.error(f"Error ID: {error_id}, Code: {error_code}, Message: {error_message}, Path: {path}")
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps({
            "error": error_message,
            "code": error_code,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "path": path,
            "error_id": error_id
        })
    }

###################
# Input Validation #
###################

def validate_uuid(value, field_name):
    """Validate UUID format"""
    if not re.match(UUID_PATTERN, value, re.I):
        raise ValueError(f"Invalid {field_name} format. Must be a valid UUID")
    return True

def validate_enum(value, valid_values, field_name):
    """Validate enum value"""
    if value not in valid_values:
        valid_str = ", ".join(valid_values)
        raise ValueError(f"Invalid {field_name} value: {value}. Must be one of: {valid_str}")
    return True

def validate_date(value, field_name):
    """Validate date format (YYYY-MM-DD)"""
    if not re.match(DATE_PATTERN, value):
        raise ValueError(f"Invalid {field_name} format. Use YYYY-MM-DD format")
    return True

def validate_number(value, field_name, min_value=None, max_value=None):
    """Validate numeric value with optional range"""
    try:
        num_value = float(value)
        if min_value is not None and num_value < min_value:
            raise ValueError(f"{field_name} must be >= {min_value}")
        if max_value is not None and num_value > max_value:
            raise ValueError(f"{field_name} must be <= {max_value}")
        return True
    except (ValueError, TypeError):
        raise ValueError(f"Invalid {field_name} value: {value}. Must be a number")

def validate_version(value, field_name):
    """Validate version format (v#.#)"""
    if not re.match(VERSION_PATTERN, value):
        raise ValueError(f"Invalid {field_name} format: {value}. Must match pattern v#.#")
    return True

def sanitize_input(value):
    """Sanitize string input to prevent injection"""
    if isinstance(value, str):
        # Remove any potentially harmful characters
        return re.sub(r'[^\w\s\-\.,;:@#$%^&*()[\]{}|/<>\'\"=+!?]', '', value)
    return value########
###########
# Main Handler    #
###################

def lambda_handler(event, context):
    """Main Lambda handler function matching OpenAPI schema"""
    # Log request details (sanitized)
    request_id = context.aws_request_id if context else str(uuid.uuid4())
    logger.info(f"Request ID: {request_id}, Method: {event.get('httpMethod')}, Path: {event.get('path')}")
    
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, x-api-key',
        'X-Request-ID': request_id,
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-XSS-Protection': '1; mode=block',
        'Cache-Control': 'no-store'
    }
    
    try:
        # Validate API key if required
        if os.environ.get("REQUIRE_API_KEY", "false").lower() == "true":
            if not validate_api_key(event):
                return create_error_response(401, "Unauthorized - Invalid or missing API key", "UNAUTHORIZED", headers)
        
        http_method = event.get("httpMethod")
        path = event.get("path", "")
        path_parameters = event.get("pathParameters") or {}
        query_parameters = event.get("queryStringParameters") or {}
        
        # Handle OPTIONS requests for CORS
        if http_method == "OPTIONS":
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({"message": "CORS preflight"})
            }
        
        # Route requests based on path and method - matching OpenAPI paths exactly
        if path == "/" and http_method == "GET":
            return handle_root_endpoint(headers)
        elif path == "/items" and http_method == "GET":
            return handle_list_items(query_parameters, headers)
        elif path == "/items" and http_method == "POST":
            return handle_create_item(event.get('body'), headers, path)
        elif path.startswith("/items/") and not path.endswith("/search") and not path.endswith("/stats"):
            policy_id = path_parameters.get('policy_id') or path.split('/')[-1]
            if http_method == "GET":
                return handle_get_item(policy_id, headers, path)
            elif http_method == "PUT":
                return handle_update_item(policy_id, event.get('body'), headers, path)
            elif http_method == "DELETE":
                return handle_delete_item(policy_id, headers, path)
        elif path == "/items/search" and http_method == "POST":
            return handle_search_items(event.get('body'), headers, path)
        elif path == "/items/stats" and http_method == "GET":
            return handle_get_stats(query_parameters, headers, path)
        else:
            return create_error_response(404, "Endpoint not found", "NOT_FOUND", headers, path)
            
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return create_error_response(500, f"Internal server error", "INTERNAL_ERROR", headers, path)

def validate_api_key(event):
    """Validate API key from request headers"""
    headers = event.get("headers") or {}
    api_key = headers.get("x-api-key")
    
    if not api_key:
        return False
    
    # Get valid API keys from environment variable (comma-separated)
    valid_keys = os.environ.get("VALID_API_KEYS", "").split(",")
    
    return api_key in valid_keys#
##################
# Endpoint Handlers #
###################

def handle_root_endpoint(headers):
    """Handle GET / - API information matching OpenAPI schema"""
    # Check cache first
    cache_key = "root_endpoint"
    cached_response = get_cached_item(cache_key)
    if cached_response:
        return cached_response
    
    response = {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            "message": "DynamoDB Plugin API",
            "version": "1.0.0",
            "endpoints": [
                "GET /",
                "GET /items",
                "POST /items", 
                "GET /items/{policy_id}",
                "PUT /items/{policy_id}",
                "DELETE /items/{policy_id}",
                "POST /items/search",
                "GET /items/stats"
            ]
        })
    }
    
    # Cache response for 1 hour (static content)
    set_cached_item(cache_key, response, 3600)
    return response

def handle_list_items(query_params, headers):
    """Handle GET /items with filtering - matches OpenAPI response schema"""
    try:
        # Generate cache key based on query parameters
        cache_key = f"list_items:{json.dumps(query_params, sort_keys=True)}"
        cached_response = get_cached_item(cache_key)
        if cached_response:
            return cached_response
        
        # Apply filters using GSIs where possible
        filtered_items = query_items_with_indexes(query_params)
        
        # Apply pagination as defined in OpenAPI
        limit = min(int(query_params.get('limit', 100)), 1000)  # Max 1000 as per schema
        offset = max(int(query_params.get('offset', 0)), 0)
        
        total_count = len(filtered_items)
        paginated_items = filtered_items[offset:offset + limit]
        has_more = (offset + limit) < total_count
        
        # Return response matching OpenAPI schema exactly
        response = {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                "items": paginated_items,
                "total_count": total_count,
                "filtered_count": len(paginated_items),
                "has_more": has_more
            }, cls=DecimalEncoder)
        }
        
        # Cache response for 30 seconds (adjustable based on data volatility)
        set_cached_item(cache_key, response, 30)
        return response
        
    except ValueError as e:
        return create_error_response(400, f"Invalid parameter value: {str(e)}", "VALIDATION_ERROR", headers)
    except Exception as e:
        logger.error(f"Error in handle_list_items: {str(e)}", exc_info=True)
        return create_error_response(500, f"Failed to retrieve items", "SCAN_ERROR", headers)def que
ry_items_with_indexes(query_params):
    """Query items using GSIs where possible, falling back to scan with filters"""
    try:
        # Check if we can use GSI for state
        if 'state' in query_params and not any(k for k in query_params.keys() if k != 'state' and k not in ['limit', 'offset']):
            state = query_params['state']
            validate_enum(state, VALID_STATES, 'state')
            
            # Use StateIndex GSI if it exists
            try:
                response = table.query(
                    IndexName='StateIndex',
                    KeyConditionExpression=Key('state').eq(state)
                )
                return response.get('Items', [])
            except ClientError as e:
                # If GSI doesn't exist, log and fall back to scan
                logger.warning(f"StateIndex GSI not found, falling back to scan: {str(e)}")
        
        # Check if we can use GSI for policy_status
        if 'policy_status' in query_params and not any(k for k in query_params.keys() if k != 'policy_status' and k not in ['limit', 'offset']):
            status = query_params['policy_status']
            validate_enum(status, VALID_POLICY_STATUSES, 'policy_status')
            
            # Use PolicyStatusIndex GSI if it exists
            try:
                response = table.query(
                    IndexName='PolicyStatusIndex',
                    KeyConditionExpression=Key('policy_status').eq(status)
                )
                return response.get('Items', [])
            except ClientError as e:
                # If GSI doesn't exist, log and fall back to scan
                logger.warning(f"PolicyStatusIndex GSI not found, falling back to scan: {str(e)}")
        
        # Fall back to scan with filters for complex queries
        response = table.scan()
        items = response['Items']
        
        # Continue scan if there are more items (pagination within DynamoDB)
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        # Apply filters
        return apply_filters(items, query_params)
        
    except Exception as e:
        logger.error(f"Error in query_items_with_indexes: {str(e)}", exc_info=True)
        raisedef app
ly_filters(items, query_params):
    """Apply filtering logic to items based on query parameters - validates against OpenAPI schema"""
    filtered_items = items
    
    # State filter - validate against OpenAPI enum
    if query_params.get('state'):
        state = query_params['state']
        validate_enum(state, VALID_STATES, 'state')
        filtered_items = [item for item in filtered_items if item.get('state') == state]
    
    # Policy status filter - validate against OpenAPI enum
    if query_params.get('policy_status'):
        status = query_params['policy_status']
        validate_enum(status, VALID_POLICY_STATUSES, 'policy_status')
        filtered_items = [item for item in filtered_items if item.get('policy_status') == status]
    
    # Policy type filter - validate against OpenAPI enum
    if query_params.get('policy_type'):
        policy_type = query_params['policy_type']
        validate_enum(policy_type, VALID_POLICY_TYPES, 'policy_type')
        filtered_items = [item for item in filtered_items if item.get('policy_type') == policy_type]
    
    # Vehicle type filter - validate against OpenAPI enum
    if query_params.get('vehicle_type'):
        vehicle_type = query_params['vehicle_type']
        validate_enum(vehicle_type, VALID_VEHICLE_TYPES, 'vehicle_type')
        filtered_items = [item for item in filtered_items if item.get('vehicle_type') == vehicle_type]
    
    # Risk rating filter - validate against OpenAPI enum
    if query_params.get('risk_rating'):
        risk_rating = query_params['risk_rating']
        validate_enum(risk_rating, VALID_RISK_RATINGS, 'risk_rating')
        filtered_items = [item for item in filtered_items if item.get('risk_rating') == risk_rating]
    
    # Deductible filter
    if query_params.get('deductible'):
        deductible = query_params['deductible']
        filtered_items = [item for item in filtered_items if item.get('deductible') == deductible]
    
    # Premium range filters - validate minimum values as per OpenAPI schema
    if query_params.get('premium_min') or query_params.get('premium_max'):
        premium_min = float(query_params.get('premium_min', 0))
        premium_max = float(query_params.get('premium_max', float('inf')))
        
        validate_number(premium_min, 'premium_min', 0)
        validate_number(premium_max, 'premium_max', 0)
        
        def in_premium_range(item):
            try:
                premium = parse_currency_amount(item.get('premium_amount', 0))
                return premium_min <= premium <= premium_max
            except (ValueError, TypeError):
                return False
        
        filtered_items = [item for item in filtered_items if in_premium_range(item)]    # 
Coverage limit range filters - validate minimum values
    if query_params.get('coverage_limit_min') or query_params.get('coverage_limit_max'):
        coverage_min = float(query_params.get('coverage_limit_min', 0))
        coverage_max = float(query_params.get('coverage_limit_max', float('inf')))
        
        validate_number(coverage_min, 'coverage_limit_min', 0)
        validate_number(coverage_max, 'coverage_limit_max', 0)
        
        def in_coverage_range(item):
            try:
                coverage = parse_currency_amount(item.get('coverage_limit', '0'))
                return coverage_min <= coverage <= coverage_max
            except (ValueError, TypeError):
                return False
        
        filtered_items = [item for item in filtered_items if in_coverage_range(item)]
    
    # Date range filters - validate date format
    date_fields = [
        ('start_date_from', 'start_date', '>='),
        ('start_date_to', 'start_date', '<='),
        ('end_date_from', 'end_date', '>='),
        ('end_date_to', 'end_date', '<=')
    ]
    
    for param_name, field_name, operator in date_fields:
        if query_params.get(param_name):
            date_value = query_params[param_name]
            validate_date(date_value, param_name)
            
            if operator == '>=':
                filtered_items = [item for item in filtered_items 
                                 if item.get(field_name, '') >= date_value]
            else:  # operator == '<='
                filtered_items = [item for item in filtered_items 
                                 if item.get(field_name, '') <= date_value]
    
    # Compliance filter - validate against OpenAPI enum
    if query_params.get('is_compliant'):
        is_compliant = query_params['is_compliant']
        validate_enum(is_compliant, VALID_COMPLIANCE_VALUES, 'is_compliant')
        filtered_items = [item for item in filtered_items if item.get('is_compliant') == is_compliant]
    
    # Agent ID filter - validate UUID format
    if query_params.get('agent_id'):
        agent_id = query_params['agent_id']
        validate_uuid(agent_id, 'agent_id')
        filtered_items = [item for item in filtered_items if item.get('agent_id') == agent_id]
    
    # Customer ID filter - validate UUID format
    if query_params.get('customer_id'):
        customer_id = query_params['customer_id']
        validate_uuid(customer_id, 'customer_id')
        filtered_items = [item for item in filtered_items if item.get('customer_id') == customer_id]
    
    # Product version filter - validate pattern as per OpenAPI schema
    if query_params.get('product_version'):
        product_version = query_params['product_version']
        validate_version(product_version, 'product_version')
        filtered_items = [item for item in filtered_items if item.get('product_version') == product_version]
    
    return filtered_items

def parse_currency_amount(amount_str):
    """Parse currency string to float (handles $1,000 format)"""
    if not amount_str:
        return 0.0
    # Remove currency symbols and commas
    cleaned = re.sub(r'[$,]', '', str(amount_str))
    return float(cleaned)def han
dle_create_item(body, headers, path):
    """Handle POST /items - Create new policy matching OpenAPI CreateResponse schema"""
    try:
        if not body:
            return create_error_response(400, "Request body is required", "MISSING_BODY", headers, path)
        
        item = json.loads(body)
        
        # Validate required fields as defined in OpenAPI schema
        required_fields = ['policy_id', 'customer_id', 'agent_id', 'policy_type', 'vehicle_type', 'policy_status']
        for field in required_fields:
            if field not in item:
                return create_error_response(400, f"Missing required field: {field}", "VALIDATION_ERROR", headers, path)
        
        # Validate enum values against OpenAPI schema
        validate_enum(item.get('policy_type'), VALID_POLICY_TYPES, 'policy_type')
        validate_enum(item.get('vehicle_type'), VALID_VEHICLE_TYPES, 'vehicle_type')
        validate_enum(item.get('policy_status'), VALID_POLICY_STATUSES, 'policy_status')
        
        # Validate UUID format for IDs
        validate_uuid(item.get('policy_id'), 'policy_id')
        validate_uuid(item.get('customer_id'), 'customer_id')
        validate_uuid(item.get('agent_id'), 'agent_id')
        
        # Add timestamp
        item['last_updated'] = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Sanitize inputs to prevent injection
        for key, value in item.items():
            item[key] = sanitize_input(value)
        
        table.put_item(Item=item)
        
        # Invalidate relevant caches
        invalidate_cache()  # For simplicity, invalidate all caches on write operations
        
        # Return response matching OpenAPI CreateResponse schema
        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                "message": "Policy created successfully",
                "policy": item
            }, cls=DecimalEncoder)
        }
        
    except json.JSONDecodeError:
        return create_error_response(400, "Invalid JSON in request body", "INVALID_JSON", headers, path)
    except ValueError as e:
        return create_error_response(400, str(e), "VALIDATION_ERROR", headers, path)
    except ClientError as e:
        logger.error(f"DynamoDB error in handle_create_item: {str(e)}", exc_info=True)
        return create_error_response(500, f"Database error", "CREATE_ERROR", headers, path)
    except Exception as e:
        logger.error(f"Error in handle_create_item: {str(e)}", exc_info=True)
        return create_error_response(500, f"Failed to create item", "CREATE_ERROR", headers, path)def handle
_get_item(policy_id, headers, path):
    """Handle GET /items/{policy_id} - Get single policy matching OpenAPI schema"""
    try:
        if not policy_id:
            return create_error_response(400, "Policy ID is required", "MISSING_POLICY_ID", headers, path)
        
        # Validate UUID format
        validate_uuid(policy_id, 'policy_id')
        
        # Check cache first
        cache_key = f"policy:{policy_id}"
        cached_response = get_cached_item(cache_key)
        if cached_response:
            return cached_response
        
        response = table.get_item(Key={'policy_id': policy_id})
        
        if 'Item' not in response:
            return create_error_response(404, "Policy not found", "NOT_FOUND", headers, path)
        
        # Return single InsurancePolicy object as per OpenAPI schema
        result = {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response['Item'], cls=DecimalEncoder)
        }
        
        # Cache individual policy for 30 seconds
        set_cached_item(cache_key, result, 30)
        return result
        
    except ValueError as e:
        return create_error_response(400, str(e), "VALIDATION_ERROR", headers, path)
    except ClientError as e:
        logger.error(f"DynamoDB error in handle_get_item: {str(e)}", exc_info=True)
        return create_error_response(500, f"Database error", "GET_ERROR", headers, path)
    except Exception as e:
        logger.error(f"Error in handle_get_item: {str(e)}", exc_info=True)
        return create_error_response(500, f"Failed to retrieve item", "GET_ERROR", headers, path)def 
handle_update_item(policy_id, body, headers, path):
    """Handle PUT /items/{policy_id} - Update policy matching OpenAPI UpdateResponse schema"""
    try:
        if not policy_id:
            return create_error_response(400, "Policy ID is required", "MISSING_POLICY_ID", headers, path)
        
        # Validate UUID format
        validate_uuid(policy_id, 'policy_id')
        
        if not body:
            return create_error_response(400, "Request body is required", "MISSING_BODY", headers, path)
        
        item = json.loads(body)
        item['policy_id'] = policy_id  # Ensure policy_id matches path parameter
        item['last_updated'] = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Check if item exists first
        existing_response = table.get_item(Key={'policy_id': policy_id})
        if 'Item' not in existing_response:
            return create_error_response(404, "Policy not found", "NOT_FOUND", headers, path)
        
        # Validate enum values if provided
        if 'policy_type' in item:
            validate_enum(item['policy_type'], VALID_POLICY_TYPES, 'policy_type')
        
        if 'vehicle_type' in item:
            validate_enum(item['vehicle_type'], VALID_VEHICLE_TYPES, 'vehicle_type')
        
        if 'policy_status' in item:
            validate_enum(item['policy_status'], VALID_POLICY_STATUSES, 'policy_status')
        
        # Validate UUID format for IDs
        if 'customer_id' in item:
            validate_uuid(item['customer_id'], 'customer_id')
        
        if 'agent_id' in item:
            validate_uuid(item['agent_id'], 'agent_id')
        
        # Sanitize inputs to prevent injection
        for key, value in item.items():
            item[key] = sanitize_input(value)
        
        table.put_item(Item=item)
        
        # Invalidate relevant caches
        invalidate_cache(f"policy:{policy_id}")  # Invalidate specific policy cache
        invalidate_cache()  # For simplicity, invalidate all list caches
        
        # Return response matching OpenAPI UpdateResponse schema
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                "message": "Policy updated successfully",
                "policy": item
            }, cls=DecimalEncoder)
        }
        
    except json.JSONDecodeError:
        return create_error_response(400, "Invalid JSON in request body", "INVALID_JSON", headers, path)
    except ValueError as e:
        return create_error_response(400, str(e), "VALIDATION_ERROR", headers, path)
    except ClientError as e:
        logger.error(f"DynamoDB error in handle_update_item: {str(e)}", exc_info=True)
        return create_error_response(500, f"Database error", "UPDATE_ERROR", headers, path)
    except Exception as e:
        logger.error(f"Error in handle_update_item: {str(e)}", exc_info=True)
        return create_error_response(500, f"Failed to update item", "UPDATE_ERROR", headers, path)def ha
ndle_delete_item(policy_id, headers, path):
    """Handle DELETE /items/{policy_id} - Delete policy matching OpenAPI schema"""
    try:
        if not policy_id:
            return create_error_response(400, "Policy ID is required", "MISSING_POLICY_ID", headers, path)
        
        # Validate UUID format
        validate_uuid(policy_id, 'policy_id')
        
        # Check if item exists
        existing_response = table.get_item(Key={'policy_id': policy_id})
        if 'Item' not in existing_response:
            return create_error_response(404, "Policy not found", "NOT_FOUND", headers, path)
        
        table.delete_item(Key={'policy_id': policy_id})
        
        # Invalidate relevant caches
        invalidate_cache(f"policy:{policy_id}")  # Invalidate specific policy cache
        invalidate_cache()  # For simplicity, invalidate all list caches
        
        # Return 204 No Content as per OpenAPI schema
        return {
            'statusCode': 204,
            'headers': headers,
            'body': ''
        }
        
    except ValueError as e:
        return create_error_response(400, str(e), "VALIDATION_ERROR", headers, path)
    except ClientError as e:
        logger.error(f"DynamoDB error in handle_delete_item: {str(e)}", exc_info=True)
        return create_error_response(500, f"Database error", "DELETE_ERROR", headers, path)
    except Exception as e:
        logger.error(f"Error in handle_delete_item: {str(e)}", exc_info=True)
        return create_error_response(500, f"Failed to delete item", "DELETE_ERROR", headers, path)def h
andle_search_items(body, headers, path):
    """Handle POST /items/search - Advanced search matching OpenAPI SearchResponse schema"""
    try:
        if not body:
            return create_error_response(400, "Request body is required", "MISSING_BODY", headers, path)
        
        search_request = json.loads(body)
        
        # Generate cache key based on search request
        cache_key = f"search:{json.dumps(search_request, sort_keys=True)}"
        cached_response = get_cached_item(cache_key)
        if cached_response:
            return cached_response
        
        start_time = datetime.utcnow()
        
        # Get all items using optimized query if possible
        filters = search_request.get('filters', {})
        filtered_items = apply_advanced_filters(filters)
        
        # Apply sorting
        sort_config = search_request.get('sort', {})
        if sort_config.get('field'):
            filtered_items = sort_items(filtered_items, sort_config)
        
        # Apply pagination
        pagination = search_request.get('pagination', {})
        limit = min(pagination.get('limit', 100), 1000)  # Max 1000 as per schema
        offset = max(pagination.get('offset', 0), 0)
        
        total_count = len(filtered_items)
        paginated_items = filtered_items[offset:offset + limit]
        
        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Return response matching OpenAPI SearchResponse schema exactly
        response = {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                "items": paginated_items,
                "total_count": total_count,
                "returned_count": len(paginated_items),
                "has_more": (offset + limit) < total_count,
                "search_metadata": {
                    "execution_time_ms": round(execution_time, 2),
                    "filters_applied": list(filters.keys())
                }
            }, cls=DecimalEncoder)
        }
        
        # Cache search results for 30 seconds
        set_cached_item(cache_key, response, 30)
        return response
        
    except json.JSONDecodeError:
        return create_error_response(400, "Invalid JSON in request body", "INVALID_JSON", headers, path)
    except ValueError as e:
        return create_error_response(400, str(e), "VALIDATION_ERROR", headers, path)
    except Exception as e:
        logger.error(f"Error in handle_search_items: {str(e)}", exc_info=True)
        return create_error_response(500, f"Search failed", "SEARCH_ERROR", headers, path)def 
apply_advanced_filters(filters):
    """Apply advanced filtering logic for search endpoint with optimized queries where possible"""
    # Try to use GSIs for efficient filtering
    if filters.get('states') and len(filters.get('states')) == 1 and len(filters) == 1:
        # If only filtering by a single state, try to use StateIndex GSI
        state = filters['states'][0]
        validate_enum(state, VALID_STATES, 'state')
        
        try:
            response = table.query(
                IndexName='StateIndex',
                KeyConditionExpression=Key('state').eq(state)
            )
            return response.get('Items', [])
        except ClientError:
            # If GSI doesn't exist, fall back to scan
            logger.warning("StateIndex GSI not found, falling back to scan")
    
    # Fall back to scan for complex filters
    response = table.scan()
    items = response['Items']
    
    # Continue scan if there are more items (pagination within DynamoDB)
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    
    filtered_items = items
    
    # Array-based filters (OR logic within each array)
    if filters.get('states'):
        states = filters['states']
        for state in states:
            validate_enum(state, VALID_STATES, 'state')
        filtered_items = [item for item in filtered_items if item.get('state') in states]
    
    if filters.get('policy_types'):
        policy_types = filters['policy_types']
        for policy_type in policy_types:
            validate_enum(policy_type, VALID_POLICY_TYPES, 'policy_type')
        filtered_items = [item for item in filtered_items if item.get('policy_type') in policy_types]
    
    if filters.get('vehicle_types'):
        vehicle_types = filters['vehicle_types']
        for vehicle_type in vehicle_types:
            validate_enum(vehicle_type, VALID_VEHICLE_TYPES, 'vehicle_type')
        filtered_items = [item for item in filtered_items if item.get('vehicle_type') in vehicle_types]
    
    if filters.get('policy_statuses'):
        statuses = filters['policy_statuses']
        for status in statuses:
            validate_enum(status, VALID_POLICY_STATUSES, 'policy_status')
        filtered_items = [item for item in filtered_items if item.get('policy_status') in statuses]
    
    if filters.get('risk_ratings'):
        ratings = filters['risk_ratings']
        for rating in ratings:
            validate_enum(rating, VALID_RISK_RATINGS, 'risk_rating')
        filtered_items = [item for item in filtered_items if item.get('risk_rating') in ratings] 
   # Range filters
    premium_range = filters.get('premium_range', {})
    if premium_range:
        premium_min = premium_range.get('min', 0)
        premium_max = premium_range.get('max', float('inf'))
        
        validate_number(premium_min, 'premium_min', 0)
        if premium_max != float('inf'):
            validate_number(premium_max, 'premium_max', 0)
        
        def in_premium_range(item):
            try:
                premium = parse_currency_amount(item.get('premium_amount', 0))
                return premium_min <= premium <= premium_max
            except (ValueError, TypeError):
                return False
        
        filtered_items = [item for item in filtered_items if in_premium_range(item)]
    
    # Date range filters
    date_range = filters.get('date_range', {})
    if date_range:
        if date_range.get('start_date_from'):
            validate_date(date_range['start_date_from'], 'start_date_from')
            filtered_items = [item for item in filtered_items 
                             if item.get('start_date', '') >= date_range['start_date_from']]
        if date_range.get('start_date_to'):
            validate_date(date_range['start_date_to'], 'start_date_to')
            filtered_items = [item for item in filtered_items 
                             if item.get('start_date', '') <= date_range['start_date_to']]
        if date_range.get('end_date_from'):
            validate_date(date_range['end_date_from'], 'end_date_from')
            filtered_items = [item for item in filtered_items 
                             if item.get('end_date', '') >= date_range['end_date_from']]
        if date_range.get('end_date_to'):
            validate_date(date_range['end_date_to'], 'end_date_to')
            filtered_items = [item for item in filtered_items 
                             if item.get('end_date', '') <= date_range['end_date_to']]
    
    # Compliance filter
    if filters.get('compliance'):
        compliance = filters['compliance']
        validate_enum(compliance, VALID_COMPLIANCE_VALUES, 'compliance')
        filtered_items = [item for item in filtered_items if item.get('is_compliant') == compliance]
    
    return filtered_items

def sort_items(items, sort_config):
    """Sort items based on sort configuration"""
    field = sort_config.get('field')
    order = sort_config.get('order', 'asc')
    
    if not field:
        return items
    
    # Validate sort field
    valid_sort_fields = ['premium_amount', 'start_date', 'end_date', 'last_updated']
    if field not in valid_sort_fields:
        logger.warning(f"Invalid sort field: {field}. Using default order.")
        return items
    
    # Handle special case for premium_amount (convert to float)
    if field == 'premium_amount':
        def get_sort_key(item):
            try:
                return parse_currency_amount(item.get(field, '0'))
            except (ValueError, TypeError):
                return 0
    else:
        def get_sort_key(item):
            return item.get(field, '')
    
    # Sort items
    reverse = (order.lower() == 'desc')
    return sorted(items, key=get_sort_key, reverse=reverse)def han
dle_get_stats(query_params, headers, path):
    """Handle GET /items/stats - Get policy statistics matching OpenAPI StatsResponse schema"""
    try:
        # Generate cache key based on query parameters
        cache_key = f"stats:{json.dumps(query_params, sort_keys=True)}"
        cached_response = get_cached_item(cache_key)
        if cached_response:
            return cached_response
        
        # Get all items
        response = table.scan()
        items = response['Items']
        
        # Continue scan if there are more items (pagination within DynamoDB)
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        # Calculate statistics
        total_policies = len(items)
        
        # Group by parameters
        group_by = query_params.get('group_by')
        summary = {}
        
        # Calculate summary statistics
        summary['by_state'] = count_by_field(items, 'state')
        summary['by_policy_type'] = count_by_field(items, 'policy_type')
        summary['by_vehicle_type'] = count_by_field(items, 'vehicle_type')
        summary['by_policy_status'] = count_by_field(items, 'policy_status')
        summary['by_risk_rating'] = count_by_field(items, 'risk_rating')
        
        # Calculate averages
        premium_values = [parse_currency_amount(item.get('premium_amount', '0')) for item in items]
        coverage_values = [parse_currency_amount(item.get('coverage_limit', '0')) for item in items]
        
        averages = {
            'premium_amount': sum(premium_values) / len(premium_values) if premium_values else 0,
            'coverage_limit': sum(coverage_values) / len(coverage_values) if coverage_values else 0
        }
        
        # Calculate ranges
        ranges = {
            'premium_amount': {
                'min': min(premium_values) if premium_values else 0,
                'max': max(premium_values) if premium_values else 0
            },
            'coverage_limit': {
                'min': min(coverage_values) if coverage_values else 0,
                'max': max(coverage_values) if coverage_values else 0
            }
        }
        
        # Calculate compliance rate
        compliant_count = sum(1 for item in items if item.get('is_compliant') == 'TRUE')
        compliance_rate = (compliant_count / total_policies * 100) if total_policies > 0 else 0
        
        # Build response matching OpenAPI StatsResponse schema
        stats_response = {
            'total_policies': total_policies,
            'summary': summary,
            'averages': averages,
            'ranges': ranges,
            'compliance_rate': round(compliance_rate, 2)
        }
        
        response = {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(stats_response, cls=DecimalEncoder)
        }
        
        # Cache statistics for 60 seconds
        set_cached_item(cache_key, response, 60)
        return response
        
    except Exception as e:
        logger.error(f"Error in handle_get_stats: {str(e)}", exc_info=True)
        return create_error_response(500, f"Failed to retrieve statistics", "STATS_ERROR", headers, path)

def count_by_field(items, field):
    """Count items grouped by a specific field"""
    result = {}
    for item in items:
        value = item.get(field, 'Unknown')
        if value not in result:
            result[value] = 0
        result[value] += 1
    return result

# Configure AWS Lambda Dead Letter Queue if environment variable is set
if os.environ.get("DLQ_ARN"):
    try:
        import boto3.session
        lambda_client = boto3.client('lambda')
        lambda_client.update_function_configuration(
            FunctionName=os.environ.get("AWS_LAMBDA_FUNCTION_NAME"),
            DeadLetterConfig={
                'TargetArn': os.environ.get("DLQ_ARN")
            }
        )
        logger.info(f"Configured DLQ: {os.environ.get('DLQ_ARN')}")
    except Exception as e:
        logger.warning(f"Failed to configure DLQ: {str(e)}")