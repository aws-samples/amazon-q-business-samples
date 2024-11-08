from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
import boto3
import base64
import html
import datetime
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

# SAML Configuration
idp_sso_url = non_empty_get_env("IDP_SSO_URL")
idp_issuer = non_empty_get_env("IDP_ISSUER")
custom_acs_url = non_empty_get_env("CUSTOM_ACS_URL")
web_experience_role_arn = non_empty_get_env("WEB_EXPERIENCE_ROLE_ARN")
iam_identity_provider_arn = non_empty_get_env("IAM_IDENTITY_PROVIDER_ARN")

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <body>
            <h1>Get AWS IAM Federation credentials</h1>
            <a href="/login/saml">Login with SAML</a>
        </body>
    </html>
    """

###### SAML #######

@app.get("/login/saml")
async def login():
    saml_request = create_saml_request()
    encoded_saml_request = base64.b64encode(saml_request.encode()).decode()
    
    params = {
        'SAMLRequest': encoded_saml_request,
        'RelayState': '/some/path'  # Optional: Add a RelayState if needed
    }
    
    redirect_url = f"{idp_sso_url}?{urlencode(params)}"
    return RedirectResponse(url=redirect_url)

def create_saml_request(assertion_consumer_service_index="0"):
    # This is a simplified SAML request. In a real-world scenario, you should use a library to create a proper SAML request.
    return f"""
    <samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                        xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                        ID="{secrets.token_hex(16)}"
                        Version="2.0"
                        IssueInstant="{datetime.datetime.utcnow().isoformat()}"
                        Destination="{idp_sso_url}"
                        AssertionConsumerServiceIndex="{assertion_consumer_service_index}"
                        ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
        <saml:Issuer>{idp_issuer}</saml:Issuer>
    </samlp:AuthnRequest>
    """

@app.api_route("/saml", methods=["POST"])
async def saml_endpoint(request: Request):
    form_data = await request.form()
    saml_response = form_data.get("SAMLResponse")

    if not saml_response:
        return HTMLResponse("No SAML response received", status_code=400)

    # Decode the SAML response
    decoded_assertion = base64.b64decode(saml_response).decode('utf-8')
    
    # Escape the XML to safely display it in HTML
    escaped_assertion = html.escape(decoded_assertion)

    # Construct the initial HTML content
    html_content = f"""
    <html>
        <head>
            <style>
                pre {{ white-space: pre-wrap; word-wrap: break-word; }}
            </style>
        </head>
        <body>
            <h2>Received SAML Assertion:</h2>
            <pre>{escaped_assertion}</pre>
    """

    # Call AWS STS API
    sts_client = boto3.client('sts')
    try:
        response = sts_client.assume_role_with_saml(
            RoleArn=web_experience_role_arn,
            DurationSeconds=3600,
            PrincipalArn=iam_identity_provider_arn,
            SAMLAssertion=saml_response  # Use the base64-encoded SAML assertion
        )
        
        # Extract and format the response
        credentials = response['Credentials']
        formatted_response = f"""
            <h2>WebApplication - 2</h2>
            <h2>AWS AssumeRoleWithSAML Response:</h2>
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
        
        html_content += formatted_response
    
    except Exception as e:
        error_message = html.escape(str(e))
        html_content += f"<h2>Error calling AWS API:</h2><pre>{error_message}</pre>"

    # Close the HTML content
    html_content += "</body></html>"

    # Ensure the response is treated as HTML
    return HTMLResponse(content=html_content, status_code=200)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000, access_log=True)
