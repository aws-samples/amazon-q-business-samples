# Amazon Q Business Samples

This repository provides guides, use cases, and code samples for implementing Amazon Q Business.

## Contents

- [Introduction to Amazon Q Business](introduction-to-qbusiness) - Learn the basics of the service
- [Identity management](identity-management) - Guides for configuring identity providers
- [Connectors](connectors) - Tips for setting up connectors
- [Code samples](code-samples) - Library of code samples


## Getting started

To get started ensure your AWS account has been allow-listed to access [Amazon Q Business](https://aws.amazon.com/q/business/) service. Then proceed to creating your first application with [Learn to create and configure Amazon Q Business application](https://catalog.workshops.aws/amazon-q-business/en-US/200-configure-application).

### Allow-listing Amazon Q Business

Your AWS organization administrator must provide your AWS identity sufficient [AWS IAM permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html) to use the Amazon Q Business service.

- To grant Amazon Q Business access to your identity, your administrator must attach the following permissions (Note: `qapps` and `iam` are optional):

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "QBusinessFullAccess",
            "Effect": "Allow",
            "Action": [
                "qbusiness:*",
                "qapps:*",
                "iam:CreateServiceLinkedRole"
            ],
            "Resource": "*"
        }
    ]
}
```

- If you're project plans to use customer managed key, add the following permissions:
```
"kms:DescribeKey"
"kms:CreateGrant"
```

- If you're using IAM Identity Center, add the following permissions:
```
"sso:CreateApplication"
"sso:PutApplicationAuthenticationMethod"
"sso:PutApplicationAccessScope"
"sso:PutApplicationGrant"
"sso:DeleteApplication"
"sso-directory:DescribeGroup"
"sso-directory:DescribeUser"
"sso:DescribeApplication"
"sso:DescribeInstance"
"organizations:DescribeOrganizations"
```

- To allow Amazon Q Business application administrator to assign user subscriptions, use the following role policy
```
"user-subscriptions:UpdateClaim"
"user-subscriptions:CreateClaim"
```

For more information on the fine-grained action and resource permissions in Bedrock, check out the Bedrock Developer Guide.

### Create your first application
1. `external` [Learn to create and configure Amazon Q Business application](https://catalog.workshops.aws/amazon-q-business/en-US/200-configure-application)

## Contributing

We welcome community contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Reporting security issues

Please refer to the [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) document for information on how to report security issues. Do **not** create a public GitHub issue for security-related concerns.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](./LICENSE) file.
