# Amazon Q Business Samples

> This repository provides guides, use cases, and code samples for implementing Amazon Q Business.

## Contents

- [Introduction to Amazon Q Business](introduction-to-qbusiness) - Learn the basics of the service
- [Identity management](identity-management) - Guides for configuring identity providers
- [Connectors](connectors) - Tips for setting up connector
- [Code samples](code-samples) - Library of code samples


## Getting started

To get started ensure your AWS account has been allow-listed to access [Amazon Q Business](https://aws.amazon.com/q/business/) service.

### Enable AWS IAM permissions for Amazon Q Business

Your AWS organization administrator must provide your AWS identity sufficient [AWS IAM permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html) to use the Amazon Q Business service.

- To grant Amazon Q Business access to your identity, your administrator must attach the following permissions:

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "QBusinessFullAccess",
            "Effect": "Allow",
            "Action": ["qbusiness:*", "qapps:*"],
            "Resource": "*"
        }
    ]
}
```

- If you're using a customer managed key, add the following permissions:
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
```
- To allow Amazon Q to assign user subscriptions, use the following role policy
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "QBusinessSubscriptionPermissions",
            "Effect": "Allow",
            "Action": [
                "qbusiness:UpdateSubscription",
                "qbusiness:CreateSubscription",
                "qbusiness:CancelSubscription",
                "qbusiness:ListSubscriptions"
            ],
            "Resource": [
             "arn:aws:qbusiness:{{region}}:{{source_account}}:application/{{application_id}}",
             "arn:aws:qbusiness:{{region}}:{{source_account}}:application/{{application_id}}/subscription/{{subscription_id}}"
            ]
        },
        {
            "Sid": "QBusinessServicePermissions",
            "Effect": "Allow",
            "Action": [
                "user-subscriptions:UpdateClaim",
                "user-subscriptions:CreateClaim",
                "organizations:DescribeOrganizations",
                "iam:CreateServiceLinkedRole",
                "sso-directory:DescribeGroup",
                "sso-directory:DescribeUser",
                "sso:DescribeApplication",
                "sso:DescribeInstance"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}
```

For more information on the fine-grained action and resource permissions in Bedrock, check out the Bedrock Developer Guide.

## Contributing

We welcome community contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Reporting security issues

Please refer to the [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) document for information on how to report security issues. Do **not** create a public GitHub issue for security-related concerns.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](./LICENSE) file.
