# Amazon Q Business Samples

[Amazon Q Business](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/what-is.html)  is a generative AI assistant that helps organizations find information, gain insights, and take action. It answers questions, provides summaries, generates content, and completes tasks securely using enterprise data and systems. Users can access the assistant through APIs, web chat, browser extensions, and integrations with Slack and Microsoft Teams.

This managed solution helps employees work more efficiently by supporting tasks like answering questions, discovering knowledge, writing emails, summarizing text, creating document outlines, and generating ideas. It streamlines activities such as document analysis, research, and comparative studies.

Key features include:
- Fast and accurate responses to complex questions using enterprise documents, images, files, and application data
- Access controls that align with user permissions
- Over 40 native connectors plus custom plugin capabilities for third-party integration
- QuickSight plugin integration for data insights
- No-code application creation using natural language through Amazon Q Apps
- More than 50 automated actions for tasks like Jira ticket creation and case updates

This repository contains how-to guides, introduction key use cases, and code samples to help you accelerate Amazon Q Business implementation.

## Index of samples, tutorials and how-to guides
List of Amazon Q Business code samples, tutorials, and how-to guides available in this and other repositories.

* &#128279; denotes link to external content or repository
* &#10784; denotes link to content in local repository

### Guides

* #### How-to
    1. &#128279;[Register web application with Amazon Cognito](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/cognito/register-webapp-with-cognito.md)
    1. &#128279;[Register web application with Microsoft Entra](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/entra/register-webapp-with-entra.md)
    1. &#128279;[How to find Microsoft Entra Issuer URI](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/entra/find-entra-issuer-url.md)
    1. &#128279;[Register web application with Okta](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/okta/register-webapp-with-okta.md)
    1. &#128279;[How to find Okta Issuer URI](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/okta/find-okta-issuer-url.md)

* #### Tutorials
    1. &#128279; [Configuring custom web application with Amazon Cognito and IAM Identity Center](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/cognito/config-webapp-using-cognito.md)
    1. &#128279; [Configuring custom web application with Microsoft Entra and IAM Identity Center](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/entra/config-webapp-using-entra.md)
    1. &#128279; [Configuring custom web application with Okta and IAM Identity Center](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/docs/tutorials/okta/config-webapp-using-okta.md)

### Code samples
* #### Python
    1. &#128279; [Simple custom data source sample](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/samples/custom_ds.py)
    1. &#10784; [Sample secure API access with IAM Federation](iam-federation-samples)
    1. &#128279; [IAM Identity Center trusted identity propagation demo](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/tree/main/webapp)

* #### Cloud Formation (CF) templates
    1. &#128279; [CF for configuring AWS IAM Identity Center](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/cf/qb-api-idc-config.yaml) | &#128279; [README](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/cf/README.md)
    1. &#128279; [CF to create Amazon Cognito user pool](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/cf/qb-api-poc-cognito.yaml) | &#128279; [README](https://github.com/aws-samples/configuring-qbusiness-with-idc-tti/blob/main/cf/README.md)

### Workshops and blogs

* #### Workshops
    1. [Innovate on enterprise data with generative AI & Amazon Q Business application](https://catalog.workshops.aws/amazon-q-business)
    1. [Integrate your application with Amazon Q Business identity-aware APIs](https://catalog.workshops.aws/amazon-q-business-api)

* #### Connectors
    1. &#128279; [Introducing document-level sync reports: Enhanced data sync visibility in Amazon Q Business](https://aws.amazon.com/blogs/machine-learning/introducing-document-level-sync-reports-enhanced-data-sync-visibility-in-amazon-q-business/)
    1. &#128279; [Connect Amazon Q Business to Microsoft SharePoint Online using least privilege access controls](https://aws.amazon.com/blogs/machine-learning/connect-amazon-q-business-to-microsoft-sharepoint-online-using-least-privilege-access-controls/)

* #### Security
    1. &#128279; [Enable or disable ACL crawling safely in Amazon Q Business](https://aws.amazon.com/blogs/machine-learning/enable-or-disable-acl-crawling-safely-in-amazon-q-business/)
    1. &#128279; [Query structured data from Amazon Q Business using Amazon QuickSight integration](https://aws.amazon.com/blogs/machine-learning/query-structured-data-from-amazon-q-business-using-amazon-quicksight-integration/)
    1. &#128279; [Build private and secure enterprise generative AI applications with Amazon Q Business using IAM Federation](https://aws.amazon.com/blogs/machine-learning/build-private-and-secure-enterprise-generative-ai-applications-with-amazon-q-business-using-iam-federation/)
    1. &#128279; [Configure Amazon Q Business with AWS IAM Identity Center trusted identity propagation](https://aws.amazon.com/blogs/machine-learning/configuring-amazon-q-business-with-aws-iam-identity-center-trusted-identity-propagation/)

* #### Customer
    1. &#128279; [London Stock Exchange Group uses Amazon Q Business to enhance post-trade client services](https://aws.amazon.com/blogs/machine-learning/london-stock-exchange-group-uses-amazon-q-business-to-enhance-post-trade-client-services/)

## Reporting security issues

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information on how report any security issues.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](./LICENSE) file.
