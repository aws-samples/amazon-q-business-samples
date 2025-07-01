import boto3
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
from urllib.parse import urljoin

# Configuration
SECRET_NAME = 'ukg-crawler-secrets'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_secret(secret_name: str) -> Dict[str, str]:
    """
    Retrieve a secret from AWS Secrets Manager.

    The secret should be stored in AWS Secrets Manager as a JSON string
    with the following structure:
    {
        "UKG_APPLICATION_ID": "your-application-id",
        "UKG_APPLICATION_SECRET": "your-application-secret",
        "UKG_CLIENT_ID": "your-client-id",
        "UKG_BASE_URL": "https://your-ukg-api-base-url",
        "S3_BUCKET_NAME": "your-s3-bucket-name",
        "Q_BUSINESS_APP_ID": "your-q-business-app-id",
        "Q_BUSINESS_INDEX_ID": "your-q-business-index-id"
    }

    Required AWS IAM permissions:
    - secretsmanager:GetSecretValue

    Args:
        secret_name: Name of the secret in Secrets Manager

    Returns:
        Dictionary containing the secret values with the following keys:
        - UKG_APPLICATION_ID: The UKG application ID for authentication
        - UKG_APPLICATION_SECRET: The UKG application secret
        - UKG_CLIENT_ID: The UKG client ID for OAuth
        - UKG_BASE_URL: The base URL for the UKG API
        - S3_BUCKET_NAME: The name of the S3 bucket for storing articles
        - Q_BUSINESS_APP_ID: The Amazon Q Business application ID
        - Q_BUSINESS_INDEX_ID: The Amazon Q Business index ID

    Raises:
        ValueError: If the secret value is not a valid JSON string
        Exception: If there's an error retrieving the secret
    """
    try:
        session = boto3.session.Session()
        client = session.client('secretsmanager')

        response = client.get_secret_value(SecretId=secret_name)
        if 'SecretString' in response:
            return json.loads(response['SecretString'])
        else:
            raise ValueError("Secret value is not a string")
    except Exception as e:
        logger.error(f"Error retrieving secret {secret_name}: {e}")
        raise


class UKGCrawler:
    def __init__(self, application_id: str, application_secret: str,
                 client_id: str, base_url: str, s3_bucket: str):
        """
        Initialize the UKG crawler with OAuth credentials.

        Args:
            application_id: UKG application ID
            application_secret: UKG application secret
            client_id: UKG client ID
            base_url: Base URL for UKG API
            s3_bucket: S3 bucket name for storing articles
        """
        self.application_id = application_id
        self.application_secret = application_secret
        self.client_id = client_id
        self.base_url = base_url
        self.s3_bucket = s3_bucket
        self.s3_client = boto3.client('s3')
        self.q_business_client = boto3.client('qbusiness')
        self.access_token = None
        self.token_expiry = None

    def _get_oauth_token(self) -> Optional[str]:
        """Get OAuth access token using client credentials flow."""
        try:
            # Token endpoint URL
            token_url = urljoin(self.base_url, '/api/v2/client/tokens')

            # Prepare the request data
            data = {
                'grant_type': 'client_credentials',
                'scope': 'client',
                'client_id': self.client_id
            }

            # Make the token request with Basic Auth
            response = requests.post(
                token_url,
                data=data,
                auth=(self.application_id, self.application_secret),
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json'
                }
            )
            response.raise_for_status()

            # Parse the response
            token_data = response.json()
            self.access_token = token_data['access_token']

            # Set token expiry (expires_in is in seconds)
            expires_in = token_data.get('expires_in', 3600)
            self.token_expiry = datetime.now() + timedelta(
                seconds=expires_in - 60
            )

            logger.info("Successfully obtained new OAuth token")
            return self.access_token

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting OAuth token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return None

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests with OAuth token."""
        # Check if token is expired or about to expire
        if (not self.access_token or
                (self.token_expiry and datetime.now() >= self.token_expiry)):
            if not self._get_oauth_token():
                raise Exception("Failed to obtain valid OAuth token")

        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def _get_articles(self) -> list:
        """Fetch all articles from UKG API using cursor-based pagination."""
        all_articles = []
        cursor = None

        while True:
            try:
                # Prepare URL with cursor parameter if available
                url = urljoin(self.base_url, '/api/v2/client/kb_articles')
                if cursor:
                    url = f"{url}?cursor={cursor}"

                logger.info(f"Fetching articles from URL: {url}")
                response = requests.get(
                    url,
                    headers=self._get_headers()
                )
                response.raise_for_status()

                # Add articles from current page
                articles = response.json()
                all_articles.extend(articles)
                logger.info(
                    f"Fetched {len(articles)} articles on this page"
                )

                # Get next cursor from header
                next_cursor = response.headers.get('Next-Cursor')
                if next_cursor:
                    logger.info(f"Found next cursor: {next_cursor}")
                    cursor = next_cursor
                else:
                    logger.info("No more pages to fetch")
                    break

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching articles: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response status: {e.response.status_code}")
                    logger.error(f"Response body: {e.response.text}")
                break

        logger.info(f"Fetched {len(all_articles)} total articles")
        return all_articles

    def _get_article_content(self, article_id: str) -> \
            Optional[Dict[str, Any]]:
        """
        Fetch content body for a specific article and return latest version.
        """
        try:
            url = urljoin(
                self.base_url, f'/api/v2/client/kb_articles/{article_id}'
            )
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            article_data = response.json()

            # Get the versions list
            versions = article_data.get('versions', [])
            if not versions:
                logger.warning(f"No versions found for article {article_id}")
                return None

            # Find the latest version based on updated_at
            def parse_datetime(dt_str):
                try:
                    return datetime.fromisoformat(
                        dt_str.replace('Z', '+00:00')
                    )
                except Exception:
                    return datetime.fromisoformat(
                        '1970-01-01T00:00:00+00:00'
                    )

            latest_version = max(
                versions,
                key=lambda v: parse_datetime(
                    v.get('updated_at', '1970-01-01T00:00:00+00:00')
                )
            )
            return latest_version

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error fetching article content for ID {article_id}: {e}"
            )
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return None

    def _create_metadata(self, article: Dict[str, Any],
                         article_content: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata for Amazon Q Business ingestion."""
        article_id = article.get("id", "")
        source_uri = urljoin(self.base_url, f"/articles/{article_id}")

        # Get timestamps from the latest version
        created_at = article_content.get('created_at', '')
        updated_at = article_content.get('updated_at', '')

        return {
            "Attributes": {
                "_category": "article",
                "_created_at": created_at,
                "_last_updated_at": updated_at,
                "_source_uri": source_uri,
                "_version": article_content.get('version_number', '1'),
                "_view_count": article.get('view_count', 0),
                "author_id": article.get('author_id', '')
            },
            "Title": article_content.get('title', '')
        }

    def _upload_to_s3(self, content: str, key: str) -> bool:
        """Upload content to S3."""
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=json.dumps(content)
            )
            return True
        except Exception as e:
            logger.error(f"Error uploading to S3: {e}")
            return False

    def process_articles(self):
        """Process all articles and upload them to S3 with metadata."""
        # Get initial token
        if not self._get_oauth_token():
            logger.error("Failed to get OAuth token, cannot proceed")
            return

        articles = self._get_articles()
        successful_count = 0

        for article in articles:
            # Create a unique identifier for the article
            article_id = article.get("id", "")
            if not article_id:
                logger.warning("Article missing ID, skipping")
                continue

            # Fetch detailed article content
            article_content = self._get_article_content(article_id)
            if not article_content:
                logger.warning(
                    f"Failed to fetch content for article {article_id}, "
                    "skipping"
                )
                continue

            # Upload article content
            content_key = f"articles/{article_id}.txt"
            if not self._upload_to_s3(
                article_content.get('body', ''),
                content_key
            ):
                continue

            # Create and upload metadata
            metadata = self._create_metadata(article, article_content)
            metadata_key = f"articles/{article_id}.txt.metadata.json"
            if not self._upload_to_s3(metadata, metadata_key):
                continue

            successful_count += 1
            logger.info(
                f"Successfully processed article: {article_id} "
                f"({successful_count}/{len(articles)})"
            )

        logger.info(
            f"Processing complete. Successfully processed "
            f"{successful_count} out of {len(articles)} articles."
        )

    def _list_s3_articles(self) -> List[Dict[str, str]]:
        """
        List all article content and metadata files from S3.

        Returns:
            List of dictionaries containing content and metadata file keys
        """
        articles = []
        paginator = self.s3_client.get_paginator('list_objects_v2')

        for page in paginator.paginate(
            Bucket=self.s3_bucket, Prefix='articles/'
        ):
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']
                if key.endswith('.txt'):
                    # Found content file, look for corresponding metadata
                    metadata_key = f"{key}.metadata.json"
                    try:
                        self.s3_client.head_object(
                            Bucket=self.s3_bucket, Key=metadata_key
                        )
                        articles.append({
                            'content_key': key,
                            'metadata_key': metadata_key
                        })
                    except self.s3_client.exceptions.ClientError:
                        logger.warning(
                            f"No metadata found for {key}, skipping"
                        )
                        continue

        return articles

    def _get_s3_object_content(self, key: str) -> Optional[str]:
        """
        Get the content of an S3 object.

        Args:
            key: S3 object key

        Returns:
            Object content as string, or None if error
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket, Key=key
            )
            return response['Body'].read().decode('utf-8')
        except Exception as e:
            logger.error(f"Error reading S3 object {key}: {e}")
            return None

    def sync_with_q_business(self, application_id: str, index_id: str):
        """
        Sync S3 content with Amazon Q Business index.

        Args:
            application_id: Amazon Q Business application ID
            index_id: Amazon Q Business index ID
        """
        articles = self._list_s3_articles()
        logger.info(
            f"Found {len(articles)} articles to sync with Q Business"
        )

        for article in articles:
            try:
                # Get content and metadata
                content = self._get_s3_object_content(
                    article['content_key']
                )
                metadata_json = self._get_s3_object_content(
                    article['metadata_key']
                )

                if not content or not metadata_json:
                    logger.warning(
                        f"Missing content or metadata for "
                        f"{article['content_key']}, skipping"
                    )
                    continue

                metadata = json.loads(metadata_json)

                # Prepare document for Q Business
                document = {
                    'documentId': article['content_key'].replace(
                        'articles/', ''
                    ).replace('.txt', ''),
                    'content': content,
                    'title': metadata.get('Title', ''),
                    'attributes': metadata.get('Attributes', {}),
                    'contentType': 'PLAINTEXT'
                }

                # Upload to Q Business
                self.q_business_client.batch_put_document(
                    applicationId=application_id,
                    indexId=index_id,
                    documents=[document]
                )

                logger.info(
                    f"Successfully synced article "
                    f"{document['documentId']} to Q Business"
                )

            except Exception as e:
                logger.error(
                    f"Error syncing article {article['content_key']} "
                    f"to Q Business: {e}"
                )
                continue

        logger.info("Completed syncing articles with Q Business")


def main():
    # Get secrets from Secrets Manager
    try:
        secrets = get_secret(SECRET_NAME)

        APPLICATION_ID = secrets['UKG_APPLICATION_ID']
        APPLICATION_SECRET = secrets['UKG_APPLICATION_SECRET']
        CLIENT_ID = secrets['UKG_CLIENT_ID']
        BASE_URL = secrets['UKG_BASE_URL']
        S3_BUCKET = secrets['S3_BUCKET_NAME']
        Q_BUSINESS_APP_ID = secrets['Q_BUSINESS_APP_ID']
        Q_BUSINESS_INDEX_ID = secrets['Q_BUSINESS_INDEX_ID']

        if not all([APPLICATION_ID, APPLICATION_SECRET, CLIENT_ID,
                   BASE_URL, S3_BUCKET, Q_BUSINESS_APP_ID,
                   Q_BUSINESS_INDEX_ID]):
            logger.error("Missing required secret values")
            return

        crawler = UKGCrawler(
            application_id=APPLICATION_ID,
            application_secret=APPLICATION_SECRET,
            client_id=CLIENT_ID,
            base_url=BASE_URL,
            s3_bucket=S3_BUCKET
        )

        # Process articles and sync with Q Business
        crawler.process_articles()
        crawler.sync_with_q_business(Q_BUSINESS_APP_ID, Q_BUSINESS_INDEX_ID)

    except Exception as e:
        logger.error(
            f"Failed to initialize crawler while trying to seed secrets: {e}"
        )
        return


if __name__ == "__main__":
    main()
