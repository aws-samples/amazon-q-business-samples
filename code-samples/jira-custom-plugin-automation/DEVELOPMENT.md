# Development Guide

This guide covers the development workflow for the Amazon Q Business Jira Plugin Sample.

## Quick Start for Developers

1. **Clone and setup**:

    ```bash
    git clone <repository-url>
    cd code-samples/jira-custom-plugin-automation
    npm install
    ```

2. **Configure the project**:

    ```bash
    cp config.example.json config.json
    # Edit config.json with your settings
    ```

3. **Run quality checks**:

    ```bash
    npm run quality
    ```

4. **Validate and test**:
    ```bash
    npm run validate
    npm run test-local
    ```

## Development Commands

### Core Development

- `npm run dev` - Show development tools help
- `npm run build` - Compile TypeScript
- `npm run watch` - Watch mode compilation

### Quality Assurance

- `npm run quality` - Run all quality checks (lint + format + type-check)
- `npm run quality:fix` - Auto-fix quality issues
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix ESLint issues
- `npm run format` - Format code with Prettier
- `npm run format:check` - Check code formatting
- `npm run type-check` - TypeScript type checking

### Testing and Validation

- `npm run validate` - Validate configuration
- `npm run validate-keys` - Validate S3 key consistency
- `npm run test-local` - Test Lambda function locally (writes files instead of S3 upload)
- `npm run generate-specs` - Generate expected OpenAPI specs
- `npm run test` - Run Jest tests

### Security

- `npm run security:audit` - Full security audit
- `npm run security:check` - Security check with moderate threshold
- `npm run security:fix` - Auto-fix security issues

### Deployment

- `npm run pre-deploy` - Complete pre-deployment validation
- `npm run deploy` - Deploy to AWS
- `npm run clean` - Clean build artifacts
- `npm run fresh-install` - Clean install from scratch

## Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality:

### Installation

```bash
# Install pre-commit (Python required)
pip install pre-commit

# Install git hooks
pre-commit install
```

### What Gets Checked

- TypeScript type checking
- ESLint linting
- Prettier formatting
- Security audit (on push)
- Trailing whitespace
- File endings
- JSON/YAML syntax
- Large file detection

### Manual Hook Execution

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run eslint
```

## Development Workflow

### Standard Workflow

1. Make code changes
2. Run `npm run quality` to check for issues
3. Run `npm run validate` to check configuration
4. Run `npm run test-local` to test functionality
5. Commit changes (pre-commit hooks will run automatically)

### Before Deployment

1. Run `npm run pre-deploy` for comprehensive validation
2. Ensure all tests pass
3. Review security audit results
4. Deploy with `npm run deploy`

### Troubleshooting Development Issues

#### TypeScript Errors

```bash
npm run type-check
# Fix reported type issues
```

#### Linting Issues

```bash
npm run lint:fix
# Review and fix remaining issues manually
```

#### Formatting Issues

```bash
npm run format
# All formatting will be auto-fixed
```

#### Configuration Issues

```bash
npm run validate
# Follow the detailed error messages
```

#### Local Testing Issues

```bash
npm run test-local
# Check ./local-lambda-output/result.json for details
# OpenAPI specs are saved to ./local-lambda-output/ instead of S3
```

## Code Quality Standards

### TypeScript

- Strict mode enabled
- No implicit any
- Proper type annotations
- Interface definitions for complex objects

### ESLint Rules

- Security plugin enabled
- Prettier integration
- Node.js best practices
- TypeScript-specific rules

### Prettier Configuration

- 2-space indentation
- Single quotes
- Trailing commas
- Line width: 100 characters

### Security

- Path sanitization for file operations
- Input validation
- No hardcoded secrets
- Regular dependency audits

## File Structure

```
├── bin/                    # CDK app entry point
├── lib/                    # CDK stack definitions
├── lambda/                 # Lambda function code
├── scripts/                # Development tools
│   ├── dev-tools.ts       # Main development CLI
│   └── README.md          # Scripts documentation
├── test/                   # Jest tests
├── config.example.json     # Configuration template
├── .pre-commit-config.yaml # Pre-commit hooks
├── package.json           # Dependencies and scripts
└── README.md              # Main documentation
```

## Contributing

1. Follow the development workflow above
2. Ensure all quality checks pass
3. Add tests for new functionality
4. Update documentation as needed
5. Use conventional commit messages

## Getting Help

- Check the main README.md for usage instructions
- Review scripts/README.md for development tools
- Run `npm run dev` for development tool help
- Check the troubleshooting sections in documentation
