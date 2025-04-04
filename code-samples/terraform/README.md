# Amazon Q Business Terraform Configuration

This Terraform configuration deploys an Amazon Q Business application along with its supporting infrastructure. It sets up a VPC, subnets, security groups, IAM roles, policies, and the Q Business application, index, retriever, and web experience.

## Description

This Terraform code automates the deployment of an Amazon Q Business application within an AWS environment. The configuration includes:

- **VPC and Subnet**: Creates a VPC with a private subnet.
- **Security Group**: Configures a security group for the Q Business data source connector.
- **VPC Endpoint**: Creates an S3 VPC endpoint for secure access to S3 within the VPC.
- **Amazon Q Business Application**: Create the Q Business application.
- **IAM Roles and Policies**: Sets up IAM roles and policies for the web experience and data source access, granting necessary permissions.
- **Web Experience**: Configures a web experience for interacting with the Q Business application.
- **Index and Retriever**: Creates an Amazon Q index and retriever for data ingestion and retrieval.
- **Permissions**: Configures necessary permissions for network interface creation and management.


## Prerequisites

Before running this Terraform code, ensure you have the following:

- **AWS Account**: An active AWS account with permissions to create resources such as VPCs, Subnets, Security Groups, IAM Roles, and Q Business applications.
- **AWS CLI**: The AWS Command Line Interface (CLI) installed and configured with credentials for your AWS account.
- **Terraform**: Terraform installed on your local machine.
- **S3 Bucket**: An existing S3 bucket containing the source data for Amazon Q Business. The bucket name should be specified in the `terraform.tfvars` file or as a command-line variable.
- **AWS Identity Center (SSO)**: Ensure that AWS Identity Center (SSO) is set up in your account, as the configuration relies on it.

Note: The default configuration assumes AWS Identity Center (SSO) is already set up in your account.

## Configuration Options


This Terraform project supports multiple deployment scenarios through the `terraform.tfvars` file:

### 1. Using Existing S3 Bucket with New VPC

```terraform
use_existing_s3_bucket = true
existing_s3_bucket_name = "XXXXXXXXXXXXXXXX"

vpc_option = "create_new"
vpc_cidr_block = "10.0.0.0/16"


 ```

### 2. Creating New S3 Bucket with Existing VPC

```terraform
use_existing_s3_bucket = false
new_s3_bucket_name = "XXXXXXXXXXXXXXXXXX"

vpc_option = "use_existing"
existing_vpc_id = "vpc-xxxxxxxxxxxxx"


 ```

 ### 3. Creating New S3 Bucket without VPC

```terraform

use_existing_s3_bucket = false
new_s3_bucket_name = "XXXXXXXXXXXXXXXXXX"

vpc_option = "no_vpc"


 ```

### 4. Using Existing S3 and No VPC

```terraform

use_existing_s3_bucket = true
use_existing_s3_bucket = "your--s3-bucket"
vpc_option = "no_vpc"


 ```

### 5. Advanced Image Indexing and Index type

```terraform
index_type = "ENTERPRISE" || 'STARTER'

enable_image_extraction = true || false

 ```




## Configuration Variables

| Variable Name | Description | Default | Required |
|---------------|-------------|---------|----------|
| use_existing_s3_bucket | Whether to use an existing S3 bucket | false | yes |
| existing_s3_bucket_name | Name of existing S3 bucket | none | if use_existing_s3_bucket is true |
| new_s3_bucket_name | Name for new S3 bucket to create | none | if use_existing_s3_bucket is false |
| vpc_option | VPC option: "create_new", "use_existing", or "no_vpc" | "create_new" | yes |
| vpc_cidr_block | CIDR block for new VPC | "10.0.0.0/16" | if vpc_option is "create_new" |
| existing_vpc_id | ID of existing VPC | none | if vpc_option is "use_existing" |
| index_type | Amazon Q Business index type | "STARTER" | yes |
| enable_image_extraction | Advanced Visual Indexing Configuration | true | yes |
| sync_schedule | Cron expression for data source sync schedule (e.g., "cron(0 12 * * ? *)" for daily sync at 12 PM UTC) | string | null | no |




## Steps to Run

1. **Clone the Repository**

   To clone only the required Terraform configurations instead of the entire repository, follow the sparse checkout instructions in [sparse-checkout.md](/sparse-checkout.md).


2. **Initialize Terraform**

    Go to terraform fodler inside the cloned repository.

    Initialize the Terraform working directory to download the necessary provider plugins.

    ```
    terraform init
    ```

3. **Plan the Deployment**

    Generate a Terraform plan to preview the changes that will be applied to your AWS environment.

    ```
    terraform plan
    ```

4. **Apply the Configuration**

    Apply the Terraform configuration to create the resources in AWS.

    ```
    terraform apply
    ```

    When prompted, review the changes and type `yes` to confirm the deployment.


5. **Outputs**

    After the deployment completes, Terraform will output any relevant information about the created resources, such as the Q Business application ID and web experience URL.

6. **Troubleshooting**

    ***Common Issues***

    - Error: Failed to create Q Business application : Ensure your AWS account has the necessary service quotas and permissions.

    - Error: VPC endpoint creation failed : Check your VPC configuration and ensure you have permissions to create VPC endpoints.

    - Error: IAM role creation failed : Verify that you have permissions to create IAM roles and policies.


For additional help, check [AWS Q Business documentation](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/what-is.html) or open an issue in this repository.

## Cleaning Up

To remove all resources created by this Terraform configuration, run: 

```
terraform destroy 
```

Review the resources to be destroyed and confirm when prompted.


## License

This library is licensed under the MIT-0 License. See the [LICENSE](/LICENSE) file.
