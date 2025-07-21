# Jira Custom Plugin Scripts

This directory contains the consolidated development tools for the Jira custom plugin automation.

## Scripts

### `dev-tools.ts` (Main Development Tool)

A comprehensive CLI tool for validation, testing, and debugging the Jira custom plugin automation. This is your primary development tool for working with the project.

#### Features

- **Configuration validation**: Ensures your config.json is properly structured
- **S3 key validation**: Validates consistency between Lambda and CDK key generation
- **Local Lambda testing**: Runs the Lambda function locally without deployment
- **OpenAPI spec generation**: Creates expected specs for comparison
- **Security-focused**: Includes path sanitization and validation
- **Multiple output formats**: Saves results to files for inspection

#### Usage

```bash
npx ts-node scripts/dev-tools.ts <command> [config-path] [args...]
```

#### Commands

- `validate`: Validate your configuration file

    ```bash
    npx ts-node scripts/dev-tools.ts validate
    npx ts-node scripts/dev-tools.ts validate custom-config.json
    ```

- `validate-keys`: Validate S3 key consistency between Lambda and CDK

    ```bash
    npx ts-node scripts/dev-tools.ts validate-keys
    npx ts-node scripts/dev-tools.ts validate-keys config.json my-stack-name
    ```

- `test`: Test the Lambda function locally (no AWS deployment needed)

    ```bash
    npx ts-node scripts/dev-tools.ts test
    npx ts-node scripts/dev-tools.ts test config.json ./test-output
    ```

- `all`: Run validation and Lambda testing in sequence

    ```bash
    npx ts-node scripts/dev-tools.ts all
    ```

- `help` (or no command): Show usage information

#### What Each Command Does

**Validate:**

- Checks required fields (jiraBaseUrl, qBusinessApplicationId)
- Validates plugin configuration (projects, flexibleIssueTypes, or built-in plugin)
- Ensures metadataProject is set when using flexible issue types
- Provides detailed feedback on configuration issues

**Validate-Keys:**

- Compares S3 key generation patterns between Lambda function and CDK stack
- Identifies mismatches that could cause "specified key does not exist" errors
- Shows expected S3 keys for debugging deployment issues
- Provides AWS CLI commands to verify deployed objects

**Test:**

- Sets up a mock CloudFormation event
- Runs the actual Lambda handler function locally
- Requires Jira API secret in AWS Secrets Manager (same region as your AWS CLI default)
- Saves results to `./local-lambda-output/result.json`
- Writes OpenAPI specs to local files instead of uploading to S3 (no AWS permissions needed)
- Shows success/failure status and generated spec count

#### NPM Script Shortcuts

The main package.json includes shortcuts for common dev-tools commands:

```bash
npm run validate       # Same as: npx ts-node scripts/dev-tools.ts validate
npm run validate-keys  # Same as: npx ts-node scripts/dev-tools.ts validate-keys
npm run test-local     # Same as: npx ts-node scripts/dev-tools.ts test
npm run generate-specs # Same as: npx ts-node scripts/dev-tools.ts generate-specs
npm run dev            # Shows dev-tools help
```

#### Quality Assurance Commands

Enhanced quality checks for robust development:

```bash
npm run quality        # Run all quality checks (lint, format, type-check)
npm run quality:fix    # Fix all auto-fixable quality issues
npm run pre-deploy     # Complete pre-deployment validation
npm run security:check # Security audit with moderate level threshold
```

#### Example Workflow

1. **Start with validation**:

    ```bash
    npm run validate
    ```

2. **Test the Lambda locally** to verify it works:

    ```bash
    npm run test-local
    ```

3. **Review the generated specs** in `./local-lambda-output/`

This workflow lets you develop and debug without deploying to AWS.

## Getting Started

### Enhanced Development Workflow

The recommended workflow using the consolidated dev-tools script and quality assurance:

1. **Configure your project**: Edit `config.json` with your Jira settings
2. **Run quality checks**: `npm run quality` (lint, format, type-check)
3. **Validate configuration**: `npm run validate`
4. **Validate S3 keys**: `npm run validate-keys` (helps debug deployment issues)
5. **Test locally**: `npm run test-local` (requires valid Jira credentials)
6. **Pre-deployment check**: `npm run pre-deploy` (comprehensive validation)

### Pre-commit Quality Checks

The project includes pre-commit hooks for automatic quality assurance:

```bash
# Install pre-commit (if not already installed)
pip install pre-commit

# Install the git hook scripts
pre-commit install

# Run hooks on all files (optional)
pre-commit run --all-files
```

Pre-commit hooks will automatically run:

- TypeScript type checking
- ESLint linting
- Prettier format checking
- Security audit (on pre-push)
- Basic file checks (trailing whitespace, JSON/YAML validation)

### Troubleshooting Deployment Issues

If you encounter "specified key does not exist" errors during deployment:

1. **Check S3 key consistency**:

    ```bash
    npm run validate-keys
    ```

2. **Verify your stack name matches** what you're using in deployment

3. **Check deployed S3 objects** after deployment:

    ```bash
    # Get your bucket name
    aws cloudformation describe-stacks --stack-name YOUR_STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`OpenApiSpecBucketName`].OutputValue' --output text

    # List objects in bucket
    aws s3 ls s3://YOUR-BUCKET-NAME/ --recursive
    ```

### Local Testing

The dev-tools script can run your Lambda function locally without deploying to AWS:

- **Requirements**: Valid Jira API credentials in AWS Secrets Manager
- **Output**: Results saved to `./local-lambda-output/result.json`
- **OpenAPI Specs**: Written to local files instead of S3 upload
- **Benefits**: Fast iteration without deployment costs or AWS permissions

### Configuration Validation

The validation command checks:

- Required fields (jiraBaseUrl, qBusinessApplicationId)
- Plugin configuration consistency
- Metadata project requirements for flexible issue types
- Overall configuration structure
