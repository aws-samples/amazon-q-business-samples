# Amazon Q Business Slack Connector - Programmatic Deployment Examples

This directory contains two complete examples for programmatically deploying Amazon Q Business Slack connectors using AWS APIs and Infrastructure as Code approaches. Both examples create the necessary AWS resources and configure the Slack data source connection to enable your organization to search and chat with Slack content through Amazon Q Business.

## Overview

Amazon Q Business can connect to your Slack workspace to index conversations, files, and other content, making it searchable through natural language queries. These examples demonstrate two different approaches to automate the deployment process:

- **Python API Example** (`example_slack.py`): Direct API integration using boto3
- **CloudFormation Template** (`example-slack-cloudformation.yaml`): Infrastructure as Code approach

Both examples handle the complete setup process, including creating AWS Secrets Manager secrets for Slack tokens, configuring IAM roles with appropriate permissions, and establishing the Slack data source connection.

## Prerequisites

Before using either example, ensure you have:

1. **Amazon Q Business Application and Index**: An existing Amazon Q Business application with at least one index
2. **Slack Workspace Access**: Administrative access to configure a Slack app in your workspace
3. **Slack App Configuration**: Follow the [Amazon Q Business Slack connector documentation](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/slack-connector.html) to create and configure your Slack app with the required scopes and permissions
4. **AWS Credentials**: Appropriate AWS credentials with permissions to create IAM roles, Secrets Manager secrets, and Amazon Q Business data sources

## Example 1: Python API Approach (`example_slack.py`)

The Python example provides maximum flexibility and control over the deployment process. It includes comprehensive error handling, validation, and step-by-step progress reporting.

### Key Features
- **Complete Setup Function**: `setup_complete_slack_connector()` handles end-to-end deployment
- **Modular Design**: Individual functions for creating secrets, IAM roles, and data sources
- **Validation**: Prerequisites validation before attempting deployment
- **Error Handling**: Detailed error messages and troubleshooting guidance
- **Flexibility**: Extensive configuration options for advanced use cases

### Quick Start
```python
from example_slack import setup_complete_slack_connector

response = setup_complete_slack_connector(
    application_id="your-application-id",
    index_id="your-index-id",
    slack_token="xoxb-your-slack-token",
    team_id="your-team-id",
    secret_name="my-slack-secret",
    data_source_name="my-slack-connector"
)
```

### Use Cases
- Integration into existing Python automation workflows
- Custom deployment scripts with specific business logic
- Development and testing environments requiring frequent redeployment
- Organizations requiring programmatic control over connector configuration

## Example 2: CloudFormation Template (`example-slack-cloudformation.yaml`)

The CloudFormation template provides a declarative Infrastructure as Code approach, ideal for consistent deployments across multiple environments and integration with existing AWS deployment pipelines.

### Key Features
- **Declarative Configuration**: Define your complete infrastructure in a single template
- **Parameter Validation**: Built-in validation for all input parameters
- **Resource Dependencies**: Automatic handling of resource creation order and dependencies
- **Stack Management**: Easy updates, rollbacks, and cleanup through CloudFormation
- **Integration Ready**: Compatible with AWS CI/CD pipelines and deployment tools

### Quick Start
```bash
aws cloudformation create-stack \
  --stack-name my-slack-connector \
  --template-body file://example-slack-cloudformation.yaml \
  --parameters \
    ParameterKey=ApplicationId,ParameterValue=your-application-id \
    ParameterKey=IndexId,ParameterValue=your-index-id \
    ParameterKey=SlackToken,ParameterValue=xoxb-your-slack-token \
    ParameterKey=TeamId,ParameterValue=your-team-id \
  --capabilities CAPABILITY_NAMED_IAM
```

### Use Cases
- Production deployments requiring infrastructure consistency
- Multi-environment deployments (dev, staging, production)
- Organizations with established CloudFormation workflows
- Compliance environments requiring infrastructure audit trails

## Configuration Options

Both examples support comprehensive configuration options including:

- **Content Filtering**: Configure which conversation types to crawl (public channels, private channels, direct messages)
- **Date Range**: Specify start dates for content crawling
- **File Handling**: Set maximum file sizes and file type inclusion rules
- **Access Control**: Enable or disable ACL crawling for permission-aware search
- **Sync Scheduling**: Configure automatic synchronization schedules
- **Performance Tuning**: Adjust sync modes for optimal performance

## Slack App Configuration

To obtain the required Slack token and team ID, refer to the [Amazon Q Business Slack connector documentation](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/slack-connector.html) for detailed instructions on:

- Creating a Slack app in your workspace
- Configuring OAuth scopes and permissions
- Installing the app and obtaining access tokens
- Identifying your Slack team ID

## Security Considerations

Both examples implement AWS security best practices:

- **Least Privilege IAM**: IAM roles include only the minimum permissions required
- **Secure Token Storage**: Slack tokens are encrypted in AWS Secrets Manager
- **Condition-Based Access**: IAM policies include condition statements to restrict access
- **Resource-Specific Permissions**: Permissions are scoped to specific Amazon Q Business applications and indexes

## Next Steps

After successful deployment with either approach:

1. **Start Sync**: Initiate your first synchronization through the Amazon Q Business console or API
2. **Monitor Progress**: Track sync job progress and resolve any content-specific issues
3. **Test Search**: Verify that Slack content appears in Amazon Q Business search results
4. **Configure Users**: Set up user access and permissions for your Amazon Q Business application

For detailed configuration options and troubleshooting guidance, consult the [Amazon Q Business documentation](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/). 