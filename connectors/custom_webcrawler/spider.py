"""
Spider implementation for Custom WebCrawler Plus.
"""

import fnmatch
import hashlib
import json
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import boto3
import botocore
import scrapy
from scrapy.exceptions import IgnoreRequest
from scrapy.spiders import CrawlSpider


class CustomWebCrawlerPlus(CrawlSpider):
    """Advanced web crawler with JavaScript rendering and S3 storage.

    This spider extends Scrapy's CrawlSpider to provide enhanced web crawling
    with JavaScript rendering via Splash, Cloudflare protection bypass,
    cookie management, and S3 storage integration.
    """
    name = "custom_webcrawler_plus"

    def __init__(self, *args, **kwargs):
        # Extract our custom parameters
        start_urls = kwargs.pop('start_urls', [])
        s3_bucket = kwargs.pop('s3_bucket', None)
        max_depth = kwargs.pop('max_depth', 10)
        include_patterns = kwargs.pop('include_patterns', [])
        exclude_patterns = kwargs.pop('exclude_patterns', [])

        super().__init__(*args, **kwargs)

        # Group all configuration and state into dictionaries to reduce
        # instance attributes
        self.config = {
            "start_urls": start_urls,
            "s3_bucket": s3_bucket,
            "max_depth": max_depth,
            "include_patterns": include_patterns,
            "exclude_patterns": exclude_patterns,
        }

        # Group crawler state attributes
        self.crawler_state = {
            "start_time": datetime.now(),
            "requests_made": 0,
            "responses_received": 0,
            "items_processed": 0,
            "errors": 0,
            "robots_ignored": 0,
            "total_processing_time": 0,
            "urls_filtered": 0,  # Total URLs filtered by patterns
            "filtered_by_include": 0,  # URLs that didn't match include
            # patterns
            "filtered_by_exclude": 0,  # URLs that matched exclude patterns
            "filtered_urls": set(),  # Set of URLs that were filtered
        }

        # Group domain-related attributes
        self.domain_config = {
            "allowed_domains": set(),
            "allowed_tlds": set(),
            "cookies": {},
            "last_request_time": {},
        }

        # Initialize S3 client
        self.s3_client = boto3.client("s3")

        # Set up allowed domains and TLDs
        for url in self.config["start_urls"]:
            domain = urlparse(url).netloc
            self.domain_config["allowed_domains"].add(domain)
            tld = ".".join(domain.split(".")[-2:])
            self.domain_config["allowed_tlds"].add(tld)

        print(f"\n{'='*80}")
        print("Crawler Configuration:")
        print(f"Allowed domains: "
              f"{list(self.domain_config['allowed_domains'])}")
        print(f"Allowed TLDs: {list(self.domain_config['allowed_tlds'])}")
        print(f"S3 bucket: {self.config['s3_bucket']}")
        print(f"Maximum crawl depth: {self.config['max_depth']}")
        if self.config['include_patterns']:
            print(f"Include patterns: {self.config['include_patterns']}")
        if self.config['exclude_patterns']:
            print(f"Exclude patterns: {self.config['exclude_patterns']}")
        print(f"{'='*80}\n")

    def parse(self, response, **kwargs):
        """Default parse method required by Spider base class."""
        # This method is required by the Spider base class but not used
        # since we override start_requests and use parse_item

    def matches_url_patterns(self, url):
        """Check if URL matches the include/exclude patterns."""
        if self.config['exclude_patterns']:
            # If exclude patterns are set, check if URL matches any exclude
            # pattern
            for pattern in self.config['exclude_patterns']:
                if fnmatch.fnmatch(url, pattern):
                    self.crawler_state["filtered_by_exclude"] += 1
                    self.crawler_state["filtered_urls"].add(url)
                    return False
            return True

        if self.config['include_patterns']:
            # If include patterns are set, check if URL matches any include
            # pattern
            for pattern in self.config['include_patterns']:
                if fnmatch.fnmatch(url, pattern):
                    return True
            self.crawler_state["filtered_by_include"] += 1
            self.crawler_state["filtered_urls"].add(url)
            return False
        return True  # If no patterns are set, allow all URLs

    def update_cookies(self, domain, new_cookies):
        """Update cookies for a domain."""
        if domain not in self.domain_config["cookies"]:
            self.domain_config["cookies"][domain] = {}

        # Update cookies
        for cookie in new_cookies:
            self.domain_config["cookies"][domain][cookie["name"]] = (
                cookie["value"])

        print(f"\nUpdated cookies for {domain}: ")
        for name, value in self.domain_config["cookies"][domain].items():
            print(f"  {name}: {value}")

    def get_cookies_for_domain(self, domain):
        """Get cookies for a domain."""
        return self.domain_config["cookies"].get(domain, {})

    def get_content_type(self, response):
        """Detect the content type from the response."""
        # Content type mappings
        content_type_mappings = {
            'application/pdf': ('PDF', '.pdf'),
            'application/json': ('JSON', '.json'),
            'text/plain': ('PLAIN_TEXT', '.txt'),
            'application/xml': ('XML', '.xml'),
            'text/xml': ('XML', '.xml'),
            'application/vnd.ms-excel': ('CSV', '.csv'),
            'text/csv': ('CSV', '.csv'),
            'application/msword': ('MS_WORD', '.docx'),
            ('application/vnd.openxmlformats-officedocument.'
             'wordprocessingml.document'): ('MS_WORD', '.docx'),
            'application/vnd.ms-powerpoint': ('PPT', '.pptx'),
            ('application/vnd.openxmlformats-officedocument.'
             'presentationml.presentation'): ('PPT', '.pptx'),
            ('application/vnd.openxmlformats-officedocument.'
             'spreadsheetml.sheet'): ('MS_EXCEL', '.xlsx'),
            'text/markdown': ('MD', '.md'),
            'text/html': ('HTML', '.html'),
            'application/xhtml+xml': ('HTML', '.html'),
            'image/jpeg': ('IMAGE', '.jpg'),
            'image/png': ('IMAGE', '.png'),
            'image/gif': ('IMAGE', '.gif'),
            'image/webp': ('IMAGE', '.webp'),
            'image/svg+xml': ('IMAGE', '.svg'),
            'image/bmp': ('IMAGE', '.bmp'),
            'image/tiff': ('IMAGE', '.tiff'),
            'audio/mpeg': ('AUDIO', '.mp3'),
            'audio/wav': ('AUDIO', '.wav'),
            'audio/ogg': ('AUDIO', '.ogg'),
            'audio/midi': ('AUDIO', '.midi'),
            'audio/webm': ('AUDIO', '.webm'),
            'video/mp4': ('VIDEO', '.mp4'),
            'video/webm': ('VIDEO', '.webm'),
            'video/ogg': ('VIDEO', '.ogv'),
            'video/quicktime': ('VIDEO', '.mov'),
            'video/x-msvideo': ('VIDEO', '.avi'),
            'video/x-matroska': ('VIDEO', '.mkv'),
        }

        # URL extension mappings
        url_extension_mappings = {
            '.jpg': ('IMAGE', '.jpg'),
            '.jpeg': ('IMAGE', '.jpg'),
            '.png': ('IMAGE', '.png'),
            '.gif': ('IMAGE', '.gif'),
            '.webp': ('IMAGE', '.webp'),
            '.svg': ('IMAGE', '.svg'),
            '.bmp': ('IMAGE', '.bmp'),
            '.tiff': ('IMAGE', '.tiff'),
            '.mp3': ('AUDIO', '.mp3'),
            '.wav': ('AUDIO', '.wav'),
            '.ogg': ('AUDIO', '.ogg'),
            '.midi': ('AUDIO', '.midi'),
            '.mp4': ('VIDEO', '.mp4'),
            '.webm': ('VIDEO', '.webm'),
            '.ogv': ('VIDEO', '.ogv'),
            '.mov': ('VIDEO', '.mov'),
            '.avi': ('VIDEO', '.avi'),
            '.mkv': ('VIDEO', '.mkv'),
        }

        # First check Content-Type header
        content_type = (
            response.headers.get("Content-Type", b"")
            .decode("utf-8", errors="ignore")
            .lower()
        )

        # Check content type mappings
        for content_type_key, result in content_type_mappings.items():
            if content_type_key in content_type:
                return result

        # Try to determine type from URL if header doesn't help
        url = response.url.lower()
        for extension, result in url_extension_mappings.items():
            if url.endswith(extension):
                return result

        # Default to HTML if we can't determine the type
        return "HTML", ".html"

    def get_storage_path(self, response_url, file_extension=".html"):
        """Generate a storage path based on the URL."""
        # Generate MD5 hash of the URL
        url_hash = hashlib.md5(response_url.encode()).hexdigest()

        # Find the matching domain from allowed domains
        for domain in self.domain_config["allowed_domains"]:
            if domain in response_url:
                # Create a clean domain name for the path
                clean_domain = domain.replace(".", "_")
                return f"{clean_domain}/{url_hash}{file_extension}"

        # Fallback if no domain matches
        return f"unknown_domain/{url_hash}{file_extension}"

    def start_requests(self):
        """Generate initial requests to start the crawling process."""
        for url in self.config["start_urls"]:
            yield scrapy.Request(
                url=url,
                callback=self.parse_item,
                errback=self.handle_error,
                meta={"depth": 0},
                dont_filter=True,
            )

    def process_request(self, request):
        """Process each request before it's sent."""
        self.crawler_state["requests_made"] += 1

        # Add Splash middleware for JavaScript rendering
        request.meta["splash"] = {
            "args": {
                "wait": 2,  # Wait for 2 seconds for JavaScript to load
                "timeout": 30,  # 30 second timeout
                "resource_timeout": 10,  # 10 second resource timeout
                "images": 0,  # Don't load images to speed up crawling
                "headers": {
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": (
                        "text/html,application/xhtml+xml,application/xml;"
                        "q=0.9,image/webp,image/apng,*/*;q=0.8"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                },
            },
            "endpoint": "render.html",
        }

        # Add cookies if we have them for this domain
        domain = urlparse(request.url).netloc
        cookies = self.get_cookies_for_domain(domain)
        if cookies:
            request.meta["splash"]["args"]["cookies"] = cookies

        # Rate limiting - respect robots.txt and add delays
        if domain in self.domain_config["last_request_time"]:
            time_since_last = (
                datetime.now() -
                self.domain_config["last_request_time"][domain]
            ).total_seconds()
            if time_since_last < 1:  # Minimum 1 second between requests
                time.sleep(1 - time_since_last)

        self.domain_config["last_request_time"][domain] = datetime.now()

        # Check depth limit
        depth = request.meta.get("depth", 0)
        if depth >= self.config['max_depth']:  # Changed from > to >=
            print(f"Skipping {request.url} - reached maximum depth "
                  f"{self.config['max_depth']}")
            return None

        return request

    def create_metadata_file(self, url, title, content_type="HTML"):
        """Create a metadata file for Amazon Q Business."""
        # Create metadata structure
        metadata = {
            "Attributes": {
                "_category": "webpage",
                "_created_at": datetime.now(timezone.utc).isoformat(),
                "_last_updated_at": datetime.now(
                    timezone.utc).isoformat(),
                "_source_uri": url,
                "_version": "1.0",
                "_view_count": 0,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "domain": urlparse(url).netloc,
            },
            "Title": title or url,
            "ContentType": content_type,
        }

        # Convert to JSON string
        metadata_json = json.dumps(
            metadata, indent=2, ensure_ascii=False)

        return metadata_json

    def _process_content(self, response, content_type):
        """Process and extract content from response."""
        if (hasattr(response, "data") and isinstance(response.data, dict)):
            # This is a Splash JSON response
            content = response.data.get("html", "")
            title = response.data.get("title", "")
        else:
            # This is a regular response
            content = response.body
            title = (
                response.css("title::text").get()
                if content_type == "HTML"
                else response.url
            )
        return content, title

    def _upload_to_s3(self, storage_path, content, metadata, response):
        """Upload content and metadata to S3."""
        # Upload content to S3 with metadata
        self.s3_client.put_object(
            Bucket=self.config['s3_bucket'],
            Key=storage_path,
            Body=content,
            ContentType=(response.headers.get("Content-Type", b"")
                         .decode("utf-8", errors="ignore")),
            Metadata={
                "category": metadata["Attributes"]["_category"],
                "created_at": metadata["Attributes"]["_created_at"],
                "last_updated_at": metadata["Attributes"]["_last_updated_at"],
                "source_uri": metadata["Attributes"]["_source_uri"],
                "version": metadata["Attributes"]["_version"],
                "view_count": str(metadata["Attributes"]["_view_count"]),
                "crawled_at": metadata["Attributes"]["crawled_at"],
                "domain": metadata["Attributes"]["domain"],
                "title": metadata["Title"],
                "content_type": metadata["ContentType"],
            },
        )

        # Create and upload metadata file
        metadata_path = f"{storage_path}.metadata.json"
        metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)
        self.s3_client.put_object(
            Bucket=self.config['s3_bucket'],
            Key=metadata_path,
            Body=metadata_json,
            ContentType="application/json",
        )
        return metadata_path

    def _print_progress(self, response, content_type, storage_path,
                        metadata_path):
        """Print progress information."""
        print(f"\n{'='*40} Successfully Processed {'='*40}")
        print(f"URL: {response.url}")
        print(f"Content type: {content_type}")
        print(f"Stored at: {storage_path}")
        print(f"Metadata at: {metadata_path}")

        # Print progress report inline
        current_time = datetime.now()
        elapsed_time = (
            current_time - self.crawler_state["start_time"]
        ).total_seconds()
        avg_time_per_page = int(
            elapsed_time / self.crawler_state["items_processed"]
            if self.crawler_state["items_processed"] > 0
            else 0
        )
        print(
            f"\nProgress: {int(elapsed_time)}s elapsed | "
            f"{self.crawler_state['requests_made']} requests | "
            f"{self.crawler_state['responses_received']} responses"
        )
        print(
            f"Stats: {self.crawler_state['items_processed']} processed | "
            f"{self.crawler_state['robots_ignored']} robots.txt ignores | "
            f"{self.crawler_state['errors']} errors"
        )
        if self.config['include_patterns']:
            print(
                f"Filtered: {self.crawler_state['filtered_by_include']} URLs "
                "didn't match include patterns"
            )
        if self.config['exclude_patterns']:
            print(
                f"Filtered: {self.crawler_state['filtered_by_exclude']} URLs "
                "matched exclude patterns"
            )
        print(f"Average: {avg_time_per_page}s per page")

    def _extract_and_follow_links(self, response, content_type, current_depth):
        """Extract and follow links from HTML content."""
        if not (content_type == "HTML" and hasattr(response, "selector")):
            return

        if current_depth >= self.config['max_depth']:
            return

        for href in response.css("a::attr(href)").getall():
            try:
                # Convert relative URLs to absolute
                absolute_url = response.urljoin(href)
                # Only follow links within allowed domains and matching
                # patterns
                if any(domain in absolute_url for domain in
                       self.domain_config["allowed_domains"]):
                    if self.matches_url_patterns(absolute_url):
                        yield scrapy.Request(
                            url=absolute_url,
                            callback=self.parse_item,
                            errback=self.handle_error,
                            meta={"depth": current_depth + 1},
                        )
                    else:
                        self.crawler_state["urls_filtered"] += 1
                        print(
                            f"Skipping {absolute_url} - doesn't match URL "
                            "patterns"
                        )
            except (ValueError, TypeError) as e:
                print(f"Warning: Error processing link {href}: {str(e)}")

    def parse_item(self, response):
        """Parse the response and extract content."""
        start_time = datetime.now()

        # Check for non-200 status codes
        if response.status != 200:
            print(f"\n{'='*40} Non-200 Response {'='*40}")
            print(f"URL: {response.url}")
            print(f"Status: {response.status}")
            print(f"Headers: {response.headers}")
            print(f"Body (first 500 chars): {response.text[:500]}")
            return

        self.crawler_state["responses_received"] += 1

        try:
            # Update cookies if we got new ones from Splash
            if (hasattr(response, "data") and isinstance(response.data, dict)):
                domain = urlparse(response.url).netloc
                if "cookies" in response.data:
                    self.update_cookies(domain, response.data["cookies"])

            # Detect content type
            content_type, file_extension = self.get_content_type(response)

            # Process content
            content, title = self._process_content(response, content_type)

            # Get storage path and create metadata
            storage_path = self.get_storage_path(response.url, file_extension)
            metadata = self.create_metadata_file(response.url, title,
                                                 content_type)
            metadata_dict = json.loads(metadata)

            # Upload to S3
            metadata_path = self._upload_to_s3(storage_path, content,
                                               metadata_dict, response)

            # Update stats
            self.crawler_state["items_processed"] += 1
            processing_time = (datetime.now() - start_time).total_seconds()
            self.crawler_state["total_processing_time"] += processing_time

            # Print progress
            self._print_progress(response, content_type, storage_path,
                                 metadata_path)

            # Extract and follow links
            current_depth = response.meta.get("depth", 0)
            yield from self._extract_and_follow_links(
                response, content_type, current_depth)

        except (OSError, IOError, botocore.exceptions.BotoCoreError,
                botocore.exceptions.ClientError) as e:
            self.crawler_state["errors"] += 1
            print(f"\n{'='*40} Processing Error {'='*40}")
            print(f"URL: {response.url}")
            print(f"Error: {str(e)}")

    def handle_error(self, failure):
        """Handle request failures."""
        self.crawler_state["errors"] += 1
        request = failure.request

        # Check if it's a robots.txt block
        if (isinstance(failure.value, IgnoreRequest) and
                "robots.txt" in str(failure.value)):
            self.crawler_state["robots_ignored"] += 1
            self.crawler_state["errors"] -= 1  # Decrement error count since
            # we're counting it separately
            print(f"\n{'='*40} Robots.txt Ignored {'='*40}")
            print(f"URL: {request.url}")
            return

        print(f"\n{'='*40} Error Processing {'='*40}")
        print(f"URL: {request.url}")
        print(f"Error type: {type(failure.value).__name__}")
        print(f"Error message: {str(failure.value)}")

        # If we have a response, print its details
        if hasattr(failure.value, "response"):
            response = failure.value.response
            print(f"Response status: {response.status}")
            print(f"Response headers: {response.headers}")
            print(f"Response body (first 500 chars): "
                  f"{response.text[:500]}")

    def closed(self, reason):
        """Log final statistics when the spider closes."""
        end_time = datetime.now()
        duration = end_time - self.crawler_state["start_time"]

        print("\n=== Crawler Final Statistics ===")
        print(f"Total duration: {duration}")
        print(f"Total requests made: {self.crawler_state['requests_made']}")
        print(f"Total responses received: "
              f"{self.crawler_state['responses_received']}")
        print(f"Total items processed: "
              f"{self.crawler_state['items_processed']}")
        print(f"Total errors: {self.crawler_state['errors']}")
        if self.config['include_patterns']:
            print("\nURL Pattern Filtering (Include):")
            print(f"Total URLs filtered: "
                  f"{self.crawler_state['filtered_by_include']}")
            print("Filtered URLs:")
            for url in sorted(self.crawler_state["filtered_urls"]):
                print(f" - {url}")
        if self.config['exclude_patterns']:
            print("\nURL Pattern Filtering (Exclude):")
            print(f"Total URLs filtered: "
                  f"{self.crawler_state['filtered_by_exclude']}")
            print("Filtered URLs:")
            for url in sorted(self.crawler_state["filtered_urls"]):
                print(f" - {url}")
        print(f"\nClose reason: {reason}")
        print("==============================\n")
