# Custom WebCrawler

A specialized web crawler designed for Q Business, addressing limitations in the native web crawler. This crawler is specifically engineered to handle modern web protection mechanisms and complex JavaScript-rendered content.

For questions, reach out to: Art Chan <chanart@amazon.com>

## License

This project is licensed under the MIT-0 (MIT No Attribution) License - see the [LICENSE](LICENSE) file for details.

## Overview

Custom WebCrawler is an alternative web crawler for Q Business that provides enhanced capabilities for crawling modern websites. It addresses several limitations of the native Q Business web crawler:

- JavaScript rendering support
- Cloudflare and Akamai protection bypass
- Cookie and session management
- Intelligent content handling
- Configurable depth control
- URL pattern filtering
- Detailed logging and statistics

The crawler stores all crawled content in Amazon S3, with properly formatted metadata files that are compatible with Amazon Q Business. This allows you to easily ingest the crawled data using the S3 connector in Q Business, ensuring that source links and metadata are correctly preserved. The crawler has been tested run on x86_64 systems running Amazon Linux.

## Technical Challenges

Modern websites employ sophisticated protection mechanisms that can prevent traditional web crawlers from accessing content. The main challenges include:

### Cloudflare Protection
Cloudflare implements multiple layers of protection:
1. **JavaScript Challenges**: Requires executing JavaScript to solve mathematical problems
2. **Browser Fingerprinting**: Checks for browser-like behavior and characteristics
3. **Rate Limiting**: Blocks requests that exceed certain thresholds
4. **Cookie Management**: Requires proper handling of security cookies
5. **TLS Fingerprinting**: Detects non-browser TLS implementations

### Akamai Protection
Akamai's protection includes:
1. **Bot Detection**: Identifies automated traffic patterns
2. **Request Validation**: Verifies request headers and parameters
3. **Session Management**: Requires maintaining valid sessions
4. **Geographic Restrictions**: May block requests from certain regions
5. **Device Fingerprinting**: Detects non-standard device characteristics

## Protection Bypass Techniques

Custom WebCrawler employs multiple techniques to bypass these protection mechanisms:

### Browser Emulation
- Modern Chrome user agent strings
- Realistic HTTP headers
- Proper TLS implementation
- Viewport and screen size emulation
- JavaScript execution environment

### Cookie Management
- Per-domain cookie storage
- Automatic cookie updates
- Session persistence
- Security cookie handling
- Cookie validation

### Request Patterns
- Randomized delays between requests
- Rate limiting compliance
- Natural request patterns
- Proper HTTP method usage
- Header consistency

### JavaScript Handling
- Full JavaScript execution
- DOM manipulation support
- Event handling
- AJAX request support
- Dynamic content rendering

### Additional Techniques
- Two-stage Cloudflare detection
- Extended wait times for challenges
- Resource timeout management
- Error recovery mechanisms
- Detailed logging for debugging

## Features

### Core Functionality
- Web crawling with Scrapy and JavaScript rendering via Splash
- S3 storage integration with metadata
- Polite crawling with rate limiting and domain-based delays
- Respects robots.txt
- Automatic retry on failures
- Comprehensive logging and progress tracking

### Advanced Features
- Cloudflare protection bypass with browser emulation
- Cookie management and session handling
- Content type detection for various file formats
- URL pattern filtering (include/exclude)
- Configurable crawl depth
- Domain and TLD-based crawling restrictions

### Storage Features
- Content stored with consistent hashing
- S3 object metadata for quick access
- Separate metadata files for Amazon Q Business
- Organized storage by domain
- Automatic file extension detection

## Requirements

### System Requirements
- x86_64 Linux environment (currently required, containerization planned for future releases)
- Docker installed and running
- Python 3.10 or higher
- AWS CLI configured with appropriate credentials

### Python Dependencies
- scrapy
- scrapy-splash
- boto3
- requests
- beautifulsoup4

## Setup

1. **Install Python Dependencies**
   ```bash
   # Create and activate virtual environment (recommended)
   python3 -m venv venv
   source venv/bin/activate

   # Install required packages
   pip install scrapy scrapy-splash boto3 requests beautifulsoup4
   ```

2. **Configure AWS Credentials**
   ```bash
   # Install AWS CLI if not already installed
   sudo yum update
   sudo yum install awscli

   # Configure AWS credentials
   aws configure
   # Enter your AWS Access Key ID
   # Enter your AWS Secret Access Key
   # Enter your default region (e.g., us-east-1)
   # Enter your preferred output format (json)
   ```

3. **Start Splash Server**
   ```bash
   # Install Docker if not already installed
   sudo yum install -y yum-utils
   sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
   sudo yum install docker-ce docker-ce-cli containerd.io
   sudo systemctl start docker
   sudo systemctl enable docker

   # Pull the Splash Docker image
   docker pull scrapinghub/splash

   # Start Splash container
   docker run -d -p 8050:8050 --name splash scrapinghub/splash
   ```

4. **Verify Setup**
   ```bash
   # Check if Splash is running
   curl http://localhost:8050/health

   # Test AWS credentials
   aws sts get-caller-identity
   ```

> **Note**: Currently, Custom WebCrawler must be run on an x86_64 Linux instance. We plan to containerize the entire application in a future release to simplify setup and make it more portable across different environments.

## Usage

### Basic Usage
```bash
python custom_webcrawler.py --start_urls <urls> --s3_bucket <bucket>
```

### Advanced Options
- `--depth`: Maximum crawl depth (default: 10)
- `--include_patterns`: Glob patterns for URLs to include
- `--exclude_patterns`: Glob patterns for URLs to exclude

### URL Pattern Examples
- Include only blog pages: `--include_patterns "*/blog/*"`
- Exclude admin pages: `--exclude_patterns "*/admin/*"`

## Output

### Storage Structure
- Content files: `<domain>/<url-hash>.<extension>`
- Metadata files: `<domain>/<url-hash>.<extension>.metadata.json`

### Metadata Content
- Category
- Creation and update timestamps
- Source URI
- Version
- View count
- Crawl timestamp
- Domain
- Title
- Content type

### S3 Object Metadata
All metadata is also stored as S3 object metadata for quick access without downloading the separate metadata file.

## Logging

The crawler provides detailed logging in two formats:

1. **Console Output**:
   - Real-time progress updates
   - Visual separators for each page
   - Success/failure status
   - Current depth level
   - Processing time
   - Progress statistics

2. **Log File** (`custom_webcrawler-YYYYMMDD_HHMMSS.log`):
   - Timestamped log file (created at crawl start)
   - Detailed request/response information
   - Error messages and stack traces
   - Cookie management details
   - Full debug information

The log file includes:
- Request details (URL, method, headers)
- Response information (status, headers, content preview)
- Error details with full stack traces
- Cookie management operations
- URL pattern filtering decisions
- Cloudflare detection and handling
- Performance metrics

