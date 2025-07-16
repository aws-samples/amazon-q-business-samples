# Amazon Q Business Box Connector

An end-to-end primer for creating and managing Amazon Q Business applications using the AWS SDK (boto3). This project demonstrates how to programmatically set up and manage Amazon Q Business with Box data sources, offering greater control and automation capabilities compared to the console experience.

## What You'll Learn

- Creating an Amazon Q Business instance with proper IAM roles and permissions
- Setting up a Box data source with customized configuration
- Adding advanced configurations through JSON configuration
- Monitoring and troubleshooting data source synchronization
- Working with indexes and retrievers for effective document search
- Managing AWS session tokens for long-running operations
- Securely storing Box credentials using AWS Secrets Manager

## Why Use This Approach?

- **Automation**: Easily replicate your Q Business setup across multiple environments
- **Advanced Configuration**: Access configuration options through JSON configuration
- **Troubleshooting**: Gain deeper insights into synchronization issues and Box connector behavior
- **Comparison**: Export configurations to compare different instances and identify discrepancies
- **Support**: Generate detailed configuration exports to share with AWS Support for troubleshooting
- **Security**: Secure credential management using AWS Secrets Manager

## Project Structure

```
.
├── box.ipynb          # Main Jupyter notebook containing the Box connector code
├── requirements.txt   # Python package dependencies
└── LICENSE           # MIT-0 License file
```

## Prerequisites

- Python 3.x
- pip (Python package installer)
- Jupyter Notebook or JupyterLab
- (Optional) An IDE that supports Jupyter notebooks (e.g., VS Code, PyCharm, DataSpell)
- AWS CLI configured with appropriate credentials
- Appropriate IAM permissions to create Q Business instances and IAM roles
- Box Developer Account with OAuth 2.0 application credentials
- Box Enterprise ID and API credentials

## Setup Instructions

1. Clone this repository:
```bash
git clone <repository-url>
cd setup-q-biz-box-by-api
```

2. (Optional) Create and activate a virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

You can run the notebook in one of two ways:

### Option 1: Using Jupyter Notebook directly
1. Launch Jupyter Notebook:
```bash
jupyter notebook
```

2. Open `box.ipynb` in your browser

### Option 2: Using an IDE
1. Open your preferred IDE (e.g., VS Code, PyCharm, DataSpell)
2. Open the `box.ipynb` file
3. Make sure you have the Jupyter extension/plugin installed in your IDE

Then follow the instructions in the notebook to run the Box connector

## Features

- Complete end-to-end setup of Amazon Q Business application
- Programmatic creation and management of Box data sources
- Advanced configuration options through JSON
- Data source synchronization monitoring and troubleshooting
- Configuration export and comparison capabilities
- Interactive development through Jupyter notebook interface
- Secure credential management using AWS Secrets Manager
- Box Enterprise integration with proper authentication

## Box Configuration

The notebook includes configuration for:
- Box OAuth 2.0 Client ID and Secret
- Box Enterprise ID
- Private Key authentication
- File type filtering and size limits
- Folder inclusion/exclusion patterns
- Access Control List (ACL) crawling

## Notes

- Make sure to keep your Box API credentials secure
- Store sensitive credentials in AWS Secrets Manager
- Follow Box API rate limits
- Regularly update your dependencies for security and performance improvements
- Ensure your Box application has the necessary scopes for file access

## License

This project is licensed under the MIT-0 License - see the [LICENSE](LICENSE) file for details.

