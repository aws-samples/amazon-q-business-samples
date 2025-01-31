# Allow-listing Amazon Q Business

To use Amazon Q Business, your AWS account administrator needs to configure the appropriate [AWS IAM permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html) for your identity.

> ⚠️ **Note:** For enterprises using AWS Organizations, these permissions must also be allowed through service control policies (SCPs) at the organization level.

## Required permissions

#### Core Amazon Q Business access permissions

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "QBusinessFullAccess",
            "Effect": "Allow",
            "Action": [
                "qbusiness:*",
                "user-subscriptions:UpdateClaim",
                "user-subscriptions:CreateClaim"
            ],
            "Resource": "*"
        }
    ]
}
```

#### Add [service-linked role](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create-service-linked-role.html) useful to reduce custom roles (includes predefined permissions by the service)
```
"iam:CreateServiceLinkedRole"
```

#### Add [Amazon Q Apps](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/purpose-built-qapps.html) permissions (if using Apps features)
```
"qapps:*"
```

#### Add [Amazon QuickSight](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/create-application-quicksight.html) permissions (if creating QuickSight application)
```
"quicksight:*"
```

#### Add customer managed key permissions (if applicable)
```
"kms:DescribeKey"
"kms:CreateGrant"
```

#### Add IAM Identity Center permissions (if using Identity Center)
```
"sso:CreateApplication"
"sso:PutApplicationAuthenticationMethod"
"sso:PutApplicationAccessScope"
"sso:PutApplicationGrant"
"sso:DeleteApplication"
```

#### Add additional user subscription management permissions (if using Identity Center) 
```
"sso-directory:DescribeGroup"
"sso-directory:DescribeUser"
"sso:DescribeApplication"
"sso:DescribeInstance"
"organizations:DescribeOrganizations"
```

For detailed information on required permissions, refer to the [Amazon Q Business documentation](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/setting-up.html#permissions).
