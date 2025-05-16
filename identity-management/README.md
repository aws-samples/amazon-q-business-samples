# Amazon Q Business security and identity management

Index of Amazon Q Business security and identity management related code samples, tutorials, and how-to guides.


## Contents

- [Choosing access federation](#choosing-access-federation)
- [Trusted identity propagation](#trusted-identity-propagation)
- [Glossary of assets](#glossary-of-assets)
    - [Workshops](#workshops)
    - [Tutorials](#tutorials)
    - [How-tos](#how-tos)
    - [Blogs](#blogs)
    - [Code samples](#code-samples)
        - [Python samples](#python-samples)
        - [Javascript samples](#javascript-samples)
        - [Cloud Formation templates](#cloud-formation-templates)
- [Frequently asked questions](#frequently-asked-questions)

#### Legends

- `external` means content stored outside this repository
- `local` means content stored in this repository

## Choosing access federation

When selecting between IAM Identity Center (Identity Center) and IAM Federation, organizations should evaluate their requirements based on four core qualification criteria:

1. User subscription consolidation - Enables single billing for same user across multiple AWS accounts
1. Cross-service integration - Amazon QuickSight, Amazon Q Business, Amazon Q Developer, Amazon S3
1. Third-party Identity Provider integration (IDP) using SAML or OIDC
1. Federated group synchronization for ACL enforcement - Centrally manage user groups from across data sources

See [Frequently asked questions](#frequently-asked-questions) section for additional guidance.

![Choosing access federation](/static/img/access-choice.png)


## Trusted identity propagation

This diagram shows how authenticated user identities propagate from enterprise Identity Providers (IdPs) to Amazon Q Business identity-aware APIs. Organizations can use either IAM Identity Center or IAM Federation service to manage trusted identity propagation (TIP) securely.

![Identity-aware APIs](/static/img/id-aware-api.png)

## Glossary of assets

### Workshops

1. `external` [IAM Identity Center: Empowering Secure Access to Generative AI Applications](https://catalog.us-east-1.prod.workshops.aws/workshops/d6323be2-38f4-457e-aaf5-08af211f3681/en-US)
1. `external` [Integrate your application with Amazon Q Business identity-aware APIs](https://catalog.workshops.aws/amazon-q-business-api)

### Tutorials

1. `external` [Configuring custom web application with Amazon Cognito and IAM Identity Center](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/cognito/config-webapp-using-cognito.md)
1. `external` [Configuring custom web application with Microsoft Entra and IAM Identity Center](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/entra/config-webapp-using-entra.md)
1. `external` [Configuring custom web application with Okta and IAM Identity Center](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/okta/config-webapp-using-okta.md)


### How-tos

1. `external`[Register web application with Amazon Cognito](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/cognito/register-webapp-with-cognito.md)
1. `external`[Register web application with Microsoft Entra](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/entra/register-webapp-with-entra.md)
1. `external`[How to find Microsoft Entra Issuer URI](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/entra/find-entra-issuer-url.md)
1. `external`[Register web application with Okta](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/okta/register-webapp-with-okta.md)
1. `external`[How to find Okta Issuer URI](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/okta/find-okta-issuer-url.md)


### Blogs

1. `external` [Enable or disable ACL crawling safely in Amazon Q Business](https://aws.amazon.com/blogs/machine-learning/enable-or-disable-acl-crawling-safely-in-amazon-q-business/)
1. `external` [Query structured data from Amazon Q Business using Amazon QuickSight integration](https://aws.amazon.com/blogs/machine-learning/query-structured-data-from-amazon-q-business-using-amazon-quicksight-integration/)
1. `external` [Build private and secure enterprise generative AI applications with Amazon Q Business using IAM Federation](https://aws.amazon.com/blogs/machine-learning/build-private-and-secure-enterprise-generative-ai-applications-with-amazon-q-business-using-iam-federation/)
1. `external` [Configure Amazon Q Business with AWS IAM Identity Center trusted identity propagation](https://aws.amazon.com/blogs/machine-learning/configuring-amazon-q-business-with-aws-iam-identity-center-trusted-identity-propagation/)


### Code samples

* #### Python samples
    
    1. `local` [Secure API access with IAM Federation](iam-federation-samples) | `external` [README](./iam-federation-samples/README.md)
    1. `external` [Token Vending Machine and UX](https://github.com/aws-samples/custom-ui-tvm-amazon-q-business/tree/main/amzn-q-auth-tvm) | `external` [README](https://github.com/aws-samples/custom-ui-tvm-amazon-q-business/blob/main/README.md)
    1. `external` [IAM Identity Center trusted identity propagation](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/tree/main/webapp) | `external` [README](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/webapp/README.md)

* #### Javascript samples
    
    1. `external` [ReactJS UX](https://github.com/aws-samples/integrate-your-application-with-amazon-q-business-identity-aware-apis/tree/main/app) | `external` [README](https://github.com/aws-samples/integrate-your-application-with-amazon-q-business-identity-aware-apis/blob/main/README.md)

* #### Cloud Formation templates
    
    1. `external` [Configure IAM Identity Center](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/cf/qb-api-idc-config.yaml) | `external` [README](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/cf/README.md)
    1. `external` [Create Amazon Cognito user pool](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/cf/qb-api-poc-cognito.yaml) | `external` [README](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/cf/README.md)



## Frequently asked questions

### 1. Does IAM Identity Center integrate with your identity provider?

IAM Identity Center uses SAML and SCIM (System for Cross-domain Identity Management), an open standard protocol, to integrate with your Identity Provider (IdP). Identity Center supports integration with leading IdPs including: Microsoft Entra ID, Ping ID, Okta, OneLogin, and Google Workspace.

Any Identity Provider that supports the SAML and SCIM protocol can integrate with Identity Center. Listed below are step-by-step instructions for various IDPs from [Identity source tutorials](https://docs.aws.amazon.com/singlesignon/latest/userguide/tutorials.html):
1. `external` [Configure SAML and SCIM with Microsoft Entra ID and IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/idp-microsoft-entra.html)
1. `external` [Configure SAML and SCIM with Okta and IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/gs-okta.html)
1. `external` [Configure SAML and SCIM with Google Workspace and IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/gs-gwp.html)
1. `external` [Configure SAML and SCIM with Ping ID - PingOne and IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/pingone-idp.html)
1. `external` [Configure SAML and SCIM with Ping ID - PingFederate and IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/pingfederate-idp.html)
1. `external` [Configure SAML and SCIM with OneLogin and IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/onelogin-idp.html)

### 2. What are the benefits of integrating Identity Center with your identity provider?

By integrating Identity Center with your existing identity provider (Azure AD, Okta, Ping ID), you can leverage your existing identity infrastructure while gaining these benefits for AWS access management.

1. **Centralized Identity Management:** Integrating with Identity Center allows you to manage user identities in one central location. This means you won't need to maintain separate user directories across different systems. As a result, this significantly reduces the administrative overhead involved in managing user identities.
1. **Enhanced Security:** The integration enables single sign-on (SSO) capabilities across your AWS accounts and applications. This allows you to enforce consistent security policies throughout your organization. You'll have better control over user access and permissions across all your AWS resources.
1. **Improved User Experience:** Your users will only need to remember one set of credentials to access multiple systems. They can seamlessly access multiple AWS accounts and applications through a single sign-on experience. This reduces password fatigue and the associated security risks that come with managing multiple credentials.
1. **Compliance Benefits:** The integration makes user access auditing much more straightforward and efficient. It provides streamlined user lifecycle management across your organization. You'll have better control over access permissions and can quickly revoke access when needed.
1. **Operational Efficiency:** With the integration in place, you can automate user provisioning and deprovisioning processes. This leads to reduced IT support costs as there's less manual intervention needed. The integration also enables faster onboarding and offboarding processes for your organization.


## License

This library is licensed under the MIT-0 License. See the [LICENSE](../LICENSE) file.