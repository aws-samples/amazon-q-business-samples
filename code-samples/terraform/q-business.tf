terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.89.0"
    }
  }
}

# Configure the AWS provider
provider "aws" {
  region = "us-east-1"
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
data "aws_ssoadmin_instances" "idc" {} 


# S3 Bucket Configuration
variable "use_existing_s3_bucket" {
  type    = bool
  default = false
  description = "Set to true if you want to use an existing S3 bucket."
}

variable "existing_s3_bucket_name" {
  type    = string
  default = ""
  description = "The name of the existing S3 bucket to use. Required if use_existing_s3_bucket is true."
}


variable "new_s3_bucket_name" {
  type    = string
  default = "pablo.terraform.projects"
  description = "The name of the new S3 bucket to create if use_existing_s3_bucket is false."
}

variable "enable_image_extraction" {
  description = "Enable or disable image extraction configuration"
  type        = bool
  default     = false
}

variable "sync_schedule" {
  type        = string
  description = "Cron expression for sync schedule (optional)"
  default     = null
}

resource "aws_s3_bucket" "qbusiness_s3_bucket" {
  count = var.use_existing_s3_bucket ? 0 : 1
  bucket = var.new_s3_bucket_name
}

data "aws_s3_bucket" "existing_s3_bucket_data" {
  count = var.use_existing_s3_bucket ? 1 : 0
  bucket = var.existing_s3_bucket_name
}

locals {
  source_s3_bucket = var.use_existing_s3_bucket ? data.aws_s3_bucket.existing_s3_bucket_data[0].bucket : aws_s3_bucket.qbusiness_s3_bucket[0].bucket
}

resource "random_id" "id" {
  byte_length = 8
}


# VPC Configuration
variable "vpc_option" {
  type    = string
  default = "create_new"
  description = "Choose VPC option: 'create_new', 'use_existing', or 'no_vpc'."
  validation {
    condition     = contains(["create_new", "use_existing", "no_vpc"], var.vpc_option)
    error_message = "Invalid vpc_option. Must be one of 'create_new', 'use_existing', or 'no_vpc'."
  }
}

variable "existing_vpc_id" {
  type    = string
  default = ""
  description = "The ID of the existing VPC to use. Required if vpc_option is 'use_existing'."
}

variable "vpc_cidr_block" {
  type    = string
  default = "10.0.0.0/16"
  description = "The CIDR block for the new VPC if vpc_option is 'create_new'."
}

resource "aws_vpc" "qbusinessvpc" {
  count      = var.vpc_option == "create_new" ? 1 : 0
  cidr_block = var.vpc_cidr_block
  tags = {
    Name = "QBusinessVPC"
  }
}

resource "aws_subnet" "private" {
  count      = var.vpc_option == "create_new" ? 1 : 0
  vpc_id     = aws_vpc.qbusinessvpc[0].id
  cidr_block = "10.0.1.0/24"
}

resource "aws_route_table" "private" {
  count = var.vpc_option == "create_new" ? 1 : 0
  vpc_id = aws_vpc.qbusinessvpc[0].id
}

resource "aws_route_table_association" "private" {
  count          = var.vpc_option == "create_new" ? 1 : 0
  subnet_id      = aws_subnet.private[0].id
  route_table_id = aws_route_table.private[0].id
}

resource "aws_security_group" "q_business_sg" {
  count       = var.vpc_option == "create_new" ? 1 : 0
  name        = "q-business-sg"
  description = "Security group for Amazon Q Business data source connector"
  vpc_id      = aws_vpc.qbusinessvpc[0].id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_vpc_endpoint" "s3" {
  count             = var.vpc_option == "create_new" ? 1 : 0
  vpc_id            = aws_vpc.qbusinessvpc[0].id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private[0].id]
}

data "aws_vpc" "existing_vpc" {
  count = var.vpc_option == "use_existing" ? 1 : 0
  id    = var.existing_vpc_id
}

locals {
  vpc_id = var.vpc_option == "create_new" ? aws_vpc.qbusinessvpc[0].id : (var.vpc_option == "use_existing" ? data.aws_vpc.existing_vpc[0].id : "")
  subnet_id = var.vpc_option == "create_new" ? aws_subnet.private[0].id : ""
  security_group_id = var.vpc_option == "create_new" ? aws_security_group.q_business_sg[0].id : ""
}



# Q index Configuration
variable "index_type" {
  type    = string
  default = "ENTERPRISE"
  description = "The type of Q index to create ('ENTERPRISE' or 'STARTER')."
  validation {
    condition     = contains(["ENTERPRISE", "STARTER"], var.index_type)
    error_message = "Invalid index_type. Must be 'ENTERPRISE' or 'STARTER'."
  }
}



# Create an Amazon Q Business application
resource "awscc_qbusiness_application" "sample-q-biz-app" {
  display_name = "QBusinessApp"
  description  = "QBusiness Application"
  attachments_configuration = {
    attachments_control_mode = "ENABLED"
  }
  identity_center_instance_arn = tolist(data.aws_ssoadmin_instances.idc.arns)[0]  
}


# create an iam role for webexperience
resource "aws_iam_role" "webexperiencerole" {
  name = "qbusiness-webexperiencerole-${random_id.id.hex}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "sts:AssumeRole",
          "sts:SetContext"
        ]
        Effect = "Allow"
        Principal = {
          Service = "application.qbusiness.amazonaws.com"
        }
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:aws:qbusiness:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.sample-q-biz-app.application_id}" 
          }
        }
      }
    ]
  })
}

# create an iam policy for webexperience
resource "aws_iam_policy" "webexperiencepolicy" {
  name   = "qbusiness-webexperience-policy-${random_id.id.hex}"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "QBusinessConversationPermission"
        Effect = "Allow"
        Action = [
          "qbusiness:Chat",
          "qbusiness:ChatSync",
          "qbusiness:ListMessages",
          "qbusiness:ListConversations",
          "qbusiness:DeleteConversation",
          "qbusiness:PutFeedback",
          "qbusiness:GetWebExperience",
          "qbusiness:GetApplication",
          "qbusiness:ListPlugins",
          "qbusiness:ListPluginActions",
          "qbusiness:GetChatControlsConfiguration",
          "qbusiness:ListRetrievers",
          "qbusiness:ListAttachments",
          "qbusiness:GetMedia",
          "qbusiness:DeleteAttachment"
        ]
        Resource = "arn:aws:qbusiness:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.sample-q-biz-app.application_id}"
      },
      {
        Sid    = "QBusinessPluginDiscoveryPermissions"
        Effect = "Allow"
        Action = [
          "qbusiness:ListPluginTypeMetadata",
          "qbusiness:ListPluginTypeActions"
        ]
        Resource = "*"
      },
      {
        Sid    = "QBusinessRetrieverPermission"
        Effect = "Allow"
        Action = [
          "qbusiness:GetRetriever"
        ]
        Resource = [
          "arn:aws:qbusiness:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.sample-q-biz-app.application_id}",
          "arn:aws:qbusiness:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.sample-q-biz-app.application_id}/retriever/*"
        ]
      },
      {
        Sid    = "QAppsResourceAgnosticPermissions"
        Effect = "Allow"
        Action = [
          "qapps:CreateQApp",
          "qapps:PredictQApp",
          "qapps:PredictProblemStatementFromConversation",
          "qapps:PredictQAppFromProblemStatement",
          "qapps:ListQApps",
          "qapps:ListLibraryItems",
          "qapps:CreateSubscriptionToken",
          "qapps:ListCategories"
        ]
        Resource = "arn:aws:qbusiness:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.sample-q-biz-app.application_id}"
      },
      {
        Sid    = "QAppsAppUniversalPermissions"
        Effect = "Allow"
        Action = [
          "qapps:DisassociateQAppFromUser"
        ]
        Resource = "arn:aws:qapps:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.sample-q-biz-app.application_id}/qapp/*"
      },
      {
        Sid    = "QAppsAppOwnerPermissions"
        Effect = "Allow"
        Action = [
          "qapps:GetQApp",
          "qapps:CopyQApp",
          "qapps:UpdateQApp",
          "qapps:DeleteQApp",
          "qapps:ImportDocument",
          "qapps:ImportDocumentToQApp",
          "qapps:CreateLibraryItem",
          "qapps:UpdateLibraryItem",
          "qapps:StartQAppSession",
          "qapps:DescribeQAppPermissions",
          "qapps:UpdateQAppPermissions",
          "qapps:CreatePresignedUrl"
        ]
        Resource = "arn:aws:qapps:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.sample-q-biz-app.application_id}/qapp/*"
        Condition = {
          StringEqualsIgnoreCase = {
            "qapps:UserIsAppOwner" = "true"
          }
        }
      },
      {
        Sid    = "QAppsPublishedAppPermissions"
        Effect = "Allow"
        Action = [
          "qapps:GetQApp",
          "qapps:CopyQApp",
          "qapps:AssociateQAppWithUser",
          "qapps:GetLibraryItem",
          "qapps:CreateLibraryItemReview",
          "qapps:AssociateLibraryItemReview",
          "qapps:DisassociateLibraryItemReview",
          "qapps:StartQAppSession",
          "qapps:DescribeQAppPermissions"
        ]
        Resource = "arn:aws:qapps:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.sample-q-biz-app.application_id}/qapp/*"
        Condition = {
          StringEqualsIgnoreCase = {
            "qapps:AppIsPublished" = "true"
          }
        }
      },
      {
        Sid    = "QAppsAppSessionModeratorPermissions"
        Effect = "Allow"
        Action = [
          "qapps:ImportDocument",
          "qapps:ImportDocumentToQAppSession",
          "qapps:GetQAppSession",
          "qapps:GetQAppSessionMetadata",
          "qapps:UpdateQAppSession",
          "qapps:UpdateQAppSessionMetadata",
          "qapps:StopQAppSession",
          "qapps:ListQAppSessionData",
          "qapps:ExportQAppSessionData",
          "qapps:CreatePresignedUrl"
        ]
        Resource = "arn:aws:qapps:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.sample-q-biz-app.application_id}/qapp/*/session/*"
        Condition = {
          StringEqualsIgnoreCase = {
            "qapps:UserIsSessionModerator" = "true"
          }
        }
      },
      {
        Sid    = "QAppsSharedAppSessionPermissions"
        Effect = "Allow"
        Action = [
          "qapps:ImportDocument",
          "qapps:ImportDocumentToQAppSession",
          "qapps:GetQAppSession",
          "qapps:GetQAppSessionMetadata",
          "qapps:UpdateQAppSession",
          "qapps:ListQAppSessionData",
          "qapps:CreatePresignedUrl"
        ]
        Resource = "arn:aws:qapps:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.sample-q-biz-app.application_id}/qapp/*/session/*"
        Condition = {
          StringEqualsIgnoreCase = {
            "qapps:SessionIsShared" = "true"
          }
        }
      },
      {
        Sid    = "QBusinessToQuickSightGenerateEmbedUrlInvocation"
        Effect = "Allow"
        Action = [
          "quicksight:GenerateEmbedUrlForRegisteredUserWithIdentity"
        ]
        Resource = "*",
        Condition = {
          "ForAllValues:StringLike" = {
            "quicksight:AllowedEmbeddingDomains" = [
              "https://*.chat.qbusiness.${data.aws_region.current.name}.on.aws/"
            ]
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "webexperience_policy_attach" {
  role       = aws_iam_role.webexperiencerole.name  
  policy_arn = aws_iam_policy.webexperiencepolicy.arn 
}

# create a web experience
resource "awscc_qbusiness_web_experience" "q-webexp" {
  application_id              = awscc_qbusiness_application.sample-q-biz-app.application_id  
  role_arn                    = aws_iam_role.webexperiencerole.arn
  sample_prompts_control_mode = "ENABLED"
  subtitle                    = "Drop a file and ask questions"
  title                       = "Amazon Q Business App"
  welcome_message             = "Welcome, to the Q Business web experience"
}

# create a Q index
resource "awscc_qbusiness_index" "q-index" {
  application_id = awscc_qbusiness_application.sample-q-biz-app.application_id   
  display_name   = "q_index"
  description    = "QBusiness Index"
  type           = var.index_type
  capacity_configuration = {
    units = 1
  }
}

# create a Q retriever
resource "awscc_qbusiness_retriever" "q-retrieve" {
  application_id = awscc_qbusiness_application.sample-q-biz-app.application_id 
  display_name   = "q_retriever"
  type           = "NATIVE_INDEX"
  configuration = {
    native_index_configuration = {
      index_id = awscc_qbusiness_index.q-index.index_id
    }
  }
}

# create an iam role for datasource
resource "aws_iam_role" "datasourcerole" {
  name = "qbussiness-datasource-role-${random_id.id.hex}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "sts:AssumeRole"
          ]
        Effect = "Allow"
        Principal = {
          Service = "qbusiness.amazonaws.com"
        }
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:aws:qbusiness:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.sample-q-biz-app.application_id}"
          }
        }
      }
    ]
  })
}

# create a iam policy
resource "aws_iam_policy" "datasourcepolicy" {
  name   = "qbusiness-datasource-policy-${random_id.id.hex}"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = "arn:aws:s3:::${local.source_s3_bucket}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = "arn:aws:s3:::${local.source_s3_bucket}"
      },
      {
        Effect = "Allow"
        Action = [
          "qbusiness:BatchPutDocument",
          "qbusiness:BatchDeleteDocument",
          "qbusiness:PutGroup",
          "qbusiness:CreateUser",
          "qbusiness:DeleteGroup",
          "qbusiness:UpdateUser",
          "qbusiness:ListGroups"
        ]
        Resource = [
          "arn:aws:qbusiness:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.sample-q-biz-app.application_id}",
          "arn:aws:qbusiness:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.sample-q-biz-app.application_id}/index/${awscc_qbusiness_index.q-index.index_id}", 
          "arn:aws:qbusiness:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.sample-q-biz-app.application_id}/index/${awscc_qbusiness_index.q-index.index_id}/data-source/*" 
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:key/24a2c5c2-01d7-4a58-a459-0f327ec0bf47"
      },
      {
            "Sid": "AllowsAmazonQToCreateAndDeleteNI",
            "Effect": "Allow",
            "Action": [
                "ec2:CreateNetworkInterface",
                "ec2:DeleteNetworkInterface"
            ],
            "Resource": [
                "arn:aws:ec2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:subnet/${local.subnet_id}",
                "arn:aws:ec2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:security-group/${local.security_group_id}"
            ]
        },
        {
            "Sid": "AllowsAmazonQToCreateAndDeleteNIForSpecificTag",
            "Effect": "Allow",
            "Action": [
                "ec2:CreateNetworkInterface",
                "ec2:DeleteNetworkInterface"
            ],
            "Resource": "arn:aws:ec2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:network-interface/*",
            "Condition": {
                "StringLike": {
                    "aws:RequestTag/AMAZON_Q": "qbusiness_${data.aws_caller_identity.current.account_id}_${awscc_qbusiness_application.sample-q-biz-app.application_id}_*"
                },
                "ForAllValues:StringEquals": {
                    "aws:TagKeys": [
                        "AMAZON_Q"
                    ]
                }
            }
        },
           {
            "Sid": "AllowsAmazonQToCreateTags",
            "Effect": "Allow",
            "Action": [
                "ec2:CreateTags"
            ],
            "Resource": "arn:aws:ec2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:network-interface/*",
            "Condition": {
                "StringEquals": {
                    "ec2:CreateAction": "CreateNetworkInterface"
                }
            }
        },
         {
            "Sid": "AllowsAmazonQToCreateNetworkInterfacePermission",
            "Effect": "Allow",
            "Action": [
                "ec2:CreateNetworkInterfacePermission"
            ],
            "Resource": "arn:aws:ec2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:network-interface/*",
            "Condition": {
                "StringLike": {
                    "aws:ResourceTag/AMAZON_Q": "qbusiness_${data.aws_caller_identity.current.account_id}_${awscc_qbusiness_application.sample-q-biz-app.application_id}_*"
                }
            }
        },
        {
            "Sid": "AllowsAmazonQToDescribeResourcesForVPC",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeNetworkInterfaces",
                "ec2:DescribeAvailabilityZones",
                "ec2:DescribeNetworkInterfaceAttribute",
                "ec2:DescribeVpcs",
                "ec2:DescribeRegions",
                "ec2:DescribeNetworkInterfacePermissions",
                "ec2:DescribeSubnets"
            ],
            "Resource": "*"
        }
    ]
  })
}

# create iam policy attachment
resource "aws_iam_role_policy_attachment" "datasource_policy_attach" {
  role       = aws_iam_role.datasourcerole.name  
  policy_arn = aws_iam_policy.datasourcepolicy.arn 
}

# create a S3 datasource
resource "awscc_qbusiness_data_source" "s3_source" {
  application_id = awscc_qbusiness_application.sample-q-biz-app.application_id 
  display_name   = "s3-source"
  index_id       = awscc_qbusiness_index.q-index.index_id  
  role_arn       = aws_iam_role.datasourcerole.arn
  sync_schedule  = try(var.sync_schedule, null)
  configuration   = jsonencode({
    type        = "S3"
    bucket_name = local.source_s3_bucket
    version  = "1.0.0"
    syncMode = "FORCED_FULL_CRAWL"
    connectionConfiguration = {
      repositoryEndpointMetadata = {
        BucketName = local.source_s3_bucket
      }
    }
    repositoryConfigurations = {
      document = {
        fieldMappings = [
          {
            dataSourceFieldName = "s3_document_id"
            indexFieldType      = "STRING"
            indexFieldName      = "s3_document_id"
          }
        ]
      }
    }
  })
  media_extraction_configuration = var.enable_image_extraction ? {
    image_extraction_configuration = {
      image_extraction_status = "ENABLED"
    }
  } : null
 vpc_configuration = var.vpc_option == "create_new" ? {
    subnet_ids         = [aws_subnet.private[0].id]
    security_group_ids = [aws_security_group.q_business_sg[0].id]
  } : null
}
