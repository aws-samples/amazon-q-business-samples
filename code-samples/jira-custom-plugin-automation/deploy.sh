#!/bin/bash

# Multi-environment deployment script for Jira Q Business Custom Plugin

set -e

show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  config   - Validate configuration only"
    echo "  build    - Install deps and build"
    echo "  deploy   - Full deployment (default)"
    echo "  destroy  - Destroy the stack"
    echo "  list     - List deployed stacks"
    echo "  help     - Show this help"
    echo ""
    echo "Options:"
    echo "  --stack-name NAME    Stack name (default: jira-custom-plugins)"
    echo "  --environment ENV    Environment suffix (dev/staging/prod)"
    echo "  --region REGION      AWS region (default: current AWS CLI region)"
    echo "  --profile PROFILE    AWS profile to use"
    echo "  --config FILE        Config file to use (default: config.json)"
    echo ""
    echo "Examples:"
    echo "  $0 deploy --stack-name dev-jira-plugins --environment dev"
    echo "  $0 deploy --stack-name prod-jira-plugins --environment prod --region us-west-2"
    echo "  $0 destroy --stack-name test-jira-plugins"
    echo "  $0 list"
}

# Default values
COMMAND=""
STACK_NAME="jira-custom-plugins"
ENVIRONMENT=""
REGION=""
PROFILE=""
CONFIG_FILE="config.json"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        config|build|deploy|destroy|list|help|--help|-h)
            if [ -z "$COMMAND" ]; then
                COMMAND=$1
            else
                echo "❌ Error: Multiple commands specified"
                show_usage
                exit 1
            fi
            ;;
        --stack-name)
            STACK_NAME="$2"
            shift
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift
            ;;
        --region)
            REGION="$2"
            shift
            ;;
        --profile)
            PROFILE="$2"
            shift
            ;;
        --config)
            CONFIG_FILE="$2"
            shift
            ;;
        *)
            echo "❌ Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
    shift
done

# Set default command if none specified
if [ -z "$COMMAND" ]; then
    COMMAND="deploy"
fi

# Handle help command
if [ "$COMMAND" = "help" ] || [ "$COMMAND" = "--help" ] || [ "$COMMAND" = "-h" ]; then
    show_usage
    exit 0
fi

# Validate command
case $COMMAND in
    config|build|deploy|destroy|list)
        ;;
    *)
        echo "❌ Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac

# Build final stack name with environment suffix
FINAL_STACK_NAME="$STACK_NAME"
if [ -n "$ENVIRONMENT" ]; then
    FINAL_STACK_NAME="${STACK_NAME}-${ENVIRONMENT}"
fi

# Build CDK command options
CDK_OPTIONS=""
if [ -n "$REGION" ]; then
    CDK_OPTIONS="$CDK_OPTIONS --region $REGION"
fi
if [ -n "$PROFILE" ]; then
    CDK_OPTIONS="$CDK_OPTIONS --profile $PROFILE"
fi

echo "🚀 Jira Q Business Plugin - $COMMAND"
echo "📋 Configuration:"
echo "   Stack Name: $FINAL_STACK_NAME"
echo "   Config File: $CONFIG_FILE"
if [ -n "$ENVIRONMENT" ]; then
    echo "   Environment: $ENVIRONMENT"
fi
if [ -n "$REGION" ]; then
    echo "   Region: $REGION"
fi
if [ -n "$PROFILE" ]; then
    echo "   AWS Profile: $PROFILE"
fi
echo ""

# Configuration check function
check_config() {
    echo "📋 Configuration Check:"

    # Check if config file exists
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "   ❌ Error: $CONFIG_FILE not found!"
        echo ""
        echo "   Please create your configuration file:"
        if [ "$CONFIG_FILE" = "config.json" ]; then
            echo "     cp config.example.json config.json"
            echo "     # Edit config.json with your settings"
        else
            echo "     cp config.example.json $CONFIG_FILE"
            echo "     # Edit $CONFIG_FILE with your settings"
        fi
        echo ""
        exit 1
    fi

    echo "   ✅ $CONFIG_FILE found"
    
    # Use dev-tools for comprehensive configuration validation
    echo "   🔍 Running configuration validation..."
    if npx ts-node scripts/dev-tools.ts validate "$CONFIG_FILE" > /dev/null 2>&1; then
        echo "   ✅ Configuration validation passed"
        
        # Extract basic info for display (simple JSON parsing)
        JIRA_BASE_URL=$(node -pe "JSON.parse(require('fs').readFileSync('$CONFIG_FILE', 'utf8')).jiraBaseUrl || 'Not set'")
        QBUSINESS_APP_ID=$(node -pe "JSON.parse(require('fs').readFileSync('$CONFIG_FILE', 'utf8')).qBusinessApplicationId || 'Not set'")
        API_KEY_SECRET_NAME=$(node -pe "JSON.parse(require('fs').readFileSync('$CONFIG_FILE', 'utf8')).jiraApiKeySecretName || 'jira-api-key'")
        
        echo "   Jira Base URL: $JIRA_BASE_URL"
        echo "   Q Business App: $QBUSINESS_APP_ID"
        echo "   API Key Secret: $API_KEY_SECRET_NAME"
    else
        echo "   ❌ Configuration validation failed"
        echo ""
        echo "   Please run the validation manually to see detailed errors:"
        echo "     npm run validate"
        echo ""
        exit 1
    fi
}

# Removed individual functions - logic moved inline for simplicity

# List deployed stacks function
list_stacks() {
    echo "📋 Listing deployed Jira plugin stacks..."
    echo ""
    
    # Get all CloudFormation stacks that match our naming pattern
    aws cloudformation list-stacks $CDK_OPTIONS \
        --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
        --query 'StackSummaries[?contains(StackName, `jira`) && contains(StackName, `plugin`)].{Name:StackName,Status:StackStatus,Created:CreationTime}' \
        --output table || {
        echo "❌ Error listing stacks. Check your AWS credentials and region."
        exit 1
    }
    
    echo ""
    echo "💡 To get detailed information about a specific stack:"
    echo "   aws cloudformation describe-stacks --stack-name STACK_NAME $CDK_OPTIONS"
}

# Execute command
case $COMMAND in
    config)
        check_config
        ;;
    build)
        check_config
        echo "📦 Installing dependencies..."
        npm install
        echo "🔨 Building project..."
        npm run build
        ;;
    list)
        list_stacks
        ;;
    destroy)
        # Set region environment variable if region is specified (for destroy too)
        if [ -n "$REGION" ]; then
            export CDK_DEFAULT_REGION="$REGION"
            export AWS_DEFAULT_REGION="$REGION"
            echo "🌍 Using region: $REGION"
        fi
        
        echo "🗑️  Destroying stack: $FINAL_STACK_NAME"
        echo ""
        read -p "Are you sure you want to destroy the stack '$FINAL_STACK_NAME'? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🗑️  Destroying CDK stack..."
            npx cdk destroy $FINAL_STACK_NAME $CDK_OPTIONS --force
            echo "✅ Stack destroyed successfully!"
        else
            echo "❌ Destruction cancelled."
            exit 1
        fi
        ;;
    deploy)
        check_config
        echo "📦 Installing dependencies..."
        npm install
        echo "🔨 Building project..."
        
        # Set region environment variable if region is specified (before any CDK commands)
        if [ -n "$REGION" ]; then
            export CDK_DEFAULT_REGION="$REGION"
            export AWS_DEFAULT_REGION="$REGION"
            echo "🌍 Using region: $REGION"
        fi
        
        echo "🏗️ Bootstrapping CDK..."
        npx cdk bootstrap $CDK_OPTIONS
        echo "🚀 Deploying CDK stack: $FINAL_STACK_NAME"
        
        # Pass the stack name and config file to CDK
        export CDK_STACK_NAME="$FINAL_STACK_NAME"
        export CDK_CONFIG_FILE="$CONFIG_FILE"
        
        npx cdk deploy $FINAL_STACK_NAME $CDK_OPTIONS --require-approval never
        ;;
esac

# Show completion message for deploy command
if [ "$COMMAND" = "deploy" ]; then
    echo "✅ Deployment complete!"
    echo ""
    echo "�  Stack Information:"
    echo "   Stack Name: $FINAL_STACK_NAME"
    echo "   Config File: $CONFIG_FILE"
    if [ -n "$REGION" ]; then
        echo "   Region: $REGION"
    fi
    if [ -n "$PROFILE" ]; then
        echo "   AWS Profile: $PROFILE"
    fi
    echo ""
    echo "📝 Next steps:"

    echo "1. ✅ Jira metadata collection completed successfully using API key: $API_KEY_SECRET_NAME"
    echo "2. 🔑 NEXT: Set up OAuth for end users:"
    echo "   a. Create a Jira OAuth app at: https://developer.atlassian.com/console/myapps/"
    echo "   b. Configure the OAuth app with the redirect URI from your Q Business application"
    echo "   c. Update the OAuth secret in AWS Secrets Manager:"
    echo "      - Check the CloudFormation outputs for the OAuth secret name (search for '$FINAL_STACK_NAME')"
    echo "      - Update the secret with your Jira OAuth app credentials:"
    echo "        {\"client_id\": \"your-oauth-client-id\", \"client_secret\": \"your-oauth-client-secret\", \"redirect_uri\": \"your-redirect-uri\"}"
    echo "3. ✅ Custom plugins added to Q Business application: $QBUSINESS_APP_ID"
    echo "4. 🧪 Test the plugin functionality - users will authenticate via OAuth when creating issues"

    echo ""
    echo "🔐 Authentication Summary:"
    echo "   ✅ API Key: Successfully used for metadata collection during deployment"
    echo "   ⏳ OAuth: Still needs setup for end-user authentication when creating issues"
    echo "   📋 This separation ensures proper user attribution and permissions"
    
    echo ""
    echo "🛠️  Management Commands:"
    echo "   List all stacks:    $0 list"
    echo "   Destroy this stack: $0 destroy --stack-name $FINAL_STACK_NAME"
    if [ -n "$ENVIRONMENT" ]; then
        echo "   Deploy to another env: $0 deploy --stack-name $STACK_NAME --environment staging"
    fi
else
    echo "✅ $COMMAND completed!"
fi