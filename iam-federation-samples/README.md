# Implementing secure API access to your Amazon Q Business applications with IAM Federation user access management

>[!IMPORTANT] 
>Please refer to the blog post [Implement secure API access to your Amazon Q Business applications with IAM federation user access management](https://aws.amazon.com/blogs/machine-learning/implement-secure-api-access-to-your-amazon-q-business-applications-with-iam-federation-user-access-management/) for a detailed description of using Amazon Q Business APIs with IAM federetion and a comprehensive tutorial of using the scripts in this repository.

[Amazon Q Business](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/what-is.html) provides a rich set of APIs to perform administrative tasks and to build an AI-assistant with customized user experience for your organization. The sample python scripts in this repository illustrate how to use [Amazon Q Business APIs](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/api-ref.html) when using [IAM Federation](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/making-sigv4-authenticated-api-calls-iam.html) for user access management. You will use these illustrative scripts to learn:

1. As an Amazon Q Business administrator, use APIs to automate creation of Amazon Q Business applications using IAM Federation for user access management.

2. As an application builder, build and deploy custom applications to get [AWS Sig V4 credentials](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) with identity information on behalf of a user authenticated with the IdP.

3. As an application developer, use the credentials thus obtained to enable the user to chat with your Amazon Q Business application and get responses only from that enterprise content which the user is authorized to access.

## Solution overview
Amazon Q Business IAM Federation requires federating the user identities provisioned in your enterprise IdP (such as Okta or Ping Identity) account using [Federation with IAM](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers.html#id_roles_providers_iam). This involves a setup described in the steps below.

1. Creating a SAML or OIDC application integration in your IdP account. This step is performed by the IAM or Security administrator in your organization. Please refer to the blog post [build private and secure enterprise generative AI applications with Amazon Q Business using IAM Federation](https://aws.amazon.com/blogs/machine-learning/build-private-and-secure-enterprise-generative-ai-applications-with-amazon-q-business-using-iam-federation/) to understand the steps involved in doing this.

2. Creating corresponding [SAML IAM identity provider](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_saml.html) or an [OIDC IAM identity provider](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html) in AWS IAM. The IAM identity provider is used by the Amazon Q Business application to validate and trust federated identities of users authenticated by the enterprise IdP, and associate a unique identity with each user. Thus, a user is uniquely identified across Amazon Q Business applications sharing the same SAML IAM identity provider or OIDC IAM identity provider. This step is performed by an AWS administrator, or by an Amazon Q Business administrator, provided they have the IAM permissions to do so. 

3. Creating an Amazon Q Business application using the SAML or OIDC IAM identity provider. This step is performed by an Amazon Q Business administrator. The sample scripts `create-iam-saml-qbiz-app.py` and `create-iam-oidc-qbiz-app.py` illustrate how the administrators can automate steps 2 and 3 using AWS APIs.

4. Users in your organization can use Amazon Q Business web experience, a built-in application, to authenticate with your IdP and chat with the AI assistant. However to address unique requirements of your organization, your developers can build a custom application or integrate a preexisting enterprise portal with the Amazon Q business application using the Amazon Q Business APIs, for the users to authenticate with your IdP, and chat with the  AI assistant. The sample scripts `samlapp.py`, `oidcapp.py` in conjunction with `simple_aq.py` illustrate how to acquire AWS Sig V4 credentials that include user identity of your authenticated users, and then use these credentials to invoke Amazon Q Business conversation APIs and implement chat functionality.

## Prerequisites
To implement the sample use case described here, you will need an AWS account. You can [sign up for an AWS account](https://portal.aws.amazon.com/billing/signup) if you don't already have one. You also need an Okta account. The samples cover workflows for both OIDC and SAML 2.0, so you can follow either one or both workflows based on your business needs. You need to create application integrations for OIDC or SAML mode, and then configure the respective IAM identity providers in your AWS account, which will be required to create and configure your Amazon Q Business applications. You will also require a [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) with [AWS SDK for python](https://aws.amazon.com/sdk-for-python/) installed.

## Using the sample scripts

Clone this repository in a directory.

As a best practice create a python virtual environment and then install the python prerequisites.
```bash
python -m venv qbiz-venv
. ./qbiz-venv/bin/activate
pip install -r requirements.txt
```

## oidc-qbiz-app-env.sh
Perform this step if you are using OIDC application integration. For SAML, you can skip all the steps for OIDC flow, and directly start with `saml-qbiz-app-env.sh`. Set environment variables to provide the parameters for `create-iam-oidc-qbiz-app.py`. Amazon Q Business administrators can put the parameters in this shell scripts and then run it as below to set the environment variables. Edit this file and set the environment variables based on your OIDC application integration setup and your AWS account.

```bash
export AWS_ACCOUNT_ID="<REPLACE-WITH-YOUR-AWS-ACCOUNT-ID>"
export AWS_DEFAULT_REGION="<REPLACE-WITH-YOUR-AWS-REGION>"
export AWS_SECRET_ID="<REPLACE-WITH-YOUR-SECRETS-MANAGER-SECRET-STORING-IDP-CLIENT-SECRET>"
export AWS_SECRET_ENCRYPTION_KEY="<REPLACE-WITH-YOUR-SECRET-ENCRYPTION-KEY>"
export IDP_CLIENT_ID="<REPLACE-WITH-YOUR-IDP-APP-INTEGRATION-CLIENT-ID>"
export IDP_ISSUER_URL="<REPLACE-WITH-YOUR-IDP-ISSUER-URL>"
```

You can run this in your CLI environment as:

```bash
. ./oidc-qbiz-app-env.sh
```

## create-iam-oidc-qbiz-app.py 
Amazon Q Business administrators can use this script to setup Amazon Q Business applications by federating user identities provisioned in your enterprise Identity Provider (IdP) such as Okta. Before the script can be run, an OpenID Connect (OIDC) Web Application type Application integration needs to be configured in your Okta account, and parameters from the application integration need to be configured in the script. The script is required to be run in a terminal with python SDK for AWS installed, with AWS credentials to create IAM roles and policies, IAM identity providers, create and use Amazon Q Business applications, based on Identity Providers (IdP) such as Okta. 

After the environment is setup by running `oidc-qbiz-app-env.sh`, you can run this script using
```bash
python ./create-iam-oidc-qbiz-app.py
```
Copy the output of this script. You will require it in subsequent steps. You will need to update your Okta OIDC application integration Sign-in redirect URI as the default endpoint obtained in this step while keeping /authorization-code/callback at the end of the URI. Add one more Sign-in redirect URI of http://localhost:8000/auth/oidc/callback that we will use in subsequent steps. Change the Sign-out URI to http://localhost:8000/login/oidc.

## oidcapp-env.sh
Custom application developers use this script to set environment variables with parameters needed by oidcapp.py. Custom developers can put the parameters in this shell script and run it as below to set the environment variables. Edit this file and set the environment variables as below. You will first need to edit and setup the environment variables as:
```bash
export OIDC_CLIENT_ID="<REPLACE-WITH-YOUR-IDP-OIDC-CLIENT-ID>"
export OIDC_CLIENT_SECRET="<REPLACE-WITH-YOUR-IDP-OIDC-CLIENT-SECRET>"
export OIDC_DISCOVERY_URL="<REPLACE-WITH-YOUR-IDP-OIDC-DISCOVERY-URL>"

export OIDC_REDIRECT_URI="http://localhost:8000/auth/oidc/callback"
export LOGOUT_REDIRECT_URI="http://localhost:8000/login/oidc"
export OIDC_ROLE_ARN="<REPLACE-WITH-YOUR-WEB-EXPERIENCE-ROLE>"
```

```bash
. ./oidcapp-env.sh
```

## oidcapp.py
This script is for custom application developers. Application developers configure and deploy this script. End user authorized to use the IdP application integration can access the deployment and sign on. The script is required to be run in a terminal with python SDK for AWS installed. It does not need AWS credentials. It provides a mechanism for the user to authenticate with the IdP, then uses the authenticated identity token received from the IdP, and makes the AssumeRoleWithWebIdentity API call to AWS Security Token Service (STS) to get AWS Sig V4 credentials having the user's identity information for the authenticated user.

You can run this script as
```bash
python oidcapp.py
```
Open http://localhost:8000/ in a new browser window and login as a user in your Okta account to get AWS Sig V4 credentials for the logged in user. After this step you can directly go to the last step, that of running `simple_aq.py`.

## saml-qbiz-app-env.sh
Set environment variables to provide the parameters for create-iam-saml-qbiz-app.py. Amazon Q Business administrators can put the parameters in this shell scripts and then run it as below to set the environment variables. You will need to setup the environment variables below based on your SAML application integration setup and your AWS account.
```bash
read -r -d '' SAML_METADATA_DOCUMENT <<METADATA_EOF
<REPLACE-WITH-SAML-METADATA-DOCUMENT-FROM-YOUR-IDP>
METADATA_EOF

export SAML_METADATA_DOCUMENT
export IDP_SSO_URL="<REPLACE-WITH-YOUR-IDP-SSO-URL>" 
export CUSTOM_ACS_URL="<REPLACE-WITH-YOUR-CUSTOM-APPLICATION-HOSTING-URL e.g. http://localhost:8000/saml>" 

export AWS_ACCOUNT_ID="<REPLACE-WITH-YOUR-AWS-ACCOUNT-ID>"
export AWS_DEFAULT_REGION="<REPLACE-WITH-YOUR-AWS-REGION>"
export AWS_SECRET_ENCRYPTION_KEY="<REPLACE-WITH-YOUR-SECRETS-MANAGER-SECRET-STORING-IDP-CLIENT-SECRET>"
```

```bash
. ./saml-qbiz-app-env.sh
```

## create-iam-saml-qbiz-app.py 
Amazon Q Business administrators can use this script to setup Amazon Q Business applications by federating user identities provisioned in your enterprise Identity Provider (IdP) such as Okta. Before the script can be run, an SAML Application integration needs to be configured in your Okta account, and parameters from the application integration need to be configured in the script. It is required to be run in a terminal with python SDK for AWS installed, with AWS credentials to create IAM roles and policies, IAM identity providers, create and use Amazon Q Business applications based on Identity Providers (IdP) such as Okta. After the environment is setup by running `saml-qbiz-app-env.sh`, you can run this script as:

```bash
python ./create-iam-saml-qbiz-app.py
```
Please note the output of this script. You will require it in subsequent steps. You will need to update your SAML application integration based on this output. You will also need to include `http://localhost:8000/saml` as Other Requestable SSO URL with index set to 0.

## samlapp-env.sh
Custom application developers use this script to set environment variables with parameters needed by samlapp.py. Custom developers can put the parameters in this shell script and run it as below to set the environment variables. You will need to setup the environment variables as below:

```bash
export IDP_SSO_URL="<REPLACE-WITH-YOUR-IDP-SSO-URL>" 
export IDP_ISSUER="<REPLACE-WITH-YOUR-IDP-ISSUER-URL>"
export CUSTOM_ACS_URL="http://localhost:8000/saml"  # Your AssertionConsumerService URL
export WEB_EXPERIENCE_ROLE_ARN="<REPLACE-WITH-YOUR-WEB-EXPERIENCE-ROLE-ARN>"
export IAM_IDENTITY_PROVIDER_ARN="<REPLACE-WITH-YOUR-IAM-IDENTITY-PROVIDER-ARN>"
```

```bash
. ./samlapp-env.sh
```

## samlapp.py
This script is for custom application developers. Application developers configure and deploy this script. End user authorized to use the IdP application integration can access the deployment and sign on. It is required to be run in a terminal with python SDK for AWS installed. It does not need AWS credentials. It provides a mechanism for the user to authenticate with the IdP, then uses the SAML assertions received from the IdP, and makes the AssumeRoleWithSAML API call to AWS Security Token Service (STS) to get AWS Sig V4 credentials having identity information for the authenticated user. You can run this script after setting the environment variables using `samlapp-env.sh` as below:

```bash
python ./samlapp.py
```
Open http://localhost:8000/ in a new browser window and login as a user in your Okta account to get AWS Sig V4 credentials for the logged in user. After this step you can directly go to the last step, that of running `simple_aq.py`.

## simple_aq.py 
An end user who has acquired AWS Sig V4 credentials having identity information using `oidcapp.py` or `samlapp.py` can use this script to make queries to Amazon Q Business application using ChatSync API. It is required to be run in a terminal with python SDK for AWS installed. The terminal environment should be set with credentials having identity information obtained either by using `oidcapp.py` or `samlapp.py`. After setting the AWS region, the Amazon Q Business application id, and a couple of queries based on the data you have ingested in your Amazon Q Business application, you can use this script as:

```bash
python simple_aq.py
```
Note that when you run `simple_aq.py` with a particular user’s credentials for the first time, you will see the error: `An error occurred (AccessDeniedException) when calling the ChatSync operation: Exception occurred for requestId: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX with message: User does not have a subscription for the given application.` This is expected, and the user is automatically subscribed to the Amazon Q Business application on this call. Run `simple_aq.py` again with the same credentials, and you will get the expected response.
