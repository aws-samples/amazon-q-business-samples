# Confluence OAuth Setup for Amazon Q Business

This AWS sample demonstrates how to set up Confluence Cloud integration with Amazon Q Business using OAuth 2.0 authentication. The sample provides a complete end-to-end setup in a Jupyter notebook format.

## Overview

This sample automates the complete process of:
- Generating Confluence OAuth tokens
- Creating Amazon Q Business application and resources
- Configuring the Confluence data source
- Setting up a web chat interface

## Getting This Sample

### Option 1: Clone Specific Directory (Recommended)

If you only need this Confluence setup sample from the larger amazon-q-business-samples repository, use git sparse checkout to download just this directory:

```bash
# Clone the repository with no files initially
git clone --filter=blob:none --sparse https://github.com/aws-samples/amazon-q-business-samples.git
cd amazon-q-business-samples

# Configure sparse checkout to include only this sample
git sparse-checkout set code-samples/confluence-setup-helper

# Navigate to the sample directory
cd code-samples/confluence-setup-helper
```

### Option 2: Full Repository Clone

```bash
# Clone the entire repository
git clone https://github.com/aws-samples/amazon-q-business-samples.git
cd amazon-q-business-samples/code-samples/confluence-setup-helper
```

## Prerequisites

- **AWS Account** with appropriate permissions for Amazon Q Business
- **Confluence Cloud instance** with admin access
- **Atlassian Developer Console** access to create OAuth apps
- **Python 3.8+** with boto3 and requests libraries
- **AWS CLI configured** with appropriate credentials

## Quick Start

### 1. Set up Atlassian OAuth App

1. Go to [Atlassian Developer Console](https://developer.atlassian.com/console/myapps/)
2. Create a new OAuth 2.0 (3LO) app
3. Configure these settings:
   - **App name**: Choose any name (e.g., "Q Business Confluence Integration")
   - **Callback URL**: See [Callback URL Guidelines](#callback-url-guidelines) below
   - **Permissions**: The notebook will guide you through the required scopes

#### Callback URL Guidelines

**Option 1: Localhost (Recommended for Individual Setup or POC)**
- **URL**: `http://localhost:8080/callback`
- **Pros**: Easy code extraction, works in all browsers, no external dependencies
- **Cons**: Only works for individual/development use
- **Best for**: Personal setups, development, testing

**Option 2: Q Business Web Experience URL (AWS Documentation Standard)**
- **URL**: Your Q Business web experience URL (e.g., `https://abc123.chat.qbusiness.us-west-2.on.aws/`)
- **Pros**: Follows AWS documentation exactly, production-ready
- **Cons**: Harder to extract authorization code from some browsers
- **Best for**: Production deployments, team environments

**Important Notes:**
- The callback URL is **only used during OAuth setup** - Q Business never uses it after you have tokens
- Both approaches work equally well for the final integration
- You can change the callback URL later if needed
- The notebook defaults to localhost for easier code extraction

### 2. Run the Setup Notebook

1. Open `confluence-oauth-setup.ipynb` in Jupyter
2. **Configure your credentials using environment variables**:
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env with your actual values
   # Required: CONFLUENCE_DOMAIN, CONFLUENCE_CLIENT_ID, CONFLUENCE_CLIENT_SECRET
   # Optional: AWS_REGION, CONFLUENCE_CALLBACK_URL
   
   # Install dependencies (includes python-dotenv)
   pip install -r requirements.txt
   ```
3. Execute all cells in order

The notebook will:
- ✅ Generate OAuth authorization URL
- ✅ Guide you through the authorization process
- ✅ Store tokens securely in AWS Secrets Manager
- ✅ Create Q Business application, index, and data source
- ✅ Set up web experience for chat interface
- ✅ Provide testing and validation steps

## What Gets Created

### AWS Resources
- **Q Business Application**: Main application container
- **Q Business Index**: Search index for Confluence content
- **Q Business Retriever**: Enables semantic search
- **Q Business Data Source**: Confluence connection configuration
- **Q Business Web Experience**: Chat interface for users
- **IAM Role**: Service role for Q Business operations
- **Secrets Manager Secret**: Secure OAuth token storage

### Confluence Integration
- **OAuth Access Token**: For API authentication
- **OAuth Refresh Token**: For token renewal
- **Comprehensive Permissions**: 35+ scopes for full content access

## Key Features

- 🚀 **Complete automation** - End-to-end setup in one notebook
- 🔒 **Secure token handling** - AWS Secrets Manager integration
- 🎯 **Optimized scopes** - Pre-configured with Q Business-optimized permissions
- 🌐 **Ready-to-use chat** - Web interface available immediately
- 📊 **Status validation** - Built-in health checks and diagnostics
- 🔄 **Error recovery** - Handles common setup issues automatically

## Configuration

### Environment Variables (Required)

This sample uses environment variables exclusively for security. All configuration is loaded from your `.env` file:

**Required Environment Variables:**
- `CONFLUENCE_DOMAIN` - Your Confluence domain (e.g., `your-company.atlassian.net`)
- `CONFLUENCE_CLIENT_ID` - OAuth client ID from Atlassian Developer Console
- `CONFLUENCE_CLIENT_SECRET` - OAuth client secret from Atlassian Developer Console

**Optional Environment Variables:**
- `CONFLUENCE_CALLBACK_URL` - OAuth callback URL (defaults to `http://localhost:8080/callback`)
- `AWS_REGION` - AWS region for resources (defaults to `us-west-2`)
- `AWS_ACCESS_KEY_ID` - AWS access key (if not using AWS CLI)
- `AWS_SECRET_ACCESS_KEY` - AWS secret key (if not using AWS CLI)
- `AWS_SESSION_TOKEN` - AWS session token (for temporary credentials)

### Required OAuth Scopes

The notebook uses comprehensive Confluence scopes optimized for Q Business:

```
read:content:confluence, read:content-details:confluence, read:space-details:confluence,
read:audit-log:confluence, read:page:confluence, read:attachment:confluence,
read:blogpost:confluence, read:custom-content:confluence, read:comment:confluence,
read:template:confluence, read:label:confluence, read:watcher:confluence,
read:group:confluence, read:relation:confluence, read:user:confluence,
read:configuration:confluence, read:space:confluence, read:space.permission:confluence,
read:space.property:confluence, read:user.property:confluence, read:space.setting:confluence,
read:analytics.content:confluence, read:content.permission:confluence,
read:content.property:confluence, read:content.restriction:confluence,
read:content.metadata:confluence, read:inlinetask:confluence, read:task:confluence,
read:permission:confluence, read:whiteboard:confluence, read:database:confluence,
read:embed:confluence, read:folder:confluence, read:app-data:confluence,
read:email-address.summary, offline_access
```

### AWS Permissions Required

Your AWS credentials need permissions for:
- Amazon Q Business (all operations)
- IAM (role creation and policy attachment)
- AWS Secrets Manager (secret creation and management)
- AWS SSO/Identity Center (if using IDC authentication)

## Usage

After setup completion:

1. **Access the chat interface** using the provided URL
2. **Start data source sync** to index Confluence content
3. **Test with questions** about your Confluence spaces
4. **Monitor sync status** in the Q Business console

## Troubleshooting

### Extracting Authorization Code from Browsers

When using non-localhost callback URLs, you'll need to manually extract the authorization code from the browser. Here are browser-specific tips:

**🔥 Firefox (Most Reliable)**
1. Open Developer Tools (F12) → Network tab **before** clicking authorize
2. Complete the OAuth authorization process
3. Look for the callback request in the network list to see the full URL with code
4. This works even if the callback page shows an error!

**🌐 Chrome/Edge**
1. **Quick method**: Complete authorization and immediately check the address bar for the code
2. **Developer method**: Use F12 → Network tab like Firefox
3. **Mobile**: Long-press the address bar to copy the full URL

**🧭 Safari**
1. Enable Developer menu: Safari → Preferences → Advanced → Show Develop menu
2. Use Develop → Show Web Inspector → Network tab method
3. Look for the callback request to extract the code

**💡 What You're Looking For:**
- URL format: `your-callback-url?code=VERY_LONG_CODE&state=...`
- The authorization code is typically 100+ characters long
- Copy everything after `code=` and before the next `&` (if present)

### Common Issues

**OAuth Authorization Fails**
- Verify client ID and secret are correct
- Ensure callback URL matches exactly: `http://localhost:8080/callback`
- Check that your Atlassian app has the required permissions

**AWS Resource Creation Fails**
- Verify AWS credentials have sufficient permissions
- Check AWS region supports Amazon Q Business
- Ensure IAM Identity Center is set up (if using IDC authentication)

**Index Shows as Inactive**
- Wait 2-5 minutes for index activation
- Check CloudWatch logs for detailed error messages
- Verify IAM role has correct permissions

### Getting Help

- Check the notebook's built-in status validation cells
- Review AWS CloudWatch logs for detailed error information
- Ensure all prerequisites are met before starting

## Security Considerations

- OAuth tokens are stored securely in AWS Secrets Manager
- IAM roles follow least-privilege principles
- Client secrets are never logged or displayed
- All AWS resources are created with appropriate security configurations

## Sample Architecture

```
Confluence Cloud ←→ OAuth Tokens (Secrets Manager) ←→ Q Business Data Source
                                                            ↓
                                                      Q Business Index
                                                            ↓
                                                     Q Business Retriever
                                                            ↓
                                                   Q Business Web Experience
```

## License

This sample is licensed under the MIT-0 License. See the LICENSE file for details.

## Contributing

This is an AWS sample project. For issues or improvements, please follow AWS sample contribution guidelines.
