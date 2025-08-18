# Gmail Infrastructure as Code (IaC) Notebook
This Jupyter notebook automates the setup of AWS Q Business application with Gmail integration using Infrastructure as Code principles.

## Overview
The notebook creates and configures AWS resources needed to integrate Gmail with AWS Q Business, including:

- AWS Secrets Manager secrets for Gmail credentials
- IAM roles for data source access
- Q Business application instance
- Gmail data source configuration

## Prerequisites
- AWS account with appropriate permissions

- IAM role with permissions for:
    - Secrets Manager (create/manage secrets)
    - IAM (create/manage roles)
    - Q Business (create/manage applications)

- Gmail service account credentials

- Python 3.x
- pip (Python package installer)
- Jupyter Notebook or JupyterLab
- (Optional) An IDE that supports Jupyter notebooks (e.g., VS Code, PyCharm, DataSpell)
- AWS CLI configured with appropriate credentials

## Setup Instructions

1. Clone this repository:

```
git clone <repository-url>
cd setup-q-business-gmail

```

2. (Optional) Create and activate a virtual environment:

```
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate

```

3. Install required packages:

`
pip install -r requirements.txt
`

## Usage

You can run the notebook in one of two ways:

### Option 1: Using Jupyter Notebook directly

1. Launch Jupyter Notebook:

`
jupyter notebook
`

2. Open gmailIaC.ipynb in your browser

### Option 2: Using an IDE

1. Open your preferred IDE (e.g., VS Code, PyCharm, DataSpell)
2. Open the gmailIaC.ipynb file
3. Make sure you have the Jupyter extension/plugin installed in your IDE

Then follow the instructions in the notebook to run the Gmail connector

# Gmail Q Business Integration

## Configuration

### Gmail Service Account Setup
Before running the notebook, ensure you have:

- Google Cloud service account with Gmail API and Admin SDK API access
- Service account email (format: `<name>@<project>.iam.gserviceaccount.com`)
- Private key for the service account
- Admin account email for domain-wide delegation and configuring the OAuth scopes

### AWS Configuration
Update the following variables in the notebook:

```python
# AWS Region
region = "<your-aws-region>"

# User configuration
email = "<your-email>"
first_name = "<your-first-name>"
family_name = "<your-last-name>"

# Gmail configuration
client_email = "<service-account-email>"
admin_account_email = "<admin-email>"
private_key = "<private-key>"
```

## Resource Naming
The notebook automatically generates unique resource names using random suffixes:

- Gmail IAM Role: `QBusiness-gmail-DataSource-<suffix>`
- Q Business Application: `my-q-business-application-<suffix>`
- Secrets Manager Secret: `QBusiness-gmail-<suffix>`

## Security Features
- SSL verification disabled for development environments
- Credentials stored securely in AWS Secrets Manager
- Random suffixes prevent resource name conflicts
- Private keys handled as secure strings