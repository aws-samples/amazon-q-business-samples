import botocore
import boto3
import secrets
import json
import re
import sys
import os

def non_empty_get_env(var_name):
    value = os.getenv(var_name)
    if not value:
        print(f"Environment variable {var_name} is not set.")
        sys.exit(1)
    return value

account_id = non_empty_get_env("AWS_ACCOUNT_ID")
region = non_empty_get_env("AWS_DEFAULT_REGION")
secret_id = non_empty_get_env("AWS_SECRET_ID")
secret_encryption_key = non_empty_get_env("AWS_SECRET_ENCRYPTION_KEY")
clientId = non_empty_get_env("IDP_CLIENT_ID")
issuer_url = non_empty_get_env("IDP_ISSUER_URL")

iss=issuer_url.replace("https://","")
prefix=f"qbiz-{re.sub('.okta.com/.*$','',iss)}-{str(secrets.SystemRandom().randint(0,10000))}"

iam = boto3.client("iam")
try:
    iam_id_provider = iam.create_open_id_connect_provider(
        Url=issuer_url,
        ClientIDList=[clientId]
    )
    print(f"OpenID Connect Provider ARN: {iam_id_provider['OpenIDConnectProviderArn']}")
except botocore.exceptions.ClientError as e:
    print(f"Error creating OpenID Connect Provider: {e}")
    sys.exit(1)

qbusiness = boto3.client("qbusiness", region_name=region)
try:
    qbusiness_application = qbusiness.create_application(
        displayName=f"{prefix}",
        description=f"OIDC Application {prefix} created using API",
        roleArn=f"arn:aws:iam::{account_id}:role/aws-service-role/qbusiness.amazonaws.com/AWSServiceRoleForQBusiness",
        identityType = 'AWS_IAM_IDP_OIDC',
        iamIdentityProviderArn=iam_id_provider['OpenIDConnectProviderArn'],
        clientIdsForOIDC=[ clientId ],
        clientToken = str(secrets.SystemRandom().randint(0,10000))
    )
except botocore.exceptions.ClientError as e:
    print(f"Error creating QBusiness Application: {e}")
    sys.exit(1)
application_id = qbusiness_application['applicationId']
try:
    qbusiness_index = qbusiness.create_index(
        applicationId=application_id,
        displayName=f"{prefix}-index",
        description=f"Index for {prefix}",
        type="ENTERPRISE",
        clientToken = str(secrets.SystemRandom().randint(0, 10000))
    )
except botocore.exceptions.ClientError as e:
    print(f"Error creating QBusiness Index: {e}")
    sys.exit(1)
try:
    qbusiness_retriever = qbusiness.create_retriever(
        applicationId=application_id,
        displayName=f"{prefix}-retriever",
        type="NATIVE_INDEX",
        configuration={
            "nativeIndexConfiguration" : {
                "indexId": qbusiness_index['indexId']
            }
        },
        clientToken = str(secrets.SystemRandom().randint(0, 10000))
    )
except botocore.exceptions.ClientError as e:
    print(f"Error creating QBusiness Retriever: {e}")
    sys.exit(1)
print(f"QBusiness Application ID: {application_id}")
print(f"QBusiness Index ID: {qbusiness_index['indexId']}")
print(f"QBusiness Retriever ID: {qbusiness_retriever['retrieverId']}")

web_experience_perm_policy = {
    "Version": "2012-10-17",
    "Statement": [{
            "Sid": "QBusinessConversationPermissions",
            "Effect": "Allow",
            "Action": [
                "qbusiness:Chat",
                "qbusiness:ChatSync",
                "qbusiness:ListMessages",
                "qbusiness:ListConversations",
                "qbusiness:PutFeedback",
                "qbusiness:DeleteConversation",
                "qbusiness:GetWebExperience",
                "qbusiness:GetApplication",
                "qbusiness:ListPlugins",
                "qbusiness:GetChatControlsConfiguration",
                "qbusiness:ListRetrievers"
            ],
            "Resource": f"arn:aws:qbusiness:{region}:{account_id}:application/{application_id}"
        },
        {
            "Sid": "QBusinessRetrieverPermission",
            "Effect": "Allow",
            "Action": [
                "qbusiness:GetRetriever"
            ],
            "Resource": [
                f"arn:aws:qbusiness:{region}:{account_id}:application/{application_id}",
                f"arn:aws:qbusiness:{region}:{account_id}:application/{application_id}/retriever/*"
            ]
        },
        {
            "Sid": "QBusinessAutoSubscriptionPermission",
            "Effect": "Allow",
            "Action":  [
                "user-subscriptions:CreateClaim" 
            ],
            "Condition":  {
                "Bool":  {
                    "user-subscriptions:CreateForSelf": "true" 
                },
                "StringEquals":  {
                    "aws:CalledViaLast": "qbusiness.amazonaws.com" 
                }
            },
            "Resource":  [
                "*" 
            ]
        },
        {
            "Sid": "QBusinessKMSDecryptPermissions",
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt"
            ],
            "Resource": [
                f"arn:aws:kms:{region}:{account_id}:{secret_encryption_key}"
            ],
            "Condition": {
                "StringLike": {
                    "kms:ViaService": [
                        f"qbusiness.{region}.amazonaws.com",
                        f"qapps.{region}.amazonaws.com"
                    ]
                }
            }
        },
        {
            "Sid": "QAppsResourceAgnosticPermissions",
            "Effect": "Allow",
            "Action": [
                "qapps:CreateQApp",
                "qapps:PredictQApp",
                "qapps:PredictProblemStatementFromConversation",
                "qapps:PredictQAppFromProblemStatement",
                "qapps:ListQApps",
                "qapps:ListLibraryItems",
                "qapps:CreateSubscriptionToken"
            ],
            "Resource": f"arn:aws:qbusiness:{region}:{account_id}:application/{application_id}"
        },
        {
            "Sid": "QAppsAppUniversalPermissions",
            "Effect": "Allow",
            "Action": [
                "qapps:DisassociateQAppFromUser"
            ],
            "Resource": f"arn:aws:qapps:{region}:{account_id}:application/{application_id}/qapp/*"
        },
        {
            "Sid": "QAppsAppOwnerPermissions",
            "Effect": "Allow",
            "Action": [
                "qapps:GetQApp",
                "qapps:CopyQApp",
                "qapps:UpdateQApp",
                "qapps:DeleteQApp",
                "qapps:ImportDocument",
                "qapps:ImportDocumentToQApp",
                "qapps:CreateLibraryItem",
                "qapps:UpdateLibraryItem",
                "qapps:StartQAppSession"
            ],
            "Resource": f"arn:aws:qapps:{region}:{account_id}:application/{application_id}/qapp/*",
            "Condition": {
                "StringEqualsIgnoreCase": {
                    "qapps:UserIsAppOwner": "true"
                }
            }
        },
        {
            "Sid": "QAppsPublishedAppPermissions",
            "Effect": "Allow",
            "Action": [
                "qapps:GetQApp",
                "qapps:CopyQApp",
                "qapps:AssociateQAppWithUser",
                "qapps:GetLibraryItem",
                "qapps:CreateLibraryItemReview",
                "qapps:AssociateLibraryItemReview",
                "qapps:DisassociateLibraryItemReview",
                "qapps:StartQAppSession"
            ],
            "Resource": f"arn:aws:qapps:{region}:{account_id}:application/{application_id}/qapp/*",
            "Condition": {
                "StringEqualsIgnoreCase": {
                    "qapps:AppIsPublished": "true"
                }
            }
        },
        {
            "Sid": "QAppsAppSessionModeratorPermissions",
            "Effect": "Allow",
            "Action": [
                "qapps:ImportDocument",
                "qapps:ImportDocumentToQAppSession",
                "qapps:GetQAppSession",
                "qapps:GetQAppSessionMetadata",
                "qapps:UpdateQAppSession",
                "qapps:UpdateQAppSessionMetadata",
                "qapps:StopQAppSession"
            ],
            "Resource": f"arn:aws:qapps:{region}:{account_id}:application/{application_id}/qapp/*/session/*",
            "Condition": {
                "StringEqualsIgnoreCase": {
                    "qapps:UserIsSessionModerator": "true"
                }
            }
        },
        {
            "Sid": "QAppsSharedAppSessionPermissions",
            "Effect": "Allow",
            "Action": [
                "qapps:ImportDocument",
                "qapps:ImportDocumentToQAppSession",
                "qapps:GetQAppSession",
                "qapps:GetQAppSessionMetadata",
                "qapps:UpdateQAppSession"
            ],
            "Resource": f"arn:aws:qapps:{region}:{account_id}:application/{application_id}/qapp/*/session/*",
            "Condition": {
                "StringEqualsIgnoreCase": {
                    "qapps:SessionIsShared": "true"
                }
            }
        }
    ]
}

web_experience_trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": f"arn:aws:iam::{account_id}:oidc-provider/{iss}"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    f"{iss}:aud": f"{clientId}"
                }
            }
        },
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": f"arn:aws:iam::{account_id}:oidc-provider/{iss}"
            },
            "Action": "sts:TagSession",
            "Condition": {
                "StringLike": {
                    "aws:RequestTag/Email": "*"
                }
            }
        }
    ]
}

secrets_manager_perm_policy = {
    "Version": "2012-10-17",
    "Statement": [{
            "Sid": "AllowsAmazonQToGetSecret",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": [
                f"arn:aws:secretsmanager:{region}:{account_id}:secret:{secret_id}"
            ]
        },
        {
            "Sid": "AllowsAmazonQToDecryptSecret",
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt"
            ],
            "Resource": [
                f"arn:aws:kms:{region}:{account_id}:{secret_encryption_key}"
            ],
            "Condition": {
                "StringLike": {
                    "kms:ViaService": [
                        "secretsmanager.*.amazonaws.com"
                    ]
                }
            }
        }
    ]
}

secrets_manager_trust_policy = {
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "AllowsAmazonQToAssumeRoleForServicePrincipal",
        "Effect": "Allow",
        "Principal": {
            "Service": "application.qbusiness.amazonaws.com"
        },
        "Action": "sts:AssumeRole",
        "Condition": {
            "StringEquals": {
                "aws:SourceAccount": f"{account_id}"
            },
            "ArnLike": {
                "aws:SourceArn": f"arn:aws:qbusiness:{region}:{account_id}:application/{application_id}"
            }
        }
    }]
}

try:
    web_experience_policy = iam.create_policy(
        PolicyName=f"{prefix}-web-experience-policy",
        Description="Web experience policy for {application_id}",
        PolicyDocument=json.dumps(web_experience_perm_policy),
    )
except botocore.exceptions.ClientError as e:
    print(f"Error creating web experience policy: {e}")
    sys.exit(1)
print(f"Web experience policy: {web_experience_policy['Policy']['Arn']}")
try:
    web_experience_role = iam.create_role(
        RoleName=f"{prefix}-web-experience-role", 
        AssumeRolePolicyDocument=json.dumps(web_experience_trust_policy)
    )
except botocore.exceptions.ClientError as e:
    print(f"Error creating web experience role: {e}")
    sys.exit(1)
print(f"Web experience role: {web_experience_role['Role']['Arn']}")
try:
    iam.attach_role_policy(
        RoleName = web_experience_role["Role"]["RoleName"],
        PolicyArn = web_experience_policy["Policy"]["Arn"]
    )
except botocore.exceptions.ClientError as e:
    print(f"Error attaching web experience policy to role: {e}")
    sys.exit(1)
print(f"Attached {web_experience_policy['Policy']['Arn']} to role {web_experience_role['Role']['RoleName']}")

try:
    secrets_manager_policy = iam.create_policy(
        PolicyName=f"{prefix}-secrets-manager-policy",
        Description="Secrets manager policy for {application_id}",
        PolicyDocument=json.dumps(secrets_manager_perm_policy),
    )
except botocore.exceptions.ClientError as e:
    print(f"Error creating secrets manager policy: {e}")
    sys.exit(1)
print(f"Secrets manager policy: {secrets_manager_policy['Policy']['Arn']}")
try:
    secrets_manager_role = iam.create_role(
        RoleName=f"{prefix}-secrets-manager-role", 
        AssumeRolePolicyDocument=json.dumps(secrets_manager_trust_policy)
    )
except botocore.exceptions.ClientError as e:
    print(f"Error creating secrets manager role: {e}")
    sys.exit(1)
print(f"Secrets manager role: {secrets_manager_role['Role']['Arn']}")
try:
    iam.attach_role_policy(
        RoleName = secrets_manager_role["Role"]["RoleName"],
        PolicyArn = secrets_manager_policy["Policy"]["Arn"]
    )
except botocore.exceptions.ClientError as e:
    print(f"Error attaching secrets manager policy to role: {e}")
    sys.exit(1)
print(f"Attached {secrets_manager_policy['Policy']['Arn']} to role {secrets_manager_role['Role']['RoleName']}")

try:
    web_experience = qbusiness.create_web_experience(
        applicationId=application_id,
        title=f"{prefix}-web-experience",
        roleArn = web_experience_role["Role"]["Arn"],
        identityProviderConfiguration={
            "openIDConnectConfiguration": {
                "secretsArn": f"arn:aws:secretsmanager:{region}:{account_id}:secret:{secret_id}",
                "secretsRole": secrets_manager_role["Role"]["Arn"]
            }
        },
        clientToken = str(secrets.SystemRandom().randint(0, 10000))
    )
except botocore.exceptions.ClientError as e:
    print(f"Error creating web experience: {e}")
    sys.exit(1)
print(f"Created web experience: {web_experience['webExperienceArn']}")

try:
    web_experience_details = qbusiness.get_web_experience(
        applicationId=application_id,
        webExperienceId=web_experience["webExperienceId"]
    )
except botocore.exceptions.ClientError as e:
    print(f"Error getting web experience: {e}")
    sys.exit(1)
print(json.dumps(web_experience_details, indent=2, default=str))
try:
    resp = qbusiness.get_application(applicationId=application_id)
    while (resp['status'] != 'ACTIVE'):
        time.sleep(5)
        resp = qbusiness.get_application(applicationId=application_id)
except botocore.exceptions.ClientError as e:
    print(f"Error getting application status: {e}")
    sys.exit(1)
try:
    qbusiness.update_application(
        applicationId=application_id,
        autoSubscriptionConfiguration={
            'autoSubscribe': 'ENABLED',
            'defaultSubscriptionType': 'Q_BUSINESS'
        }
    )
except botocore.exceptions.ClientError as e:
    print(f"Error updating QBusiness Application auto subscription: {e}")
    sys.exit(1)
print(f"QBusiness auto subscription enabled for Q_BUSINESS")
