# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import os
import json
import re
import logging
import ssl
import base64
from botocore.exceptions import ClientError
from datetime import datetime
from typing import List, Dict
from urllib import request, parse, error

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add handler if not already present (for local testing)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '[%(levelname)s]\t%(asctime)s.%(msecs)dZ\t%(aws_request_id)s\t',
        '%(message)s\n',
        '%Y-%m-%dT%H:%M:%S'
    ))
    logger.addHandler(handler)


class LogStreamProcessor:
    def __init__(
            self,
            application_id=None,
            data_source_id=None,
            index_id=None,
            servicenow_host=None,
            servicenow_username=None,
            servicenow_password=None,
            global_domain=None
    ):

        """
        Initialize the LogStreamProcessor with configuration
        """
        logger.info("Initializing LogStreamProcessor")

        # Initialize AWS clients
        self.cloudwatch_logs = boto3.client('logs')
        self.qbusiness = boto3.client('qbusiness')
        self.secrets_client = boto3.client('secretsmanager')

        # Get configuration from environment variables with optional overrides
        self.application_id = application_id or os.getenv('APPLICATION_ID')
        self.data_source_id = data_source_id or os.getenv('DATA_SOURCE_ID')
        self.index_id = index_id or os.getenv('INDEX_ID')
        self.servicenow_host = servicenow_host or os.getenv('SERVICENOW_HOST')
        self.servicenow_username = (
            servicenow_username or os.getenv('SERVICENOW_USERNAME')
        )
        self.global_domain = global_domain or os.getenv('GLOBAL_DOMAIN')

        # Get ServiceNow password from Secrets Manager if not provided
        if not servicenow_password:
            secret_name = os.getenv('SERVICENOW_SECRET_NAME')
            if not secret_name:
                logger.error("SERVICENOW_SECRET_NAME env variable not set")
                raise ValueError("SERVICENOW_SECRET_NAME env variable not set")

            try:
                secret_response = (
                    self.secrets_client.get_secret_value(
                        SecretId=secret_name
                    )
                )
                secret_value = json.loads(secret_response['SecretString'])
                self.servicenow_password = secret_value.get('password')
                if not self.servicenow_password:
                    raise ValueError("Password not found in secret value")
            except ClientError as e:
                logger.error(
                    f"Failed to retrieve secret: "
                    f"{e.response['Error']['Message']}"
                )
                raise ValueError(
                    f"Failed to retrieve secret: {e.response['Error']['Code']}"
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Invalid secret format: {str(e)}")
                raise ValueError("Invalid secret format")
        else:
            self.servicenow_password = servicenow_password

        logger.info(
            f"Configuration loaded - Application ID: {self.application_id}, "
            f"Data Source ID: {self.data_source_id}, Index ID: {self.index_id}"
        )

        # Validate required parameters
        missing_params = []
        if not self.application_id:
            missing_params.append('APPLICATION_ID')
        if not self.data_source_id:
            missing_params.append('DATA_SOURCE_ID')
        if not self.index_id:
            missing_params.append('INDEX_ID')
        if not self.servicenow_host:
            missing_params.append('SERVICENOW_HOST')
        if not self.servicenow_username:
            missing_params.append('SERVICENOW_USERNAME')
        if not self.servicenow_password:
            missing_params.append('SERVICENOW_PASSWORD')
        if not self.global_domain:
            missing_params.append('GLOBAL_DOMAIN')

        if missing_params:
            error_msg = (
                f"Missing required parameters: "
                f"{', '.join(missing_params)}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Updated log group name format for Q Business
        self.log_group_name = f"/aws/qbusiness/{self.application_id}"
        logger.info(f"Log group name set to: {self.log_group_name}")

        # Set up ServiceNow base URL and parameters
        self.servicenow_base_url = (
            f"https://{self.servicenow_host}/api/now/table/sys_user_has_role"
        )
        self.servicenow_params = {
            'sysparm_fields': 'role.sys_id,role.name,user.sys_id,user.email',
            'sysparm_query_template': (
                'role.sys_id={role_id}^ORDERBYsys_created_on^state=active^'
                'role.nameISNOTEMPTY^user.emailISNOTEMPTY^user.active=true'
            )
        }

        try:
            # Set up basic auth
            credentials = base64.b64encode(
                f"{self.servicenow_username}:"
                f"{self.servicenow_password}".encode()
            ).decode()

            self.servicenow_headers = {
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        except Exception as e:
            logger.error(
                f"Failed to set up ServiceNow authentication headers: "
                f"{str(e)}"
            )
            raise

        # Compile regex pattern for role ID extraction
        self.role_pattern = re.compile(
            r"Retrieving group members for group id:\s*([a-f0-9]{32})"
        )

    def get_latest_sync_job_id(self):
        """
        Get the latest sync job execution ID using ListDataSourceSyncJobs
        """
        logger.info("Fetching latest sync job ID")
        try:
            response = self.qbusiness.list_data_source_sync_jobs(
                applicationId=self.application_id,
                dataSourceId=self.data_source_id,
                indexId=self.index_id
            )

            sync_jobs = response.get('history', [])

            if not sync_jobs:
                logger.warning("No sync jobs found")
                return None

            latest_job = sorted(
                sync_jobs,
                key=lambda x: x.get('startTime', datetime.min),
                reverse=True
            )[0]

            job_status = latest_job.get('status')
            execution_id = latest_job.get('executionId')

            logger.info(
                f"Latest sync job found - ID: {execution_id}, "
                f"Status: {job_status}"
            )
            return execution_id

        except ClientError as e:
            logger.error(f"Error fetching sync jobs: {str(e)}")
            raise

    def find_log_streams(self, sync_job_run_id):
        """
        Find all log stream names for a specific sync job
        Returns a list of log stream names that end with the sync_job_run_id
        """
        logger.info(
            f"Searching for log streams for sync job ID: "
            f"{sync_job_run_id}"
        )

        try:
            log_stream_prefix = f"{self.data_source_id}/"
            matching_streams = []

            paginator = (
                self.cloudwatch_logs.get_paginator('describe_log_streams')
            )

            try:
                for page in paginator.paginate(
                    logGroupName=self.log_group_name,
                    logStreamNamePrefix=log_stream_prefix
                ):
                    for stream in page.get('logStreams', []):
                        stream_name = stream['logStreamName']
                        if stream_name.endswith(sync_job_run_id):
                            matching_streams.append(stream_name)

                logger.info(f"Found {len(matching_streams)} matching streams")
                return matching_streams

            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.warning(
                        f"Log group not found: {self.log_group_name}"
                    )
                    return []
                raise

        except ClientError as e:
            logger.error(f"Error searching for log streams: {str(e)}")
            raise

    def extract_role_ids(self, log_stream_name):
        """
        Extract all role IDs from the log stream
        """
        logger.info(
            f"Starting role ID extraction from log stream: "
            f"{log_stream_name}"
        )
        role_ids_with_timestamps = {}
        next_token = None
        events_processed = 0

        try:
            while True:
                kwargs = {
                    'logGroupName': self.log_group_name,
                    'logStreamName': log_stream_name,
                    'startFromHead': True,
                    'limit': 100
                }

                if next_token:
                    kwargs['nextToken'] = next_token

                response = self.cloudwatch_logs.get_log_events(**kwargs)

                # Process each log event
                for event in response['events']:
                    events_processed += 1
                    message = event['message']
                    match = self.role_pattern.search(message)
                    if match:
                        role_id = match.group(1)
                        timestamp = event['timestamp']

                        # Log the full message and match for debugging
                        logger.info(f"Found match in message: {message}")
                        logger.info(f"Extracted SourceId: {role_id}")

                        # Store or update role ID with its timestamp
                        if (
                            role_id not in role_ids_with_timestamps
                            or timestamp > role_ids_with_timestamps[role_id][
                                'timestamp'
                            ]
                        ):
                            role_ids_with_timestamps[role_id] = {
                                'timestamp': timestamp,
                                'datetime': datetime.fromtimestamp(
                                    timestamp/1000
                                ).isoformat()
                            }

                # Check if we've reached the end of the stream
                if next_token == response.get('nextForwardToken'):
                    break

                next_token = response['nextForwardToken']

            # Convert to list and sort by timestamp
            role_ids_list = [
                {
                    'role_id': role_id,
                    'timestamp': info['timestamp'],
                    'datetime': info['datetime']
                }
                for role_id, info in role_ids_with_timestamps.items()
            ]

            # Sort by timestamp, newest first
            role_ids_list.sort(key=lambda x: x['timestamp'], reverse=True)

            logger.info(f"Processed {events_processed} log events")
            logger.info(f"Found {len(role_ids_list)} unique roleid(s)")
            return role_ids_list

        except ClientError as e:
            logger.error(f"Error processing log stream: {str(e)}")
            raise

    def get_servicenow_role_members(
        self,
        role_data_list: List[Dict]
    ) -> List[Dict]:
        """
        Retrieve role member info from ServiceNow API for given role IDs.

        Args:
            role_data_list (List[Dict]): List of dictionaries with role_id,
                timestamp, and datetime

        Returns:
            List[Dict]: List of role member information from ServiceNow with
                timestamp data
        """
        all_results = []
        processed_roles = 0
        total_roles = len(role_data_list)

        logger.info(
            f"Starting to process {total_roles} role(s) for ServiceNow"
        )
        logger.info(f"URL for ServiceNow call is {self.servicenow_base_url}")
        # Create SSL context
        context = ssl.create_default_context()

        for role_entry in role_data_list:
            role_id = role_entry.get('role_id')
            if not role_id:
                logger.warning(
                    f"Skipping entry with missing role_id: {role_entry}"
                )
                continue

            try:
                # Construct query parameters for this specific role
                params = self.servicenow_params.copy()
                params['sysparm_query'] = (
                    self.servicenow_params['sysparm_query_template'].format(
                        role_id=role_id
                    )
                )

                # Build URL with encoded parameters
                full_url = (
                    f"{self.servicenow_base_url}?"
                    f"{parse.urlencode(params)}"
                )

                # Create request object
                req = request.Request(
                    url=full_url,
                    headers=self.servicenow_headers,
                    method='GET'
                )

                logger.debug(f"Fetching data for role ID: {role_id}")

                # Make the request
                with request.urlopen(
                    req,
                    context=context,
                    timeout=30
                ) as response:
                    data = json.loads(
                        response.read().decode('utf-8')
                    )

                    # Add timestamp and datetime from input data to each result
                    for result in data.get('result', []):
                        result.update({
                            'timestamp': role_entry['timestamp'],
                            'datetime': role_entry['datetime'],
                            'source_role_id': role_id
                        })

                    all_results.extend(data.get('result', []))
                    processed_roles += 1

                    if processed_roles % 10 == 0:
                        logger.info(
                            f"Processed {processed_roles}/{total_roles} roles"
                        )

            except error.HTTPError as e:
                logger.error(
                    f"HTTP Error for role ID {role_id}: {e.code} - {e.reason}"
                )
                logger.error(f"Response: {e.read().decode('utf-8')}")
                raise
            except error.URLError as e:
                logger.error(f"URL Error for role ID {role_id}: {str(e)}")
                if hasattr(e, 'reason'):
                    logger.error(f"Failure reason: {str(e.reason)}")
                raise
            except json.JSONDecodeError as e:
                logger.error(
                    f"JSON Decode Error for role ID {role_id}: {str(e)}"
                )
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error for role ID {role_id}: {str(e)}"
                )
                raise

        logger.info(f"Completed processing {processed_roles} roles")
        logger.info(f"Total member records retrieved: {len(all_results)}")

        return all_results

    def resolve_users(self, results: List[Dict]):
        """
        Process user updates/creations for Q Business based on ServiceNow role
        members

        Args:
            results: List of dictionaries containing ServiceNow role member
                information
        """
        for member in results:
            try:
                user_email = member.get('user.email')
                user_sys_id = member.get('user.sys_id')
                role_name = member.get('role.name')

                if not user_email or not user_sys_id:
                    logger.error(
                        f"Missing required user info for role {role_name}"
                    )
                    continue

                # First attempt to update the user
                try:
                    # Transform email for creation
                    # Convert domain structure to match users
                    modified_email = (
                        f"{user_email.split('@')[0]}"
                        f"@{self.global_domain}"
                    )

                    # userId must match the globalid value
                    # userId (within userAliasesToUpdate must
                    # be the modified email
                    response = self.qbusiness.update_user(
                        applicationId=self.application_id,
                        userId=modified_email,
                        userAliasesToUpdate=[
                            {
                                'userId': user_email
                            }
                        ]
                    )

                    logger.info(
                        f"Successfully updated alias for {modified_email} to "
                        f"SNow user refernece {user_email}"
                    )
                    logger.debug(
                        f"Q Business update_user response: {response}"
                    )

                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code')

                    if error_code == 'ResourceNotFoundException':
                        logger.info(
                            f"User {modified_email} not found. Attempting to "
                            f"create user"
                        )

                        # Transform email for creation
                        # Convert domain structure to match users
                        modified_email = (
                            f"{user_email.split('@')[0]}"
                            f"@{self.global_domain}"
                        )

                        try:
                            # Create the user with modified email, which would
                            # match their globalid value
                            response = self.qbusiness.create_user(
                                applicationId=self.application_id,
                                userId=modified_email,
                                userAliases=[
                                    {
                                        'userId': user_email
                                    },
                                ]
                            )

                            logger.info(
                                f"Successfully created user {modified_email} "
                                f"with ServiceNow alias {user_email}"
                                )
                            logger.debug(
                                f"Q Business create user response: {response}"
                            )
                        except ClientError as create_error:
                            logger.error(
                                f"Failed to create user {modified_email}: "
                                f"{str(create_error)}"
                                )
                            continue
                    else:
                        logger.error(
                            f"Error updating user {user_email}: {str(e)}"
                            )
                        continue

            except Exception as e:
                logger.error(
                    f"Unexpected error processing member with email "
                    f"{member.get('user.email', 'UNKNOWN')}: {str(e)}"
                )
                continue

    def process_single_user(self, user_email: str) -> Dict:
        """
        Process a single user email for domain normalization
            and Q Business update.

        Args:
            user_email (str): The email address to process

        Returns:
            Dict: Response containing status and processing details
        """
        logger.info(f"Processing single user update for: {user_email}")

        try:
            # Transform email for creation
            modified_email = (
                f"{user_email.split('@')[0]}"
                f"@{self.global_domain}"
            )

            # First attempt to update the user
            try:
                response = self.qbusiness.update_user(
                    applicationId=self.application_id,
                    userId=modified_email,
                    userAliasesToUpdate=[
                        {
                            'userId': user_email
                        }
                    ]
                )

                logger.info(
                    f"Successfully updated alias for {modified_email} to "
                    f"SNow user reference {user_email}"
                )
                logger.debug(
                    f"Q Business update_user response: {response}"
                )

                return {
                    'success': True,
                    'modified_email': modified_email,
                    'original_email': user_email,
                    'operation': 'update'
                }

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code')

                if error_code == 'ResourceNotFoundException':
                    logger.info(
                        f"User {modified_email} not found. Attempting to "
                        f"create user"
                    )

                    try:
                        response = self.qbusiness.create_user(
                            applicationId=self.application_id,
                            userId=modified_email,
                            userAliases=[
                                {
                                    'userId': user_email
                                }
                            ]
                        )

                        logger.info(
                            f"Successfully created user {modified_email} "
                            f"with ServiceNow alias {user_email}"
                        )
                        logger.debug(
                            f"Q Business create user response: {response}"
                        )

                        return {
                            'success': True,
                            'modified_email': modified_email,
                            'original_email': user_email,
                            'operation': 'create'
                        }

                    except ClientError as create_error:
                        error_msg = (
                            f"Failed to create user {modified_email}: "
                            f"{str(create_error)}"
                        )
                        logger.error(error_msg)
                        return {
                            'success': False,
                            'error': error_msg
                        }
                else:
                    error_msg = f"Error updating user {user_email}: {str(e)}"
                    logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg
                    }

        except Exception as e:
            error_msg = (
                f"Unexpected error processing user {user_email}: {str(e)}"
            )
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }


def lambda_handler(event, context):
    """
    Lambda function handler
    """
    logger.info(f"Starting Lambda execution with event: {json.dumps(event)}")

    try:
        # Initialize processor
        processor = LogStreamProcessor()

        # Check for single user processing
        specific_user = event.get('user_email')
        if specific_user:
            result = processor.process_single_user(specific_user)

            if result.get('success', False):
                return {
                    'statusCode': 200,
                    'body': json.dumps(result)
                }
            else:
                return {
                    'statusCode': 500,
                    'body': json.dumps(result)
                }

        # Get the sync job ID from the event or fetch the latest
        sync_job_run_id = event.get('sync_job_run_id')
        if not sync_job_run_id:
            logger.info("No sync_job_run_id provided, fetching latest")
            sync_job_run_id = processor.get_latest_sync_job_id()

        if not sync_job_run_id:
            logger.warning("No sync job found")
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'No sync job found',
                    'applicationId': processor.application_id,
                    'dataSourceId': processor.data_source_id,
                    'indexId': processor.index_id
                })
            }

        # Find all log streams for the sync job
        log_stream_names = processor.find_log_streams(sync_job_run_id)
        if not log_stream_names:
            logger.warning(
                f"No log streams found for sync job ID: {sync_job_run_id}"
            )
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'Log streams not found',
                    'sync_job_run_id': sync_job_run_id
                })
            }

        # Extract role IDs from all log streams
        all_role_ids = []
        for log_stream_name in log_stream_names:
            stream_role_ids = processor.extract_role_ids(log_stream_name)
            all_role_ids.extend(stream_role_ids)

        logger.info(
            f"Successfully processed {len(log_stream_names)} "
            f"log streams. Found {len(all_role_ids)} role IDs"
            )

        try:
            # Attempt to get ServiceNow role members
            try:
                results = processor.get_servicenow_role_members(all_role_ids)
                if not results:
                    logger.warning("No results returned from ServiceNow query")
                    return

            except ConnectionError as ce:
                logger.error(
                    f"Connection error while querying ServiceNow: {str(ce)}"
                )
                raise
            except Exception as e:
                logger.error(
                    f"Failed to get ServiceNow role members: {str(e)}"
                )
                raise

            # Process users in Q Business
            try:
                response = processor.resolve_users(results)
                logger.info(
                    f"Successfully processed {len(results)} "
                    f"members in Q Business"
                )

            except ValueError as ve:
                logger.error(
                    f"Configuration error in resolve_users: {str(ve)}"
                )
                raise
            except ClientError as ce:
                logger.error(f"AWS API error in resolve_users: {str(ce)}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error in resolve_users: {str(e)}")
                raise

            # Log detailed results
            try:
                logger.info("Recording user update output:")
                for result in results:
                    logger.info(f"user.email : {result.get('user.email')}")
                    logger.info(f"user.sys_id: {result.get('user.sys_id')}")
                    logger.info("--------------------")
            except Exception as e:
                logger.error(f"Error logging member details: {str(e)}")

        except Exception as e:
            logger.error(f"Critical error in process_role_members: {str(e)}")
            raise

        response = {
            'statusCode': 200,
            'body': json.dumps({
                'sync_job_run_id': sync_job_run_id,
                'log_stream_name': log_stream_name,
                'role_ids': all_role_ids,
                'role_count': len(all_role_ids),
                'member_count_update': len(results),
                'members': results,
                'configuration': {
                    'applicationId': processor.application_id,
                    'dataSourceId': processor.data_source_id,
                    'indexId': processor.index_id
                }
            }, default=str)
        }

        logger.info("Lambda execution completed successfully")
        logger.info(f"Response: {response}")

        return response

    except ValueError as e:
        error_msg = str(e)
        logger.error(f"Validation error: {error_msg}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': error_msg})
        }
    except ClientError as e:
        error_msg = f"AWS API Error: {str(e)}"
        logger.error(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }
