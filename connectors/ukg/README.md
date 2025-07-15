# UKG Connector

A Python-based connector for integrating with [UKG's](https://www.ukg.com/) API, designed to fetch and process knowledge base articles and sync them with Amazon Q Business for enhanced search capabilities.

## About UKG

UKG (Ultimate Kronos Group) is a leading provider of HR, payroll, and workforce management solutions. Formed through the merger of Ultimate Software and Kronos, UKG serves organizations of all sizes with cloud-based human capital management (HCM) solutions that help businesses manage their people, payroll, and workplace operations more effectively.

For questions reach out to Art Chan <chanart@amazon.com>

## Overview

This connector provides a robust solution for:
- Fetching knowledge base articles from UKG's API
- Managing OAuth2 authentication
- Storing articles in AWS S3
- Syncing content with Amazon Q Business for search functionality

## Prerequisites

- Python 3.6+
- AWS Account with appropriate permissions
- UKG API credentials
- Amazon Q Business setup

## Required AWS Services

- AWS Secrets Manager
- Amazon S3
- Amazon Q Business

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ukg_connector
```

2. Install required dependencies:
```bash
pip install boto3 requests
```

## Configuration

### AWS Secrets Manager Setup

Create a secret in AWS Secrets Manager with the following structure:
```json
{
    "UKG_APPLICATION_ID": "your-application-id",
    "UKG_APPLICATION_SECRET": "your-application-secret",
    "UKG_CLIENT_ID": "your-client-id",
    "UKG_BASE_URL": "https://your-ukg-api-base-url",
    "S3_BUCKET_NAME": "your-s3-bucket-name",
    "Q_BUSINESS_APP_ID": "your-q-business-app-id",
    "Q_BUSINESS_INDEX_ID": "your-q-business-index-id"
}
```

### Required AWS IAM Permissions

The connector requires the following AWS IAM permissions:
- `secretsmanager:GetSecretValue`
- S3 permissions for the specified bucket
- Q Business permissions for the specified application and index

## Usage

1. Set up your AWS credentials:
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=your_region
```

2. Run the connector:
```bash
python ukg_custom_connector.py
```

## Features

- **Secure Authentication**: OAuth2 implementation with automatic token refresh
- **Pagination Support**: Cursor-based pagination for efficient article fetching
- **Version Management**: Handles multiple versions of articles
- **Error Handling**: Comprehensive error handling and logging
- **AWS Integration**: Seamless integration with AWS services
- **Metadata Management**: Rich metadata for Q Business search optimization

## Code Structure

- `UKGCrawler`: Main class handling all UKG API interactions
- `get_secret()`: Utility function for AWS Secrets Manager integration
- `main()`: Entry point for the application

## Error Handling

The connector implements comprehensive error handling for:
- API request failures
- Authentication errors
- S3 upload issues
- Q Business sync problems

All errors are logged with detailed information for debugging.

## Logging

Logging is configured to provide detailed information about:
- API requests and responses
- Authentication status
- Article processing
- Error conditions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request


## Support

For support, please contact Art Chan <chanart@amazon.com>