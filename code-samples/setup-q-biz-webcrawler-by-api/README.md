# Q-Biz Web Crawler

An end-to-end primer for creating and managing Amazon Q Business applications using the AWS SDK (boto3). This project demonstrates how to programmatically set up and manage Amazon Q Business with web crawler data sources, offering greater control and automation capabilities compared to the console experience.

## What You'll Learn

- Creating an Amazon Q Business instance with proper IAM roles and permissions
- Setting up a web crawler data source with customized configuration
- Adding advanced configurations like crawling delays that aren't available in the console
- Monitoring and troubleshooting data source synchronization
- Working with indexes and retrievers for effective document search
- Managing AWS session tokens for long-running operations

## Why Use This Approach?

- **Automation**: Easily replicate your Q Business setup across multiple environments
- **Advanced Configuration**: Access undocumented features like crawling delays through JSON configuration
- **Troubleshooting**: Gain deeper insights into synchronization issues and crawler behavior
- **Comparison**: Export configurations to compare different instances and identify discrepancies
- **Support**: Generate detailed configuration exports to share with AWS Support for troubleshooting

## Project Structure

```
.
├── webcrawler.ipynb    # Main Jupyter notebook containing the web crawler code
└── requirements.txt    # Python package dependencies
```

## Prerequisites

- Python 3.x
- pip (Python package installer)
- Jupyter Notebook or JupyterLab
- (Optional) An IDE that supports Jupyter notebooks (e.g., VS Code, PyCharm, DataSpell)
- AWS CLI configured with appropriate credentials
- Appropriate IAM permissions to create Q Business instances and IAM roles

## Setup Instructions

1. Clone this repository:
```bash
git clone <repository-url>
cd setup-q-biz-webcrawler-by-api
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

2. Open `webcrawler.ipynb` in your browser

### Option 2: Using an IDE
1. Open your preferred IDE (e.g., VS Code, PyCharm, DataSpell)
2. Open the `webcrawler.ipynb` file
3. Make sure you have the Jupyter extension/plugin installed in your IDE

Then follow the instructions in the notebook to run the web crawler

## Features

- Complete end-to-end setup of Amazon Q Business application
- Programmatic creation and management of web crawler data sources
- Advanced configuration options through JSON
- Data source synchronization monitoring and troubleshooting
- Configuration export and comparison capabilities
- Interactive development through Jupyter notebook interface

## Notes

- Make sure to keep your API credentials secure
- Follow the rate limits of the API you're using
- Regularly update your dependencies for security and performance improvements

