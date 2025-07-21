# Advanced Deployment Guide

This guide covers advanced deployment scenarios including multi-environment setups, CI/CD integration, and production best practices.

## Multi-Environment Deployments

### Environment-Specific Configurations

Create separate config files for each environment:

**config.dev.json** (Development):

```json
{
    "jiraBaseUrl": "https://dev-company.atlassian.net",
    "jiraApiKeySecretName": "jira-api-key-dev",
    "qBusinessApplicationId": "dev-app-id-here",
    "projects": [{ "key": "DEV", "name": "Development", "issueTypes": ["Task", "Bug"] }]
}
```

**config.prod.json** (Production):

```json
{
    "jiraBaseUrl": "https://company.atlassian.net",
    "jiraApiKeySecretName": "jira-api-key-prod",
    "qBusinessApplicationId": "prod-app-id-here",
    "projects": [{ "key": "PROD", "name": "Production", "issueTypes": ["Bug", "Epic"] }],
    "enableBuiltInJiraPlugin": true,
    "pluginVersion": "1.0.0"
}
```

### Advanced Deployment Commands

```bash
# Development environment
./deploy.sh deploy --stack-name dev-jira --environment dev --config config.dev.json

# Production in different region
./deploy.sh deploy --stack-name prod-jira --environment prod --config config.prod.json --region us-west-2

# Multi-region deployment for redundancy
./deploy.sh deploy --stack-name prod-jira-east --config config.prod.json --region us-east-1
./deploy.sh deploy --stack-name prod-jira-west --config config.prod.json --region us-west-2

# Using specific AWS profile
./deploy.sh deploy --stack-name staging-jira --profile staging-account
```

**Available Commands:**

```bash
./deploy.sh help                    # Show all options
./deploy.sh list                    # List deployed stacks
./deploy.sh destroy --stack-name my-stack  # Remove a deployment
./deploy.sh config --config config.dev.json  # Validate configuration
```

## Resource Isolation

Each deployment creates completely isolated resources:

**Per-Stack Resources:**

- **S3 Bucket**: `qbusiness-jira-openapi-{hash}-{account}-{region}`
- **Lambda Function**: `{stack-name}-JiraMetadataFunction-{hash}`
- **OAuth Secret**: `jira-oauth-{stack-name}`
- **Q Business Plugins**: `Create-{IssueType}-Issue`, `Create-{IssueType}-{ProjectKey}`

**Shared Resources (by design):**

- Q Business applications (you specify different ones per environment)
- Jira API key secrets (you create environment-specific ones)

## Automatic Metadata Updates

The deployment system automatically updates Jira metadata on every deployment to ensure OpenAPI specs reflect current field requirements.

### How It Works

1. **Configuration Hash**: Generated from your Jira configuration plus timestamp
2. **Lambda Execution**: Fetches latest Jira metadata during deployment
3. **Spec Regeneration**: OpenAPI specs updated with current field requirements
4. **Plugin Updates**: Q Business plugins automatically use updated specs

### Benefits

- ✅ **Always current**: Field requirements match your Jira configuration
- ✅ **No manual intervention**: Updates happen automatically
- ✅ **Consistent validation**: Q Business enforces same rules as Jira
- ✅ **Change detection**: New fields or requirement changes captured

### Manual Version Updates

Force plugin updates without other changes:

```json
{
    "pluginVersion": "1.0.1"
}
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy Jira Plugins

on:
    push:
        branches: [main]
    workflow_dispatch:

jobs:
    deploy:
        runs-on: ubuntu-latest
        strategy:
            matrix:
                environment: [dev, staging, prod]

        steps:
            - uses: actions/checkout@v3

            - name: Setup Node.js
              uses: actions/setup-node@v3
              with:
                  node-version: '18'

            - name: Install dependencies
              run: npm install

            - name: Configure AWS credentials
              uses: aws-actions/configure-aws-credentials@v2
              with:
                  aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
                  aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
                  aws-region: us-east-1

            - name: Validate configuration
              run: ./deploy.sh config --config config.${{ matrix.environment }}.json

            - name: Deploy
              run: ./deploy.sh deploy --stack-name ${{ matrix.environment }}-jira --environment ${{ matrix.environment }} --config config.${{ matrix.environment }}.json
```

### AWS CodePipeline Integration

```yaml
# buildspec.yml
version: 0.2

phases:
    install:
        runtime-versions:
            nodejs: 18
        commands:
            - npm install -g aws-cdk
            - npm install

    pre_build:
        commands:
            - echo "Validating configuration..."
            - ./deploy.sh config --config config.$ENVIRONMENT.json

    build:
        commands:
            - echo "Deploying to $ENVIRONMENT..."
            - ./deploy.sh deploy --stack-name $ENVIRONMENT-jira --environment $ENVIRONMENT --config config.$ENVIRONMENT.json --region $AWS_DEFAULT_REGION

artifacts:
    files:
        - '**/*'
```

## Production Best Practices

### 1. Deployment Safety

```bash
# Always validate configuration first
./deploy.sh config --config config.prod.json

# Deploy to staging before production
./deploy.sh deploy --stack-name staging-jira --config config.staging.json

# Use explicit parameters for production
./deploy.sh deploy --stack-name prod-jira --environment prod --config config.prod.json --region us-west-2
```

### 2. Naming Conventions

```bash
# Good stack names
dev-jira-plugins
staging-jira-plugins
prod-jira-plugins-east
prod-jira-plugins-west

# Avoid generic names
my-stack, test, jira
```

### 3. Security Best Practices

- **Environment-specific secrets**: Use different API keys per environment
- **Least privilege IAM**: Minimal required permissions
- **Secret rotation**: Regular API key updates
- **Audit logging**: Enable CloudTrail for deployment tracking

### 4. Monitoring and Alerting

```bash
# Set up CloudWatch alarms for Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name "JiraPlugin-Lambda-Errors" \
  --alarm-description "Lambda function errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold

# Monitor deployment costs
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

## Troubleshooting Advanced Scenarios

### Multi-Region Deployment Issues

**Problem**: Resources not found in different regions

```bash
# Solution: Ensure consistent region usage
./deploy.sh deploy --region us-east-1
./deploy.sh destroy --region us-east-1  # Same region for cleanup
```

**Problem**: Cross-region secret access

```bash
# Solution: Create secrets in each deployment region
aws secretsmanager create-secret \
  --name "jira-api-key-prod" \
  --secret-string '{"email": "user@example.com", "apiToken": "token"}' \
  --region us-east-1

aws secretsmanager create-secret \
  --name "jira-api-key-prod" \
  --secret-string '{"email": "user@example.com", "apiToken": "token"}' \
  --region us-west-2
```

### CI/CD Pipeline Failures

**Problem**: Permission denied in CI/CD

```bash
# Solution: Ensure CI/CD role has required permissions
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "s3:*",
        "lambda:*",
        "iam:*",
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "*"
    }
  ]
}
```

**Problem**: Configuration validation fails in pipeline

```bash
# Solution: Store config files in repository or use parameter store
aws ssm put-parameter \
  --name "/jira-plugin/prod/config" \
  --value file://config.prod.json \
  --type SecureString
```

### Large-Scale Deployments

**Problem**: Lambda timeout with many projects

```bash
# Solution: Reduce projects per deployment or increase timeout
# In CDK stack, increase Lambda timeout:
timeout: Duration.minutes(5)
```

**Problem**: S3 bucket conflicts across accounts

```bash
# Solution: Use account-specific bucket naming
# Bucket names automatically include account ID: qbusiness-jira-openapi-{hash}-{account}-{region}
```

## Migration Strategies

### From Single to Multi-Environment

1. **Backup current deployment**:

    ```bash
    cp config.json config.backup.json
    ```

2. **Create environment-specific configs**:

    ```bash
    cp config.json config.prod.json
    # Edit config.prod.json with production values
    ```

3. **Deploy with new stack name**:

    ```bash
    ./deploy.sh deploy --stack-name prod-jira-plugins --config config.prod.json
    ```

4. **Verify and cleanup**:
    ```bash
    # Test new deployment
    # Clean up old deployment when satisfied
    ./deploy.sh destroy --stack-name CustomPluginJiraStack2
    ```

### Zero-Downtime Updates

1. **Deploy to new stack**:

    ```bash
    ./deploy.sh deploy --stack-name prod-jira-v2 --config config.prod.json
    ```

2. **Test new deployment**:

    ```bash
    # Verify plugins work in Q Business
    # Test issue creation workflows
    ```

3. **Switch traffic and cleanup**:
    ```bash
    # Update Q Business to use new plugins
    ./deploy.sh destroy --stack-name prod-jira-v1
    ```

## Cost Optimization

### Resource Sizing

- **Lambda**: Default 128MB memory sufficient for most deployments
- **S3**: Lifecycle policies for old spec versions
- **Secrets**: Use single secret per environment, not per stack

### Monitoring Costs

```bash
# Get deployment costs by service
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --filter file://cost-filter.json

# cost-filter.json
{
  "Dimensions": {
    "Key": "RESOURCE_ID",
    "Values": ["your-stack-name*"]
  }
}
```

### Cleanup Strategies

```bash
# List all stacks for cleanup
./deploy.sh list

# Remove unused environments
./deploy.sh destroy --stack-name old-test-stack

# Clean up orphaned S3 buckets (if stack deletion fails)
aws s3 rb s3://qbusiness-jira-openapi-hash-account-region --force
```
