# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    # Duration,
    Stack,
    aws_qbusiness as qbusiness,
    aws_kms as kms,
    aws_iam as iam,
    # aws_logs as logs,
    aws_s3 as s3,
    aws_lambda as lambda_,
    CfnParameter,
    CfnTag,
    CfnOutput,
    # RemovalPolicy,
    aws_s3_deployment as s3deploy,
    BundlingOptions,
    DockerImage,
    Duration,
    aws_s3_assets
)
from constructs import Construct


class QbusCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        idc_instance_arn = CfnParameter(
            self, 'idcInstanceArn',
            type='String',
            description='The ARN of the Identity Center instance'
            )

        kms_key_id_ = self.create_kms_id()

        # Creates a Q Business Application
        cfn_application = qbusiness.CfnApplication(
            self, "MyCfnApplication",
            display_name="QBusiness-Application-CDK",
            attachments_configuration=qbusiness.CfnApplication
            .AttachmentsConfigurationProperty(
                attachments_control_mode="ENABLED"
            ),
            description="Q Business application deployed using CDK",
            # encryption_configuration=qbusiness.CfnApplication.EncryptionConfigurationProperty(
            #     kms_key_id=kms_key_id_
            # ),
            identity_center_instance_arn=idc_instance_arn.value_as_string,
            personalization_configuration=qbusiness
            .CfnApplication.PersonalizationConfigurationProperty(
                personalization_control_mode="ENABLED"
            ),
            q_apps_configuration=qbusiness.CfnApplication
            .QAppsConfigurationProperty(
                q_apps_control_mode="ENABLED"
            ),
            role_arn=self.create_iam_role_qbus(),
            tags=[CfnTag(
                key="Environment",
                value="Demo"
            )]
        )

        # Creates an Index for the Q Business Application
        cfn_index = qbusiness.CfnIndex(
            self,
            "MyCfnIndex",
            application_id=cfn_application.attr_application_id,
            display_name="QBusinessIndexCDK",
            capacity_configuration=qbusiness.CfnIndex
            .IndexCapacityConfigurationProperty(
                units=1
            ),
            description="Q Business application index created using CDK",
            document_attribute_configurations=[
                qbusiness.CfnIndex.DocumentAttributeConfigurationProperty(
                    name="name",
                    search="ENABLED",
                    type="STRING"
                    )],
            tags=[CfnTag(
                key="Environment",
                value="Demo"
            )],
            type="ENTERPRISE"
        )
        cfn_index.add_dependency(cfn_application)

        # Creates a Retriver for the Q Business Application
        cfn_retriever = qbusiness.CfnRetriever(
            self,
            "MyCfnRetriever",
            application_id=cfn_application.attr_application_id,
            configuration=qbusiness
            .CfnRetriever.RetrieverConfigurationProperty(
                native_index_configuration=qbusiness
                .CfnRetriever.NativeIndexConfigurationProperty(
                    index_id=cfn_index.attr_index_id
                )
            ),
            display_name="QBusinessRetrieverCDK",
            type="NATIVE_INDEX",
            # role_arn="roleArn",
            tags=[CfnTag(
                key="Environment",
                value="Demo"
            )]
        )
        cfn_retriever.add_dependency(cfn_index)

        # Creates the web experience for the Q Business Application
        cfn_web_experience = qbusiness.CfnWebExperience(
            self,
            "MyCfnWebExperience",
            application_id=cfn_application.attr_application_id,
            role_arn=self
            .create_iam_role_qbus_web(cfn_application
                                      .attr_application_id,
                                      kms_key_id_
                                      ),
            sample_prompts_control_mode="ENABLED",
            subtitle="Demostration of Q Business Features",
            tags=[CfnTag(
                key="Environment",
                value="Demo"
            )],
            title="Q Business Demo",
            welcome_message="I'm MARS, an AI assistant. "
            "I can help brainstorm ideas, summarize text, "
            "or answer from your company data."
        )
        cfn_web_experience.add_dependency(cfn_application)

        # Creates an S3 Bucket for Data Source
        data_bucket = s3.Bucket(
            self,
            "MyBucket",
            # removal_policy=RemovalPolicy.DESTROY,
            # auto_delete_objects=True,
            bucket_name="qbus-cde-data-cdk"
        )

        # Creates a BucketDeployment to upload the test document
        s3deploy.BucketDeployment(
            self,
            "DeployDocument",
            sources=[
                s3deploy.Source.asset("doc/")
            ],
            destination_bucket=data_bucket
            # destinationKeyPrefix="/data/"
        )

        # Creates a Bucket for CDE
        cde_bucket = s3.Bucket(
            self,
            "MyBucket1",
            # removal_policy=RemovalPolicy.DESTROY,
            # auto_delete_objects=True,
            bucket_name="qbus-cde-cdk"
        )

        # Creates the IAM role for CDE
        cde_qbus_role = self.create_iam_role_qbus_cde(
            kms_key_id_,
            cde_bucket.bucket_name
            )

        # Creates the Layer, IAM Execution role and Lambda function for CDE
        cde_lambda = self.create_cde_lambda(
            cde_bucket.bucket_name,
            kms_key_id_
            )

        # Creates the S3 Data Source with CDE configuration
        cfn_data_source = qbusiness.CfnDataSource(
            self,
            "MyCfnDataSource",
            application_id=cfn_application.attr_application_id,
            configuration={
                    "type": "S3",
                    "syncMode": "FORCED_FULL_CRAWL",
                    "connectionConfiguration": {
                        "repositoryEndpointMetadata": {
                            "BucketName": f"{data_bucket.bucket_name}"
                        }
                    },
                    "repositoryConfigurations": {
                        "document": {
                            "fieldMappings": [
                                {
                                    "dataSourceFieldName": "s3_document_id",
                                    "indexFieldName": "s3_document_id",
                                    "indexFieldType": "STRING"
                                }
                            ]
                        }
                    },
                    "additionalProperties": {
                        "inclusionPatterns": ["*.pdf", "*.docx"],
                        "exclusionPatterns": ["*.tmp"],
                        # "inclusionPrefixes": ["/important-docs/"],
                        "exclusionPrefixes": ["/temporary/"],
                        # "aclConfigurationFilePath": "/configs/acl.json",
                        # "metadataFilesPrefix": "/metadata/",
                        "maxFileSizeInMegaBytes": "50",
                        "enableDeletionProtection": "false"
                    }
                },
            display_name="S3DataSourceCDETestCDK",
            index_id=cfn_index.attr_index_id,
            description="S3 Data Source to test CDE",
            document_enrichment_configuration=qbusiness
            .CfnDataSource.DocumentEnrichmentConfigurationProperty(
                pre_extraction_hook_configuration=qbusiness
                .CfnDataSource.HookConfigurationProperty(
                    lambda_arn=cde_lambda,
                    role_arn=cde_qbus_role,
                    s3_bucket_name=cde_bucket.bucket_name
                )
            ),
            role_arn=self.create_iam_role_qbus_datasource(
                kms_key_id_,
                cfn_application.attr_application_id,
                cfn_index.attr_index_id,
                data_bucket.bucket_name
                ),
            # sync_schedule="syncSchedule",
            tags=[CfnTag(
                key="Environment",
                value="Demo"
            )],
            # vpc_configuration=qbusiness.CfnDataSource.DataSourceVpcConfigurationProperty(
            #     security_group_ids=["securityGroupIds"],
            #     subnet_ids=["subnetIds"]
            # )
        )

        CfnOutput(self, "DataSourceARN",
                  value=cfn_data_source.attr_data_source_arn)

    # Creates a KMS key to encrypt Q Business Application
    def create_kms_id(self):
        kms_key = kms.Key(self, "KMSKey")
        return kms_key.key_id

    # Creates an IAM for Q Business Application
    def create_iam_role_qbus(self):
        assume_role_policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AmazonQApplicationPermission",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "qbusiness.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole",
                        "Condition": {
                            "StringEquals": {
                                "aws:SourceAccount": f"{self.account}"
                            },
                            "ArnLike": {
                                "aws:SourceArn": (
                                    f"arn:aws:qbusiness:{self.region}:"
                                    f"{self.account}:application/*")
                            }
                        }
                    }
                ]
                }

        policy_document = {
                "Version": "2012-10-17",
                "Statement": [{
                        "Sid": "AmazonQApplicationPutMetricDataPermission",
                        "Effect": "Allow",
                        "Action": [
                            "cloudwatch:PutMetricData"
                        ],
                        "Resource": "*",
                        "Condition": {
                            "StringEquals": {
                                "cloudwatch:namespace": "AWS/QBusiness"
                            }
                        }
                    },
                    {
                        "Sid": "AmazonQApplicationDescribeLogGroupsPermission",
                        "Effect": "Allow",
                        "Action": [
                            "logs:DescribeLogGroups"
                        ],
                        "Resource": "*"
                    },
                    {
                        "Sid": "AmazonQApplicationCreateLogGroupPermission",
                        "Effect": "Allow",
                        "Action": [
                            "logs:CreateLogGroup"
                        ],
                        "Resource": [
                            (f"arn:aws:logs:{self.region}:"
                             f"{self.account}:log-group:/aws/qbusiness/*")
                        ]
                    },
                    {
                        "Sid": "AmazonQApplicationLogStreamPermission",
                        "Effect": "Allow",
                        "Action": [
                            "logs:DescribeLogStreams",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents"
                        ],
                        "Resource": [
                            (f"arn:aws:logs:{self.region}:"
                             f"{self.account}:log-group:"
                             "/aws/qbusiness/*:log-stream:*")
                        ]
                    }
                ]
            }

        iam_role = iam.CfnRole(
            self,
            "QBusinessRoleCDK",
            assume_role_policy_document=assume_role_policy_document,
            description="Q Business Application IAM role from CDK",
            path="/qbusiness/",
            policies=[iam.CfnRole.PolicyProperty(
                policy_document=policy_document,
                policy_name="QBusinessRolePolicyCDK"
            )],
            role_name="QBusinessRoleCDK",
            tags=[CfnTag(
                key="Environment",
                value="Demo"
            )]
        )

        return iam_role.attr_arn

    # Creates an IAM role for Q Business Application Web Experience
    def create_iam_role_qbus_web(self, app_id, key_id):
        assume_role_policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "QBusinessTrustPolicy",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "application.qbusiness.amazonaws.com"
                        },
                        "Action": [
                            "sts:AssumeRole",
                            "sts:SetContext"
                        ],
                        "Condition": {
                            "StringEquals": {
                                "aws:SourceAccount": f"{self.account}"
                                },
                            "ArnEquals": {
                                "aws:SourceArn": (f"arn:aws:qbusiness:"
                                                  f"{self.region}:"
                                                  f"{self.account}:"
                                                  f"application/{app_id}")
                            }
                        }
                    }
                ]
                }

        policy_document = {
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
                            "qbusiness:ListPluginActions",
                            "qbusiness:GetChatControlsConfiguration",
                            "qbusiness:ListRetrievers",
                            "qbusiness:ListAttachments",
                            "qbusiness:GetMedia",
                            "qbusiness:DeleteAttachment"
                        ],
                        "Resource": (f"arn:aws:qbusiness:"
                                     f"{self.region}:"
                                     f"{self.account}:application/{app_id}")
                    },
                    {
                        "Sid": "QBusinessPluginDiscoveryPermissions",
                        "Effect": "Allow",
                        "Action": [
                            "qbusiness:ListPluginTypeMetadata",
                            "qbusiness:ListPluginTypeActions"
                        ],
                        "Resource": "*"
                    },
                    {
                        "Sid": "QBusinessRetrieverPermission",
                        "Effect": "Allow",
                        "Action": [
                            "qbusiness:GetRetriever"
                        ],
                        "Resource": [
                            (f"arn:aws:qbusiness:"
                             f"{self.region}:"
                             f"{self.account}:"
                             f"application/{app_id}"),
                            (f"arn:aws:qbusiness:"
                             f"{self.region}:{self.account}:"
                             f"application/{app_id}/retriever/*")
                        ]
                    },
                    {
                        "Sid": "QBusinessKMSDecryptPermissions",
                        "Effect": "Allow",
                        "Action": [
                            "kms:Decrypt"
                        ],
                        "Resource": [
                            (f"arn:aws:kms:"
                             f"{self.region}:"
                             f"{self.account}:key/{key_id}")
                        ],
                        "Condition": {
                            "StringLike": {
                                "kms:ViaService": [
                                    f"qbusiness.{self.region}.amazonaws.com",
                                    f"qapps.{self.region}.amazonaws.com"
                                ]
                            }
                        }
                    },
                    {
                        "Sid": "QBusinessSetContextPermissions",
                        "Effect": "Allow",
                        "Action": [
                            "sts:SetContext"
                        ],
                        "Resource": [
                            "arn:aws:sts::*:self"
                        ],
                        "Condition": {
                            "StringLike": {
                                "aws:CalledViaLast": [
                                    "qbusiness.amazonaws.com",
                                    "qapps.amazonaws.com"
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
                            "qapps:CreateSubscriptionToken",
                            "qapps:ListCategories"
                        ],
                        "Resource": (f"arn:aws:qbusiness:"
                                     f"{self.region}:"
                                     f"{self.account}:"
                                     f"application/{app_id}")
                    },
                    {
                        "Sid": "QAppsAppUniversalPermissions",
                        "Effect": "Allow",
                        "Action": [
                            "qapps:DisassociateQAppFromUser"
                        ],
                        "Resource": (f"arn:aws:qapps:"
                                     f"{self.region}:"
                                     f"{self.account}:"
                                     f"application/{app_id}/qapp/*")
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
                            "qapps:CreateLibraryItem",
                            "qapps:UpdateLibraryItem",
                            "qapps:StartQAppSession",
                            "qapps:DescribeQAppPermissions",
                            "qapps:UpdateQAppPermissions"
                        ],
                        "Resource": (f"arn:aws:qapps:"
                                     f"{self.region}:"
                                     f"{self.account}:"
                                     f"application/{app_id}/qapp/*"),
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
                            "qapps:StartQAppSession",
                            "qapps:DescribeQAppPermissions"
                        ],
                        "Resource": (f"arn:aws:qapps:"
                                     f"{self.region}:"
                                     f"{self.account}:"
                                     f"application/{app_id}/qapp/*"),
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
                            "qapps:GetQAppSession",
                            "qapps:GetQAppSessionMetadata",
                            "qapps:UpdateQAppSession",
                            "qapps:UpdateQAppSessionMetadata",
                            "qapps:StopQAppSession",
                            "qapps:ListQAppSessionData",
                            "qapps:ExportQAppSessionData"
                        ],
                        "Resource": (f"arn:aws:qapps:{self.region}:"
                                     f"{self.account}:"
                                     f"application/{app_id}/qapp/*/session/*"),
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
                            "qapps:GetQAppSession",
                            "qapps:GetQAppSessionMetadata",
                            "qapps:UpdateQAppSession",
                            "qapps:ListQAppSessionData"
                        ],
                        "Resource": (f"arn:aws:qapps:{self.region}:"
                                     f"{self.account}:"
                                     f"application/{app_id}/qapp/*/session/*"),
                        "Condition": {
                            "StringEqualsIgnoreCase": {
                                "qapps:SessionIsShared": "true"
                            }
                        }
                    },
                    {
                        "Sid": "QBusToQuickSightGenerateEmbedUrlInvocation",
                        "Effect": "Allow",
                        "Action":
                        ["quicksight:"
                         "GenerateEmbedUrlForRegisteredUserWithIdentity"],
                        "Resource": "*",
                        "Condition": {
                            "ForAllValues:StringLike": {
                                "quicksight:AllowedEmbeddingDomains": [
                                    (f"https://*.chat.qbusiness."
                                     f"{self.region}.on.aws/")
                                ]
                            }
                        }
                    }
                ]
            }

        iam_role = iam.CfnRole(
            self,
            "QBusinessRoleWebCDK",
            assume_role_policy_document=assume_role_policy_document,
            description="Q Bus Application Web Experience IAM role from CDK",
            path="/qbusiness/",
            policies=[iam.CfnRole.PolicyProperty(
                policy_document=policy_document,
                policy_name="QBusinessWebRolePolicyCDK"
            )],
            role_name="QBusinessWebRoleCDK",
            tags=[CfnTag(
                key="Environment",
                value="Demo"
            )]
        )

        return iam_role.attr_arn

    # Creates the Lambda layer, IAM execution role and Lambda function for CDE
    def create_cde_lambda(self, cde_bucket, key_id):
        cde_lambda_role = iam.Role(
            self,
            "CDELambdaRoleCDK",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="CDE Lambda Role",
            managed_policies=[
                iam.ManagedPolicy
                .from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "QBusiness-preextraction-policy":
                iam.PolicyDocument(
                        statements=[
                            iam.PolicyStatement(
                                actions=["s3:GetObject",
                                         "s3:PutObject",
                                         "s3:DeleteObject"],
                                resources=[
                                           f"arn:aws:s3:::{cde_bucket}",
                                           f"arn:aws:s3:::{cde_bucket}/*"
                                          ]
                            ),
                            iam.PolicyStatement(
                                actions=["s3:ListBucket"],
                                resources=[
                                        f"arn:aws:s3:::{cde_bucket}"
                                          ]
                            ),
                            iam.PolicyStatement(
                                actions=["kms:Decrypt"],
                                resources=[
                                        (f"arn:aws:kms:"
                                         f"{self.region}:{self.account}:"
                                         f"key/{key_id}")
                                          ]
                            ),
                            iam.PolicyStatement(
                                actions=["bedrock:InvokeModel",
                                         "bedrock:"
                                         "InvokeModelWithResponseStream"],
                                resources=[
                                        (f"arn:aws:bedrock:"
                                         f"{self.region}::"
                                         f"foundation-model/*")
                                          ]
                            )
                                ]
                            )
                    },
            path="/qbusiness/",
            role_name="CDELambdaRoleCDK"
        )

        cde_lambda = lambda_.Function(
            self,
            "cde-lambda",
            handler="cde_lambda.lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            code=lambda_.Code.from_asset(
                "src//lambda",
                bundling=BundlingOptions(
                    image=DockerImage.from_registry("public.ecr.aws/sam/build-python3.13"),
                    platform="linux/amd64",
                    command=[
                        "bash", "-c",
                        "pip3 install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ]
                )
            ),
            role=cde_lambda_role,
            function_name="pre-extraction-lambda-function-cdk",
            timeout=Duration.seconds(120),
            retry_attempts=0
            )

        lambda_.CfnPermission(
            self,
            "qbus-permission-on-cde-lambda",
            action="lambda:InvokeFunction",
            function_name=cde_lambda.function_name,
            principal="qbusiness.amazonaws.com")

        return cde_lambda.function_arn

    # Creates the IAM role for Q Business Data Source
    def create_iam_role_qbus_datasource(self,
                                        key_id,
                                        app_id,
                                        index_id,
                                        data_bucket):
        assume_role_policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AmazonQApplicationPermission",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "qbusiness.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole",
                        "Condition": {
                            "StringEquals": {
                                "aws:SourceAccount": f"{self.account}"
                            },
                            "ArnLike": {
                                "aws:SourceArn": (f"arn:aws:qbusiness:"
                                                  f"{self.region}:"
                                                  f"{self.account}:"
                                                  f"application/{app_id}")
                            }
                        }
                    }
                ]
                }

        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Resource": [f"arn:aws:s3:::{data_bucket}/*"],
                    "Condition": {
                        "StringEquals": {
                            "aws:ResourceAccount": f"{self.account}"
                        }
                    }
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:ListBucket"
                    ],
                    "Resource": [f"arn:aws:s3:::{data_bucket}"],
                    "Condition": {
                        "StringEquals": {
                            "aws:ResourceAccount": f"{self.account}"
                        }
                    }
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "qbusiness:BatchPutDocument",
                        "qbusiness:BatchDeleteDocument",
                        "qbusiness:PutGroup",
                        "qbusiness:CreateUser",
                        "qbusiness:DeleteGroup",
                        "qbusiness:UpdateUser",
                        "qbusiness:ListGroups"
                    ],
                    "Resource": [
                        (f"arn:aws:qbusiness:"
                         f"{self.region}:{self.account}:"
                         f"application/{app_id}"),
                        (f"arn:aws:qbusiness:{self.region}:"
                         f"{self.account}:application/{app_id}"
                         f"/index/{index_id}"),
                        (f"arn:aws:qbusiness:{self.region}:"
                         f"{self.account}:application/{app_id}"
                         f"/index/{index_id}/data-source/*")
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kms:Decrypt"
                    ],
                    "Resource": (f"arn:aws:kms:{self.region}:"
                                 f"{self.account}:key/{key_id}")
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction"
                    ],
                    "Resource": "*"
                }
            ]
        }

        iam_role = iam.CfnRole(
            self,
            "QBusinessRoleDataSourceS3CDK",
            assume_role_policy_document=assume_role_policy_document,
            description="Q Bus Application S3 Data Source IAM role from CDK",
            path="/qbusiness/",
            policies=[iam.CfnRole.PolicyProperty(
                policy_document=policy_document,
                policy_name="QBusinessRoleS3DataSourcePolicyCDK"
            )],
            role_name="QBusinessS3DataSourceRoleCDK",
            tags=[CfnTag(
                key="Environment",
                value="Demo"
            )]
        )

        return iam_role.attr_arn

    # Creates the IAM role for CDE
    def create_iam_role_qbus_cde(self, key_id, cde_bucket):
        assume_role_policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AmazonQApplicationPermission",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "qbusiness.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole",
                        "Condition": {
                            "StringEquals": {
                                "aws:SourceAccount": f"{self.account}"
                            },
                            "ArnLike": {
                                "aws:SourceArn": (f"arn:aws:qbusiness:"
                                                  f"{self.region}:"
                                                  f"{self.account}:"
                                                  f"application/*")
                            }
                        }
                    }
                ]
                }

        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{cde_bucket}/*",
                        f"arn:aws:s3:::{cde_bucket}"
                    ],
                    "Effect": "Allow"
                },
                {
                    "Action": "s3:ListBucket",
                    "Resource": [f"arn:aws:s3:::{cde_bucket}"],
                    "Effect": "Allow"
                },
                {
                    "Action": "lambda:InvokeFunction",
                    "Resource": [
                        (f"arn:aws:lambda:"
                         f"{self.region}:{self.account}:"
                         f"function:pre-extraction-lambda-function-cdk")],
                    "Effect": "Allow"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kms:Decrypt"
                    ],
                    "Resource": (f"arn:aws:kms:"
                                 f"{self.region}:"
                                 f"{self.account}:key/{key_id}")
                },
            ]
        }

        iam_role = iam.CfnRole(
            self,
            "QBusinessRoleCDECDK",
            assume_role_policy_document=assume_role_policy_document,
            description="Q Bus Application S3 Data Source IAM role from CDK",
            path="/qbusiness/",
            policies=[iam.CfnRole.PolicyProperty(
                policy_document=policy_document,
                policy_name="QBusiness-preextraction-policy"
            )],
            role_name="CDEQbusRoleCDK",
            tags=[CfnTag(
                key="Environment",
                value="Demo"
            )]
        )

        return iam_role.attr_arn
