"""
Amazon Q Business Slack Connector Setup Module.

This module provides functions to create and configure a Slack connector
for Amazon Q Business, including secret management, IAM role creation,
and data source configuration.
"""
# pylint: disable=line-too-long
# flake8: noqa: E501

import json
import uuid
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import boto3


def validate_prerequisites(
    application_id: str,
    index_id: str,
    secret_arn: str,
) -> bool:
    """
    Validate that the prerequisites exist before creating the data source.

    Args:
        application_id (str): The Amazon Q Business application ID
        index_id (str): The Amazon Q Business index ID
        secret_arn (str): The secret ARN

    Returns:
        bool: True if all prerequisites are valid
    """
    print("🔍 Validating prerequisites...")

    try:
        # Check if application exists
        qbusiness_client = boto3.client("qbusiness")

        print("    📱 Checking application...")
        qbusiness_client.get_application(applicationId=application_id)
        print("    ✅ Application ID is valid")

        print("    📇 Checking index...")
        qbusiness_client.get_index(
            applicationId=application_id,
            indexId=index_id,
        )
        print("    ✅ Index ID is valid")

        print("    🔐 Checking secret accessibility...")
        secrets_client = boto3.client("secretsmanager")
        secrets_client.get_secret_value(SecretId=secret_arn)
        print("    ✅ Secret is accessible")

        return True

    except (
        qbusiness_client.exceptions.ResourceNotFoundException,
        qbusiness_client.exceptions.AccessDeniedException,
        secrets_client.exceptions.ResourceNotFoundException,
        secrets_client.exceptions.AccessDeniedException,
    ) as e:
        print(f"    ❌ Validation failed: {str(e)}")
        return False


def create_slack_connector(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-statements
    application_id: str,
    index_id: str,
    secret_arn: str,
    team_id: str,
    data_source_name: str = "Slack Data Source",
    since_date: Optional[str] = None,
    conversation_types: Optional[List[str]] = None,
    crawl_bot_messages: bool = False,
    exclude_archived: bool = True,
    max_file_size_mb: str = "50",
    sync_mode: str = "FULL_CRAWL",
    is_crawl_acl: bool = True,
    role_arn: Optional[str] = None,
    client_token: Optional[str] = None,
    sync_schedule: Optional[str] = None,
    tags: Optional[List[Dict[str, str]]] = None,
    vpc_configuration: Optional[Dict[str, Any]] = None,
    document_enrichment_configuration: Optional[Dict[str, Any]] = None,
    media_extraction_configuration: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a Slack connector data source for Amazon Q Business.

    For complete documentation on all available parameters and configuration
    options, see:
    https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/slack-api.html
    API Reference:
    https://docs.aws.amazon.com/amazonq/latest/api-reference/API_CreateDataSource.html

    Args:
        application_id (str): The Amazon Q Business application ID
        index_id (str): The Amazon Q Business index ID
        secret_arn (str): The ARN of the AWS Secrets Manager secret
                          containing Slack token
        team_id (str): The Slack team ID from your Slack workspace URL
        data_source_name (str): Name for the data source
                               (default: "Slack Data Source")
        since_date (str, optional): ISO 8601 date string to crawl from
                                   (default: 1 month ago)
        conversation_types (List[str], optional): Types of conversations
                                                 to crawl (default:
                                                 ["PUBLIC_CHANNEL",
                                                  "PRIVATE_CHANNEL"])
        crawl_bot_messages (bool): Whether to crawl bot messages
                                  (default: False)
        exclude_archived (bool): Whether to exclude archived channels
                                (default: True)
        max_file_size_mb (str): Maximum file size to crawl in MB
                               (default: "50")
        sync_mode (str): Sync mode - "FULL_CRAWL", "FORCED_FULL_CRAWL",
                        or "CHANGE_LOG"
        is_crawl_acl (bool): Whether to crawl access control information
                            (default: True)
        role_arn (str, optional): IAM role ARN for the data source
        client_token (str, optional): Idempotency token for the request
        sync_schedule (str, optional): Cron expression for sync schedule
        tags (List[Dict[str, str]], optional): Tags for the data source
        vpc_configuration (Dict[str, Any], optional): VPC configuration
        document_enrichment_configuration (Dict[str, Any], optional):
                                          Document enrichment config
        media_extraction_configuration (Dict[str, Any], optional):
                                       Media extraction config

    Returns:
        Dict[str, Any]: Response from CreateDataSource API call
    """
    # Default since_date to 1 month ago if not provided (simple date format)
    if since_date is None:
        one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        since_date = one_month_ago.strftime("%Y-%m-%d")

    # Default conversation types
    if conversation_types is None:
        conversation_types = ["PUBLIC_CHANNEL", "PRIVATE_CHANNEL"]

    # Configuration JSON following the Slack schema
    # Reference:
    # https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/slack-api.html
    configuration = {
        "type": "SLACK",
        "syncMode": sync_mode,
        "secretArn": secret_arn,
        "enableIdentityCrawler": False,
        "identityLoggingStatus": "DISABLED",
        "connectionConfiguration": {"repositoryEndpointMetadata": {"teamId": team_id}},
        "repositoryConfigurations": {
            "All": {
                "fieldMappings": [
                    {
                        "indexFieldName": "_authors",
                        "indexFieldType": "STRING_LIST",
                        "dataSourceFieldName": "authors",
                    },
                    {
                        "indexFieldName": "_source_uri",
                        "indexFieldType": "STRING",
                        "dataSourceFieldName": "url",
                    },
                    {
                        "indexFieldName": "_created_at",
                        "indexFieldType": "DATE",
                        "dataSourceFieldName": "created_at",
                        "dateFieldFormat": "yyyy-MM-dd'T'HH:mm:ss'Z'",
                    },
                    {
                        "indexFieldName": "_last_updated_at",
                        "indexFieldType": "DATE",
                        "dataSourceFieldName": "last_updated_at",
                        "dateFieldFormat": "yyyy-MM-dd'T'HH:mm:ss'Z'",
                    },
                ]
            }
        },
        "additionalProperties": {
            "exclusionPatterns": [],
            "inclusionPatterns": [],
            "crawlBotMessages": crawl_bot_messages,
            "excludeArchived": exclude_archived,
            "channelFilter": {"private_channel": [], "public_channel": []},
            "conversationType": conversation_types,
            "sinceDate": since_date,
            "isCrawlAcl": is_crawl_acl,
            "fieldForUserId": "uuid",
            "channelIdFilter": [],
            "includeSupportedFileType": False,
            "maxFileSizeInMegaBytes": max_file_size_mb,
            "enableDeletionProtection": False,
            "deletionProtectionThreshold": "0",
        },
        "version": "1.0.0",
    }

    # Initialize boto3 client
    qbusiness_client = boto3.client("qbusiness")

    # Generate client token if not provided
    if not client_token:
        client_token = str(uuid.uuid4())

    # Prepare the CreateDataSource request
    create_data_source_params = {
        "applicationId": application_id,
        "indexId": index_id,
        "displayName": data_source_name,
        "configuration": configuration,
        "description": f"Slack data source for team {team_id}",
        "clientToken": client_token,
    }

    # Add optional parameters if provided
    if role_arn:
        create_data_source_params["roleArn"] = role_arn

    if sync_schedule:
        create_data_source_params["syncSchedule"] = sync_schedule

    if tags:
        create_data_source_params["tags"] = tags

    if vpc_configuration:
        create_data_source_params["vpcConfiguration"] = vpc_configuration

    if document_enrichment_configuration:
        create_data_source_params["documentEnrichmentConfiguration"] = (
            document_enrichment_configuration
        )

    if media_extraction_configuration:
        create_data_source_params["mediaExtractionConfiguration"] = (
            media_extraction_configuration
        )

    try:
        # Debug output
        print("🔍 Debug: Attempting to create data source with parameters:")
        print(f"    📱 Application ID: {application_id}")
        print(f"    📇 Index ID: {index_id}")
        print(f"    📝 Display Name: {data_source_name}")
        config_size = len(json.dumps(configuration))
        print(f"    🔧 Configuration size: {config_size} characters")

        # Create the data source
        create_response = qbusiness_client.create_data_source(
            **create_data_source_params
        )

        print("💬 ✅ Slack data source created successfully!")
        print(f"    📊 Data Source ID: {create_response['dataSourceId']}")
        print(f"    📝 Data Source Name: {data_source_name}")
        print(f"    🏢 Team ID: {team_id}")
        since_date_value = configuration["additionalProperties"]["sinceDate"]
        print(f"    📅 Since Date: {since_date_value}")

        return create_response

    except (
        qbusiness_client.exceptions.ResourceNotFoundException,
        qbusiness_client.exceptions.AccessDeniedException,
        qbusiness_client.exceptions.ValidationException,
        qbusiness_client.exceptions.ConflictException,
        qbusiness_client.exceptions.InternalServerException,
    ) as e:
        print(f"💬 ❌ Error creating Slack data source: {str(e)}")

        # Additional troubleshooting info
        if "InternalFailure" in str(e):
            print("🔍 Troubleshooting tips for InternalFailure:")
            print("    • Verify your Application ID and Index ID are correct")
            print("    • Check if your AWS credentials have sufficient permissions")
            print("    • Ensure the secret ARN is accessible from your AWS account")
            print(
                "    • Try again in a few minutes (could be temporary service issue)"
            )
            print("    • Check AWS Service Health Dashboard for any ongoing issues")

        # Print configuration for debugging (without sensitive data)
        debug_config = configuration.copy()
        debug_config["secretArn"] = "***REDACTED***"
        print("🔍 Configuration being sent (sanitized):")
        print(json.dumps(debug_config, indent=2))

        raise


def wait_for_iam_role_propagation(
    role_arn: str,
    max_wait_time: int = 300,
    initial_wait: int = 5,
    max_backoff: int = 30,
) -> bool:
    """
    Wait for IAM role to be properly propagated and accessible.

    Uses exponential backoff to check if the role exists and can be assumed
    by the Q Business service.

    Args:
        role_arn (str): The ARN of the IAM role to wait for
        max_wait_time (int): Maximum time to wait in seconds (default: 300)
        initial_wait (int): Initial wait time in seconds (default: 5)
        max_backoff (int): Maximum backoff time in seconds (default: 30)

    Returns:
        bool: True if role is accessible, False if timeout reached
    """
    print(f"⏳ Waiting for IAM role propagation: {role_arn}")

    iam_client = boto3.client("iam")
    role_name = role_arn.split("/")[-1]

    start_time = time.time()
    wait_time = initial_wait
    attempt = 1

    while time.time() - start_time < max_wait_time:
        try:
            # Check if role exists and is accessible
            response = iam_client.get_role(RoleName=role_name)

            # Verify the role has the correct trust policy
            trust_policy = response["Role"]["AssumeRolePolicyDocument"]

            # Check if qbusiness.amazonaws.com is in the trust policy
            if isinstance(trust_policy, str):
                trust_policy = json.loads(trust_policy)

            for statement in trust_policy.get("Statement", []):
                principal = statement.get("Principal", {})
                if (
                    isinstance(principal, dict)
                    and principal.get("Service") == "qbusiness.amazonaws.com"
                ):
                    print(
                        f"✅ IAM role is accessible after {attempt} attempts "
                        f"({time.time() - start_time:.1f}s)"
                    )
                    return True

            print("⚠️  Role exists but trust policy may be incomplete")

        except iam_client.exceptions.NoSuchEntityException:
            print(
                f"⏳ Attempt {attempt}: Role not yet available, waiting {wait_time}s..."
            )
        except (iam_client.exceptions.AccessDeniedException,
                iam_client.exceptions.ServiceFailureException) as e:
            print(f"⚠️  Attempt {attempt}: Error checking role: {str(e)}")

        time.sleep(wait_time)
        attempt += 1
        wait_time = min(wait_time * 2, max_backoff)

    print(f"❌ Timeout waiting for IAM role propagation after {max_wait_time}s")
    return False


def create_slack_secret(
    slack_token: str,
    secret_name: str,
    description: str = "Slack token for Amazon Q Business connector",
    region_name: Optional[str] = None,
) -> str:
    """
    Create an AWS Secrets Manager secret containing the Slack token.

    Args:
        slack_token (str): The Slack user token (starts with 'xoxb-')
        secret_name (str): Name for the secret in AWS Secrets Manager
        description (str): Description for the secret
        region_name (str, optional): AWS region name (uses default if not
                                    specified)

    Returns:
        str: The ARN of the created secret
    """
    # Initialize Secrets Manager client
    if region_name:
        secrets_client = boto3.client(
            "secretsmanager",
            region_name=region_name,
        )
    else:
        secrets_client = boto3.client("secretsmanager")

    # Secret must contain the Slack token in the required format
    secret_value = {"slackToken": slack_token}

    try:
        # Create the secret
        secret_response = secrets_client.create_secret(
            Name=secret_name,
            Description=description,
            SecretString=json.dumps(secret_value),
        )

        secret_arn = secret_response["ARN"]
        print("🔐 ✅ Secret created successfully!")
        print(f"    📋 Secret Name: {secret_name}")
        print(f"    🔗 Secret ARN: {secret_arn}")
        return secret_arn

    except secrets_client.exceptions.ResourceExistsException:
        # Secret already exists, get its ARN
        print("🔐 ⚠️  Secret already exists - updating with new token...")
        describe_response = secrets_client.describe_secret(
            SecretId=secret_name,
        )
        secret_arn = describe_response["ARN"]

        # Update the secret value
        secrets_client.update_secret(
            SecretId=secret_name, SecretString=json.dumps(secret_value)
        )
        print("🔐 ✅ Secret updated successfully!")
        print(f"    📋 Secret Name: {secret_name}")
        print(f"    🔗 Secret ARN: {secret_arn}")
        return secret_arn

    except (
        secrets_client.exceptions.InvalidRequestException,
        secrets_client.exceptions.ResourceNotFoundException,
        secrets_client.exceptions.AccessDeniedException,
    ) as e:
        print(f"🔐 ❌ Error creating secret: {str(e)}")
        raise


def create_iam_role_for_slack_connector(  # pylint: disable=too-many-locals
    role_name: str,
    application_id: str,
    region_name: Optional[str] = None,
    account_id: Optional[str] = None,
) -> str:
    """
    Create an IAM role for the Slack connector with required permissions.

    Based on AWS documentation:
    https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/slack-iam-role.html

    Args:
        role_name (str): Name for the IAM role
        application_id (str): Amazon Q Business application ID
        region_name (str, optional): AWS region name (auto-detected if not
                                    provided)
        account_id (str, optional): AWS account ID (auto-detected if not
                                   provided)

    Returns:
        str: The ARN of the created IAM role
    """
    # Initialize clients
    iam_client = boto3.client("iam")
    sts_client = boto3.client("sts")

    # Get account ID and region if not provided
    if not account_id:
        account_id = sts_client.get_caller_identity()["Account"]

    if not region_name:
        region_name = boto3.Session().region_name or "us-east-1"

    print(f"🔧 Creating IAM role: {role_name}")
    print(f"    🆔 Account ID: {account_id}")
    print(f"    🌍 Region: {region_name}")
    print(f"    📱 Application ID: {application_id}")

    # Trust policy for Amazon Q Business service
    source_arn = (
        f"arn:aws:qbusiness:{region_name}:{account_id}:" f"application/{application_id}"
    )
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowsAmazonQServicePrincipal",
                "Effect": "Allow",
                "Principal": {"Service": "qbusiness.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {"aws:SourceAccount": account_id},
                    "ArnEquals": {"aws:SourceArn": source_arn},
                },
            }
        ],
    }

    # Permissions policy for the Slack connector
    secret_resource = f"arn:aws:secretsmanager:{region_name}:{account_id}:secret:*"
    kms_resource = f"arn:aws:kms:{region_name}:{account_id}:key/*"
    qbusiness_app_resource = (
        f"arn:aws:qbusiness:{region_name}:{account_id}:" f"application/{application_id}"
    )
    qbusiness_index_resource = (
        f"arn:aws:qbusiness:{region_name}:{account_id}:"
        f"application/{application_id}/index/*"
    )
    qbusiness_datasource_resource = (
        f"arn:aws:qbusiness:{region_name}:{account_id}:"
        f"application/{application_id}/index/*/data-source/*"
    )

    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowsAmazonQToGetSecret",
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue"],
                "Resource": [secret_resource],
            },
            {
                "Sid": "AllowsAmazonQToDecryptSecret",
                "Effect": "Allow",
                "Action": ["kms:Decrypt"],
                "Resource": [kms_resource],
                "Condition": {
                    "StringLike": {
                        "kms:ViaService": [
                            f"secretsmanager.{region_name}.amazonaws.com"
                        ]
                    }
                },
            },
            {
                "Sid": "AllowsAmazonQToIngestDocuments",
                "Effect": "Allow",
                "Action": [
                    "qbusiness:BatchPutDocument",
                    "qbusiness:BatchDeleteDocument",
                ],
                "Resource": [
                    qbusiness_app_resource,
                    qbusiness_index_resource,
                ],
            },
            {
                "Sid": "AllowsAmazonQToIngestPrincipalMapping",
                "Effect": "Allow",
                "Action": [
                    "qbusiness:PutGroup",
                    "qbusiness:CreateUser",
                    "qbusiness:DeleteGroup",
                    "qbusiness:UpdateUser",
                    "qbusiness:ListGroups",
                ],
                "Resource": [
                    qbusiness_app_resource,
                    qbusiness_index_resource,
                    qbusiness_datasource_resource,
                ],
            },
        ],
    }

    try:
        # Create the IAM role
        role_description = (
            f"IAM role for Amazon Q Business Slack connector - "
            f"Application {application_id}"
        )
        role_result = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=role_description,
            MaxSessionDuration=3600,
        )

        role_arn = role_result["Role"]["Arn"]

        # Create and attach the permissions policy
        policy_name = f"{role_name}-SlackConnectorPolicy"
        policy_description = "Permissions policy for Amazon Q Business Slack connector"
        policy_result = iam_client.create_policy(
            PolicyName=policy_name,
            PolicyDocument=json.dumps(permissions_policy),
            Description=policy_description,
        )

        policy_arn = policy_result["Policy"]["Arn"]

        # Attach the policy to the role
        iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

        print("🔧 ✅ IAM role created successfully!")
        print(f"    🎭 Role ARN: {role_arn}")
        print(f"    📋 Policy ARN: {policy_arn}")

        return role_arn

    except iam_client.exceptions.EntityAlreadyExistsException:
        # Role already exists, get its ARN
        print("🔧 ⚠️  IAM role already exists - using existing role...")
        existing_role_response = iam_client.get_role(RoleName=role_name)
        role_arn = existing_role_response["Role"]["Arn"]
        print(f"    🎭 Role ARN: {role_arn}")
        return role_arn

    except (
        iam_client.exceptions.MalformedPolicyDocumentException,
        iam_client.exceptions.LimitExceededException,
        iam_client.exceptions.AccessDeniedException,
    ) as e:
        print(f"🔧 ❌ Error creating IAM role: {str(e)}")
        raise


def setup_complete_slack_connector(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    application_id: str,
    index_id: str,
    slack_token: str,
    team_id: str,
    secret_name: str,
    data_source_name: str = "slack-data-source",
    since_date: Optional[str] = None,
    conversation_types: Optional[List[str]] = None,
    crawl_bot_messages: bool = False,
    exclude_archived: bool = True,
    max_file_size_mb: str = "50",
    sync_mode: str = "FULL_CRAWL",
    is_crawl_acl: bool = True,
    role_arn: Optional[str] = None,
    role_name: Optional[str] = None,
    region_name: Optional[str] = None,
    sync_schedule: Optional[str] = None,
    tags: Optional[List[Dict[str, str]]] = None,
    vpc_configuration: Optional[Dict[str, Any]] = None,
    document_enrichment_configuration: Optional[Dict[str, Any]] = None,
    media_extraction_configuration: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Complete setup: Create secret, IAM role, and Slack connector.

    This is a convenience function that combines all required resource
    creation and connector setup.

    Args:
        application_id (str): The Amazon Q Business application ID
        index_id (str): The Amazon Q Business index ID
        slack_token (str): The Slack user token (starts with 'xoxb-')
        team_id (str): The Slack team ID from your Slack workspace URL
        secret_name (str): Name for the secret in AWS Secrets Manager
        data_source_name (str): Name for the data source
                               (default: "slack-data-source")
        since_date (str, optional): ISO 8601 date string to crawl from
                                   (default: 1 month ago)
        conversation_types (List[str], optional): Types of conversations
                                                 to crawl
        crawl_bot_messages (bool): Whether to crawl bot messages
                                  (default: False)
        exclude_archived (bool): Whether to exclude archived channels
                                (default: True)
        max_file_size_mb (str): Maximum file size to crawl in MB
                               (default: "50")
        sync_mode (str): Sync mode - "FULL_CRAWL", "FORCED_FULL_CRAWL",
                        or "CHANGE_LOG"
        is_crawl_acl (bool): Whether to crawl access control information
                            (default: True)
        role_arn (str, optional): IAM role ARN for the data source
                                 (will create if not provided)
        role_name (str, optional): Name for IAM role to create
                                  (default: auto-generated)
        region_name (str, optional): AWS region name
        sync_schedule (str, optional): Cron expression for sync schedule
        tags (List[Dict[str, str]], optional): Tags for the data source
        vpc_configuration (Dict[str, Any], optional): VPC configuration
        document_enrichment_configuration (Dict[str, Any], optional):
                                          Document enrichment config
        media_extraction_configuration (Dict[str, Any], optional):
                                       Media extraction config

    Returns:
        Dict[str, Any]: Dictionary containing secret ARN, role ARN,
                       data source response, and sync response
    """
    print("🚀 " + "=" * 60)
    print("  🔧 AMAZON Q BUSINESS - SLACK CONNECTOR SETUP")
    print("=" * 64)

    result = {}

    # Step 1: Create the secret
    print("\n📋 STEP 1/4: Creating AWS Secrets Manager secret...")
    print("-" * 50)
    secret_arn = create_slack_secret(
        slack_token=slack_token,
        secret_name=secret_name,
        region_name=region_name,
    )
    result["secret_arn"] = secret_arn

    # Step 2: Create IAM role if not provided
    if not role_arn:
        print("\n📋 STEP 2/4: Creating IAM role...")
        print("-" * 50)

        if not role_name:
            role_name = f"AmazonQSlackConnectorRole-{data_source_name}"

        role_arn = create_iam_role_for_slack_connector(
            role_name=role_name,
            application_id=application_id,
            region_name=region_name,
        )
        result["role_arn"] = role_arn

        # Wait for IAM role propagation
        print("\n⏳ Waiting for IAM role propagation...")
        if not wait_for_iam_role_propagation(
            role_arn, max_wait_time=180, initial_wait=10
        ):
            print("⚠️  IAM role propagation taking longer than expected.")
            print("    Adding additional wait time for AWS service propagation...")
            time.sleep(30)  # Additional wait for AWS service propagation
    else:
        print("\n📋 STEP 2/4: Using provided IAM role...")
        print("-" * 50)
        print(f"    🎭 Role ARN: {role_arn}")
        result["role_arn"] = role_arn

    # Step 3: Validate prerequisites and create the Slack connector
    print("\n📋 STEP 3/4: Creating Slack data source...")
    print("-" * 50)

    # Additional wait to ensure role is fully propagated across all AWS services
    print("⏳ Ensuring IAM role is fully propagated across AWS services...")
    time.sleep(15)

    # Validate prerequisites first
    if not validate_prerequisites(application_id, index_id, secret_arn):
        raise ValueError(
            "❌ Prerequisites validation failed. Please check the error "
            "messages above."
        )

    data_source_response = create_slack_connector(
        application_id=application_id,
        index_id=index_id,
        secret_arn=secret_arn,
        team_id=team_id,
        data_source_name=data_source_name,
        since_date=since_date,
        conversation_types=conversation_types,
        crawl_bot_messages=crawl_bot_messages,
        exclude_archived=exclude_archived,
        max_file_size_mb=max_file_size_mb,
        sync_mode=sync_mode,
        is_crawl_acl=is_crawl_acl,
        role_arn=role_arn,
        sync_schedule=sync_schedule,
        tags=tags,
        vpc_configuration=vpc_configuration,
        document_enrichment_configuration=document_enrichment_configuration,
        media_extraction_configuration=media_extraction_configuration,
    )
    result["data_source"] = data_source_response

    print("\n" + "=" * 64)
    print("🎉 ✅ SLACK CONNECTOR SETUP COMPLETE!")
    print("🚀 Your Slack workspace is now connected to Amazon Q Business")
    print("=" * 64)
    return result


# Example usage
if __name__ == "__main__":
    # Example configuration - replace with your actual values
    APPLICATION_ID = "your-application-id"
    INDEX_ID = "your-index-id"
    SLACK_TOKEN = "xoxb-your-slack-token"
    TEAM_ID = "your-team-id"  # Get this from your Slack workspace URL
    SECRET_NAME = "my-slack-secret"
    DATA_SOURCE_NAME = "my-slack-connector"

    # Create the Slack connector
    main_response = setup_complete_slack_connector(
        application_id=APPLICATION_ID,
        index_id=INDEX_ID,
        slack_token=SLACK_TOKEN,
        team_id=TEAM_ID,
        secret_name=SECRET_NAME,
        data_source_name=DATA_SOURCE_NAME,
    )
