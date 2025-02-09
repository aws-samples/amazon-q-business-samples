#!/bin/bash

read -r -d '' SAML_METADATA_DOCUMENT <<METADATA_EOF
<REPLACE-WITH-SAML-METADATA-DOCUMENT-FROM-YOUR-IDP>
METADATA_EOF

export SAML_METADATA_DOCUMENT
export IDP_SSO_URL="<REPLACE-WITH-YOUR-IDP-SSO-URL>" 
export CUSTOM_ACS_URL="<REPLACE-WITH-YOUR-CUSTOM-APPLICATION-HOSTING-URL e.g. http://localhost:8000/saml>" 
export REGIONAL_SIGNIN_ENDPOINT_URL="<REPLACE-WITH-YOUR-REGIONAL-SIGNIN-ENDPOINT-URL e.g. https://signin.aws.amazon.com/saml or https://us-west-2.signin.aws.amazon.com/saml>"

export AWS_ACCOUNT_ID="<REPLACE-WITH-YOUR-AWS-ACCOUNT-ID>"
export AWS_DEFAULT_REGION="<REPLACE-WITH-YOUR-AWS-REGION>"
export AWS_SECRET_ENCRYPTION_KEY="<REPLACE-WITH-YOUR-SECRETS-MANAGER-SECRET-STORING-IDP-CLIENT-SECRET>"