"""
Custom WebCrawler - Advanced Web Crawler with S3 Storage
Author: Art Chan (chanart@amazon.com)

License: MIT-0 (MIT No Attribution)
Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Usage:
    python custom_webcrawler.py --start_urls https://example1.com \
        https://example2.com --s3_bucket your-bucket-name

Required Arguments:
    --start_urls: One or more URLs to start crawling from
    --s3_bucket: Name of the S3 bucket to store crawled content

System Requirements:
    - x86_64 architecture (not compatible with ARM64/Apple Silicon because
      of Splash docker package)
    - Docker installed and running

Environment Setup:
    AWS Credentials (Required):
    export AWS_ACCESS_KEY_ID='your-access-key'
    export AWS_SECRET_ACCESS_KEY='your-secret-key'
    export AWS_DEFAULT_REGION='your-region'  # e.g., us-west-2

    Splash Setup (Required):
    - Install Docker:
      # Ubuntu/Debian
      sudo apt-get update
      sudo apt-get install docker.io
      sudo usermod -aG docker $USER
      newgrp docker

      # RHEL/CentOS
      sudo yum install docker
      sudo systemctl start docker
      sudo systemctl enable docker
      sudo usermod -aG docker $USER
      newgrp docker

    - Run Splash:
      # Clean up any existing containers
      docker stop splash || true
      docker rm splash || true

      # Start Splash container
      docker run -d \
        --name splash \
        -p 8050:8050 \
        --shm-size=2g \
        --memory=2g \
        --memory-swap=2g \
        scrapinghub/splash

      # Check if it's running
      docker ps | grep splash

      # View logs if needed
      docker logs splash

    - Stop Splash when done:
      docker stop splash
      docker rm splash
"""

import argparse
import logging
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime
from urllib.parse import urlparse

import boto3
import botocore
import pkg_resources
import requests
from scrapy.crawler import CrawlerProcess
from scrapy.utils.log import configure_logging

# Import the spider class from the separate module
from spider import CustomWebCrawlerPlus

# Spider settings
SPIDER_SETTINGS = {
    "ROBOTSTXT_OBEY": True,
    "CONCURRENT_REQUESTS": 16,
    "DOWNLOAD_DELAY": 2,
    "COOKIES_ENABLED": True,  # Enable cookie handling
    "COOKIES_DEBUG": True,  # Enable cookie debugging
    "DOWNLOAD_TIMEOUT": 60,
    "RETRY_TIMES": 3,
    "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408, 429],
    "DEFAULT_REQUEST_HEADERS": {
        "Accept": "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "TE": "trailers",
        "Pragma": "no-cache",
        "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", '
                     '"Chromium";v="121"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "DNT": "1",
    },
    "SPLASH_URL": "http://localhost:8050",
    "DOWNLOADER_MIDDLEWARES": {
        "scrapy_splash.SplashCookiesMiddleware": 723,
        "scrapy_splash.SplashMiddleware": 725,
        "scrapy.downloadermiddlewares.httpcompression."
        "HttpCompressionMiddleware": 810,
        "scrapy.downloadermiddlewares.cookies.CookiesMiddleware": 700,
        # Add cookies middleware
    },
    "SPIDER_MIDDLEWARES": {
        "scrapy_splash.SplashDeduplicateArgsMiddleware": 100,
    },
    "DUPEFILTER_CLASS": "scrapy_splash.SplashAwareDupeFilter",
    "HTTPCACHE_STORAGE": "scrapy_splash.SplashAwareFSCacheStorage",
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    "LOG_FILE": "crawler.log",
}


def check_architecture():
    """Check if running on x86_64 architecture."""
    if platform.machine() != "x86_64":
        print("\nError: This crawler requires x86_64 architecture.")
        print(f"Current architecture: {platform.machine()}")
        print("\nThe Splash browser engine is only available for "
              "x86_64 architecture.")
        print("Please run this crawler on an x86_64 machine or "
              "EC2 instance.")
        sys.exit(1)


def check_docker():
    """Check if Docker is installed and running."""
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=False)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("\nError: Docker is not installed or not running.")
        print("\nTo fix this:")
        print("1. Install Docker:")
        if os.path.exists("/etc/debian_version"):  # Debian/Ubuntu
            print("   sudo apt-get update")
            print("   sudo apt-get install docker.io")
            print("   # Add your user to the docker group to run docker "
                  "without sudo")
            print("   sudo usermod -aG docker $USER")
            print("   # Apply the new group membership (or log out and "
                  "back in)")
            print("   newgrp docker")
        else:  # RHEL/CentOS
            print("   sudo yum install docker")
            print("   sudo systemctl start docker")
            print("   sudo systemctl enable docker")
            print("   # Add your user to the docker group to run docker "
                  "without sudo")
            print("   sudo usermod -aG docker $USER")
            print("   # Apply the new group membership (or log out and "
                  "back in)")
            print("   newgrp docker")
        print("\n2. Start Docker and verify it's running:")
        print("   docker info")
        return False


def check_splash_container():
    """Check if Splash container is running."""
    try:
        # Check if container exists and is running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=splash", "--format",
             "{{.Status}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if "Up" in result.stdout:
            return True, None

        # Check if container exists but is stopped
        result = subprocess.run(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                "name=splash",
                "--format",
                "{{.Status}}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            # Get container logs for debugging
            logs = subprocess.run(
                ["docker", "logs", "splash"], capture_output=True,
                text=True, check=False
            )
            return (
                False,
                f"""Splash container exists but is not running. To start it:
   docker start splash

Container logs: 
{logs.stdout}

If the container keeps crashing, try these steps:
1. Remove the existing container:
   docker rm splash

2. Start a new container with proper configuration:
   docker run -d \
     --name splash \
     -p 8050:8050 \
     --shm-size=2g \
     --memory=2g \
     --memory-swap=2g \
     scrapinghub/splash

3. Check the logs: 
   docker logs splash""",
            )

        return (
            False,
            """Splash container is not installed.

To install and run it:
   # Clean up any existing containers
   docker stop splash || true
   docker rm splash || true

   # Start Splash container
   docker run -d \
     --name splash \
     -p 8050:8050 \
     --shm-size=2g \
     --memory=2g \
     --memory-swap=2g \
     scrapinghub/splash

   # Check if it's running
   docker ps | grep splash

   # View logs if needed
   docker logs splash
""",
        )
    except subprocess.SubprocessError as e:
        return False, f"Error checking Splash container status: {str(e)}"
    except (OSError, IOError) as e:
        return False, f"Unexpected error checking Splash container: {str(e)}"


def check_splash():
    """Check if Splash is running and accessible."""
    try:
        # Try to render a simple test page
        response = requests.get(
            "http://localhost:8050/render.html",
            params={"url": "http://example.com", "timeout": 5},
            timeout=10,
        )
        return (response.status_code == 200 and
                "Example Domain" in response.text)
    except (requests.RequestException, ImportError):
        return False


def check_python_packages():
    """Check if all required Python packages are installed."""
    requirements_file = "requirements.txt"

    if not os.path.exists(requirements_file):
        print(f"\nError: {requirements_file} not found in the current "
              "directory.")
        print(
            "Please ensure requirements.txt exists with all required "
            "package versions."
        )
        return False

    try:
        with open(requirements_file, "r", encoding="utf-8") as f:
            required_packages = [
                line.strip() for line in f
                if line.strip() and not line.startswith("#")
            ]
    except (OSError, IOError) as e:
        print(f"\nError reading {requirements_file}: {str(e)}")
        return False

    missing_packages = []
    version_mismatches = []

    for package in required_packages:
        try:
            pkg_resources.require(package)
        except pkg_resources.DistributionNotFound:
            missing_packages.append(package)
        except pkg_resources.VersionConflict as e:
            # Show both required and installed versions
            version_mismatches.append(
                {
                    "package": package,
                    "required": (package.split("==")[1] if "==" in package
                                 else "latest"),
                    "installed": e.dist.version,
                }
            )

    if missing_packages or version_mismatches:
        print("\nPackage check failed:")

        if missing_packages:
            print("\nMissing packages:")
            for package in missing_packages:
                print(f" - {package}")

        if version_mismatches:
            print("\nVersion mismatches:")
            for mismatch in version_mismatches:
                print(f" - {mismatch['package']}")
                print(f"    Required: {mismatch['required']}")
                print(f"    Installed: {mismatch['installed']}")

        print("\nPlease install/update packages using:")
        print("pip install -r requirements.txt")
        return False

    return True


def check_s3_bucket(bucket_name):
    """Check if the specified S3 bucket exists and is accessible."""
    try:
        s3_client = boto3.client("s3")
        s3_client.head_bucket(Bucket=bucket_name)
        return True
    except botocore.exceptions.ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "404":
            print(f"\nError: S3 bucket '{bucket_name}' does not exist.")
        elif error_code == "403":
            print(f"\nError: Access denied to S3 bucket '{bucket_name}'.")
            print("Please check your AWS credentials and bucket "
                  "permissions.")
        else:
            print(f"\nError accessing S3 bucket '{bucket_name}': {str(e)}")
        return False
    except (OSError, IOError, botocore.exceptions.BotoCoreError) as e:
        print(f"\nError checking S3 bucket '{bucket_name}': {str(e)}")
        return False


def check_domain_resolvability(urls):
    """Check if all start URLs have resolvable domains."""
    unresolvable_domains = []

    for url in urls:
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            # Try to resolve the domain
            socket.gethostbyname(domain)
        except socket.gaierror:
            unresolvable_domains.append(domain)
        except (ValueError, TypeError) as e:
            print(f"\nError checking domain for {url}: {str(e)}")
            unresolvable_domains.append(domain)

    if unresolvable_domains:
        print("\nThe following domains could not be resolved:")
        for domain in unresolvable_domains:
            print(f" - {domain}")
        print("\nPlease check that:")
        print("1. The domains are spelled correctly")
        print("2. The domains are active and accessible")
        print("3. Your DNS settings are correct")
        return False

    return True


def check_environment():
    """Check if all required components are available."""
    print("\n=== Environment Check ===")

    # Check architecture
    print("\n1. Checking system architecture...")
    if platform.machine() != "x86_64":
        print("❌ Architecture check failed")
        print("Error: This script requires an x86_64 architecture.")
        print(
            "Please run this script on an x86_64 machine or use a "
            "compatible environment."
        )
        sys.exit(1)
    print("✅ Architecture check passed")

    # Check Docker
    print("\n2. Checking Docker installation...")
    if not check_docker():
        print("❌ Docker check failed")
        print("Error: Docker is not installed or not running.")
        print("Please install Docker and ensure it's running before "
              "continuing.")
        sys.exit(1)
    print("✅ Docker check passed")

    # Check Splash container
    print("\n3. Checking Splash container...")
    splash_status, splash_error = check_splash_container()
    if not splash_status:
        print("❌ Splash container check failed")
        print(f"Error: {splash_error}")
        print("\nTo install and run Splash container:")
        print(
            "1. Run: docker run -d -p 8050:8050 --name splash "
            "--shm-size=1g scrapinghub/splash"
        )
        print("2. Verify it's running: docker ps | grep splash")
        print("3. Check logs if needed: docker logs splash")
        sys.exit(1)
    print("✅ Splash container check passed")

    # Check Splash service
    print("\n4. Checking Splash service...")
    if not check_splash():
        print("❌ Splash service check failed")
        print("Error: Splash service is not responding.")
        print("Please check if the Splash container is running "
              "properly.")
        print("You can check the logs with: docker logs splash")
        sys.exit(1)
    print("✅ Splash service check passed")

    # Check Python packages
    print("\n5. Checking required Python packages...")
    if not check_python_packages():
        print("❌ Python packages check failed")
        print("Error: Some required Python packages are missing.")
        print("Please install all required packages using pip:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    print("✅ Python packages check passed")

    print("\n=== All environment checks passed successfully! ===\n")
    return True


def check_additional_requirements(start_urls=None, s3_bucket=None):
    """Check additional requirements after package imports."""
    if not start_urls and not s3_bucket:
        return True

    print("\n=== Additional Requirements Check ===")

    # Check S3 bucket if provided
    if s3_bucket:
        print("\n1. Checking S3 bucket...")
        if not check_s3_bucket(s3_bucket):
            print("❌ S3 bucket check failed")
            sys.exit(1)
        print("✅ S3 bucket check passed")

    # Check domain resolvability if start URLs are provided
    if start_urls:
        print("\n2. Checking domain resolvability...")
        if not check_domain_resolvability(start_urls):
            print("❌ Domain resolvability check failed")
            sys.exit(1)
        print("✅ Domain resolvability check passed")

    print("\n=== All additional requirements passed successfully! ===\n")
    return True


# Run environment checks before importing any other packages
check_environment()


def run_spider(
    start_urls, s3_bucket, max_depth=10, include_patterns=None,
    exclude_patterns=None
):
    """Run the spider with the given start URLs and S3 bucket."""
    # Get current timestamp for log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"custom_webcrawler-{timestamp}.log"

    # Configure logging to both file and console
    configure_logging(install_root_handler=False)

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    console_formatter = logging.Formatter("%(message)s")

    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    print("\n=== Starting Custom WebCrawler Plus ===")
    print(f"Start URLs: {start_urls}")
    print(f"S3 Bucket: {s3_bucket}")
    print(f"Maximum depth: {max_depth}")
    if include_patterns:
        print(f"Include patterns: {include_patterns}")
    if exclude_patterns:
        print(f"Exclude patterns: {exclude_patterns}")
    print(f"Log file: {log_file}")
    print("==============================\n")

    # Get spider settings
    settings = SPIDER_SETTINGS.copy()

    # Create and start the crawler process
    process = CrawlerProcess(settings)
    process.crawl(
        CustomWebCrawlerPlus,
        start_urls=start_urls,
        s3_bucket=s3_bucket,
        max_depth=max_depth,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )
    process.start()  # This will block until the crawling is finished

    print("\n=== Crawling completed ===\n")


def main():
    """Main function to parse arguments and run the spider."""
    parser = argparse.ArgumentParser(
        description=(
            "Custom WebCrawler Plus - Web Crawler with Splash and "
            "S3 Storage"
        )
    )
    parser.add_argument(
        "--start_urls", nargs="+", required=True,
        help="Starting URLs to crawl"
    )
    parser.add_argument(
        "--s3_bucket", required=True,
        help="S3 bucket to store crawled content"
    )
    parser.add_argument(
        "--depth", type=int, default=10,
        help="Maximum crawl depth (default: 10)"
    )
    parser.add_argument(
        "--include_patterns", nargs="+",
        help="Glob patterns for URLs to include"
    )
    parser.add_argument(
        "--exclude_patterns", nargs="+",
        help="Glob patterns for URLs to exclude"
    )
    args = parser.parse_args()

    # Validate that we don't have both include and exclude patterns
    if args.include_patterns and args.exclude_patterns:
        parser.error("Cannot specify both include and exclude patterns")

    # Run the spider
    run_spider(
        args.start_urls,
        args.s3_bucket,
        args.depth,
        args.include_patterns,
        args.exclude_patterns,
    )


if __name__ == "__main__":
    main()
