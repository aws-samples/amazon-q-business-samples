from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
import boto3
import base64
import html
import requests
import json
from urllib.parse import urlencode
from botocore.exceptions import ClientError
import secrets
import sys, os

###
# pip install fastapi uvicorn boto3 authlib requests python-multipart
###
app = FastAPI()

def non_empty_get_env(var_name):
    value = os.getenv(var_name)
    if not value:
        print(f"Environment variable {var_name} is not set.")
        sys.exit(1)
    return value

# OIDC Configuration
OIDC_CLIENT_ID = non_empty_get_env("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = non_empty_get_env("OIDC_CLIENT_SECRET")
OIDC_DISCOVERY_URL = non_empty_get_env("OIDC_DISCOVERY_URL")

OIDC_REDIRECT_URI = non_empty_get_env("OIDC_REDIRECT_URI")
LOGOUT_REDIRECT_URI = non_empty_get_env("LOGOUT_REDIRECT_URI")
OIDC_ROLE_ARN = non_empty_get_env("OIDC_ROLE_ARN")

# Fetch OIDC configuration
oidc_config = requests.get(OIDC_DISCOVERY_URL,timeout=10).json()
AUTHORIZATION_ENDPOINT = oidc_config['authorization_endpoint']
TOKEN_ENDPOINT = oidc_config['token_endpoint']

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <body>
            <h1>Get AWS IAM Federation credentials</h1>
            <a href="/login/oidc">Login with OIDC</a>
        </body>
    </html>
    """

##### OIDC ######

@app.get("/login/oidc")
async def login_oidc(request: Request):
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    params = {
        'client_id': OIDC_CLIENT_ID,
        'response_type': 'code',
        'scope': 'openid email profile',
        'redirect_uri': OIDC_REDIRECT_URI,
        'state': state,
        'nonce': nonce
    }
    auth_url = f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)

@app.get("/auth/oidc/callback")
async def auth_oidc_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    
    # Here you should verify the state parameter
    
    token_response = requests.post(TOKEN_ENDPOINT, data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': OIDC_REDIRECT_URI,
        'client_id': OIDC_CLIENT_ID,
        'client_secret': OIDC_CLIENT_SECRET
    }, headers={'Accept': 'application/json'}, timeout=10)
    
    if token_response.status_code != 200:
        return HTMLResponse(f"<h1>Token Error</h1><p>{token_response.text}</p>")
    
    tokens = token_response.json()
    id_token = tokens['id_token']
    access_token = tokens['access_token']
    
    # Decode and verify the ID token (in a production environment)
    id_token_parts = id_token.split('.')
    id_token_payload = json.loads(base64.urlsafe_b64decode(id_token_parts[1] + '==').decode('utf-8'))

        # Call AWS STS to assume role with web identity
    sts_client = boto3.client('sts')
    try:
        response = sts_client.assume_role_with_web_identity(
            RoleArn=OIDC_ROLE_ARN,
            RoleSessionName='OIDCSession',
            WebIdentityToken=id_token,
            DurationSeconds=3600  # 1 hour
        )
        
        # Extract and format the response
        credentials = response['Credentials']
        formatted_response = f"""
        <h2>AWS AssumeRoleWithWebIdentity Response:</h2>
        <pre>
        AccessKeyId: {html.escape(credentials['AccessKeyId'])}
        SecretAccessKey: {html.escape(credentials['SecretAccessKey'])}
        SessionToken: {html.escape(credentials['SessionToken'])}
        Expiration: {credentials['Expiration']}

        export AWS_ACCESS_KEY_ID={html.escape(credentials['AccessKeyId'])}
        export AWS_SECRET_ACCESS_KEY={html.escape(credentials['SecretAccessKey'])}
        export AWS_SESSION_TOKEN={html.escape(credentials['SessionToken'])}
        </pre>
        """
    except ClientError as e:
        formatted_response = f"<h2>Error calling AWS API:</h2><pre>{html.escape(str(e))}</pre>"

    return HTMLResponse(f"""
    <h1>OIDC Login Successful</h1>
    <p>Welcome, {html.escape(id_token_payload.get('name', 'User'))}!</p>
    <h2>ID Token Claims:</h2>
    <pre>{html.escape(json.dumps(id_token_payload, indent=4))}</pre>
    <h2>Access Token:</h2>
    <pre>{html.escape(access_token)}</pre>
    {formatted_response}
    <a href="{oidc_config['end_session_endpoint']}?id_token_hint={id_token}&post_logout_redirect_uri={LOGOUT_REDIRECT_URI}">Logout</a>
    """)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
