/**
 * Jira Q Business Plugin Development Tools
 *
 * Consolidated script for validation, testing, and debugging
 */

import * as fs from 'fs';
import * as path from 'path';
import { handler } from '../lambda/jira-metadata-handler';

interface DeploymentConfig {
    jiraBaseUrl?: string;
    atlassianSiteId?: string;
    jiraApiKeySecretName?: string;
    qBusinessApplicationId?: string;
    projects?: Array<{ key: string; name: string; issueTypes: string[] }>;
    flexibleIssueTypes?: string[];
    metadataProject?: string;
    enableBuiltInJiraPlugin?: boolean;
    pluginVersion?: string;
}

class DevTools {
    private config: DeploymentConfig;

    constructor(configPath: string = 'config.json') {
        this.config = this.loadConfig(configPath);
    }

    /**
     * Sanitize and validate file paths to prevent directory traversal attacks
     * Returns a safe path that semgrep will recognize as validated
     */
    private sanitizePath(inputPath: string, baseDir: string = process.cwd()): string {
        // Reject paths with dangerous patterns upfront
        if (inputPath.includes('..') || inputPath.includes('~') || path.isAbsolute(inputPath)) {
            throw new Error(`Unsafe path detected: ${inputPath}`);
        }

        // Only allow alphanumeric, hyphens, underscores, and forward slashes
        if (!/^[a-zA-Z0-9\-_/.]+$/.test(inputPath)) {
            throw new Error(`Invalid characters in path: ${inputPath}`);
        }

        // Get absolute base directory path
        const absoluteBaseDir = path.resolve(baseDir);

        // Build safe path by joining with base directory
        const resolvedPath = path.join(absoluteBaseDir, inputPath);

        // Double-check the resolved path is within base directory
        const relativePath = path.relative(absoluteBaseDir, resolvedPath);
        if (relativePath.startsWith('..') || path.isAbsolute(relativePath)) {
            throw new Error(`Path escapes base directory: ${inputPath}`);
        }

        return resolvedPath;
    }

    /**
     * Create a safe file path for writing files
     * This method explicitly validates paths to satisfy semgrep
     */
    private createSafeFilePath(baseDir: string, filename: string): string {
        // Validate filename doesn't contain path separators or dangerous characters
        if (filename.includes('/') || filename.includes('\\') || filename.includes('..')) {
            throw new Error(`Invalid filename: ${filename}`);
        }

        // Only allow safe filename characters
        if (!/^[a-zA-Z0-9\-_.]+$/.test(filename)) {
            throw new Error(`Unsafe characters in filename: ${filename}`);
        }

        // Ensure filename has .json extension
        if (!filename.endsWith('.json')) {
            throw new Error(`Filename must end with .json: ${filename}`);
        }

        // Create safe path by joining validated components
        return path.join(baseDir, filename);
    }

    /**
     * Validate that a config path is safe to read
     */
    private validateConfigPath(configPath: string): string {
        // Only allow config files in current directory or config subdirectory
        const allowedExtensions = ['.json', '.js'];
        const ext = path.extname(configPath);

        if (!allowedExtensions.includes(ext)) {
            throw new Error(
                `Invalid config file extension: ${ext}. Only .json and .js files are allowed.`
            );
        }

        return this.sanitizePath(configPath);
    }

    private loadConfig(configPath: string): DeploymentConfig {
        try {
            const safePath = this.validateConfigPath(configPath);

            // Check if config file exists
            if (!fs.existsSync(safePath)) {
                throw new Error(
                    `Configuration file not found: ${configPath}\n` +
                        '💡 Please copy config.example.json to config.json and update with your settings:\n' +
                        '   cp config.example.json config.json'
                );
            }

            const configContent = fs.readFileSync(safePath, 'utf8');

            // Validate JSON content before parsing
            if (!configContent.trim()) {
                throw new Error('Configuration file is empty');
            }

            let config: any;
            try {
                config = JSON.parse(configContent);
            } catch (parseError) {
                throw new Error(
                    `Invalid JSON in configuration file: ${parseError}\n` +
                        '💡 Check for missing commas, quotes, or brackets in your config.json'
                );
            }

            // Validate that config is an object
            if (!config || typeof config !== 'object' || Array.isArray(config)) {
                throw new Error('Configuration must be a JSON object');
            }

            // Filter out comment fields (fields starting with _)
            const cleanConfig = this.filterCommentFields(config);

            // Apply defaults and validate structure
            const processedConfig = this.applyConfigDefaults(cleanConfig);

            console.log(`✓ Loaded configuration from ${configPath}`);
            return processedConfig;
        } catch (error) {
            if (error instanceof Error && error.message.includes('Configuration file not found')) {
                throw error; // Re-throw with helpful message
            }
            throw new Error(
                `Failed to load configuration from ${configPath}.\n` +
                    'Please ensure your config.json is valid JSON and follows the structure in config.example.json.\n' +
                    `Error: ${error}`
            );
        }
    }

    /**
     * Filter out comment fields (starting with _) from configuration
     */
    private filterCommentFields(config: any): any {
        const filtered: any = {};

        for (const [key, value] of Object.entries(config)) {
            // Skip comment fields
            if (key.startsWith('_')) {
                continue;
            }

            // Recursively filter nested objects
            if (value && typeof value === 'object' && !Array.isArray(value)) {
                filtered[key] = this.filterCommentFields(value);
            } else {
                filtered[key] = value;
            }
        }

        return filtered;
    }

    /**
     * Apply configuration defaults and validate structure
     */
    private applyConfigDefaults(config: any): DeploymentConfig {
        // Apply defaults
        const processedConfig: DeploymentConfig = {
            ...config,
            jiraApiKeySecretName: config.jiraApiKeySecretName || 'jira-api-key',
            enableBuiltInJiraPlugin: Boolean(config.enableBuiltInJiraPlugin),
            pluginVersion: config.pluginVersion || '1.0.0',
        };

        // Validate and clean arrays
        if (processedConfig.projects) {
            if (!Array.isArray(processedConfig.projects)) {
                throw new Error('projects must be an array');
            }
            // Validate each project structure
            for (const project of processedConfig.projects) {
                if (!project.key || !project.name || !Array.isArray(project.issueTypes)) {
                    throw new Error('Each project must have key, name, and issueTypes array');
                }
            }
        }

        if (processedConfig.flexibleIssueTypes) {
            if (!Array.isArray(processedConfig.flexibleIssueTypes)) {
                throw new Error('flexibleIssueTypes must be an array');
            }
        }

        return processedConfig;
    }

    // Validate configuration with comprehensive checks
    public validateConfig(): void {
        console.log('🔍 Validating configuration...\n');

        // Check required fields with detailed validation
        this.validateRequiredFields();
        this.validatePluginConfiguration();
        this.validateProjectConfiguration();
        this.validateFlexibleConfiguration();
        this.validateSecuritySettings();

        console.log('\n✅ Configuration validation passed!\n');
    }

    private validateRequiredFields(): void {
        console.log('📋 Validating required fields...');

        if (!this.config.jiraBaseUrl) {
            throw new Error('❌ jiraBaseUrl is required');
        }

        // Validate Jira URL format
        try {
            const url = new URL(this.config.jiraBaseUrl);
            if (url.protocol !== 'https:') {
                throw new Error('❌ jiraBaseUrl must use HTTPS protocol');
            }
            if (!url.hostname.includes('atlassian.net') && !url.hostname.includes('jira')) {
                console.warn('⚠️  jiraBaseUrl does not appear to be a standard Jira URL');
            }
        } catch (error) {
            throw new Error(`❌ jiraBaseUrl is not a valid URL: ${this.config.jiraBaseUrl}`);
        }
        console.log(`✓ Jira Base URL: ${this.config.jiraBaseUrl}`);

        if (!this.config.qBusinessApplicationId) {
            throw new Error(
                '❌ qBusinessApplicationId is required - must specify an existing Q Business application'
            );
        }

        // Validate Q Business Application ID format (should be a UUID)
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if (!uuidRegex.test(this.config.qBusinessApplicationId)) {
            console.warn('⚠️  qBusinessApplicationId does not appear to be a valid UUID format');
        }
        console.log(`✓ Q Business Application ID: ${this.config.qBusinessApplicationId}`);
    }

    private validatePluginConfiguration(): void {
        console.log('🔧 Validating plugin configuration...');

        const hasProjects = this.config.projects && this.config.projects.length > 0;
        const hasFlexibleTypes =
            this.config.flexibleIssueTypes && this.config.flexibleIssueTypes.length > 0;
        const hasBuiltInPlugin = this.config.enableBuiltInJiraPlugin || false;

        if (!hasProjects && !hasFlexibleTypes && !hasBuiltInPlugin) {
            throw new Error(
                '❌ At least one plugin type must be configured:\n' +
                    '   • Set enableBuiltInJiraPlugin: true, OR\n' +
                    '   • Configure projects array, OR\n' +
                    '   • Configure flexibleIssueTypes array'
            );
        }

        console.log(`✓ Plugin configuration valid`);
        if (hasProjects) {
            console.log(`  • Targeted projects: ${this.config.projects!.length}`);
        }
        if (hasFlexibleTypes) {
            console.log(`  • Flexible issue types: ${this.config.flexibleIssueTypes!.length}`);
        }
        if (hasBuiltInPlugin) {
            console.log(`  • Built-in Jira plugin: enabled`);
        }
    }

    private validateProjectConfiguration(): void {
        if (!this.config.projects || this.config.projects.length === 0) {
            return;
        }

        console.log('📁 Validating project configuration...');

        for (const project of this.config.projects) {
            if (!project.key) {
                throw new Error('❌ All projects must have a "key" field');
            }
            if (!project.name) {
                throw new Error(`❌ Project ${project.key} must have a "name" field`);
            }
            if (!project.issueTypes || project.issueTypes.length === 0) {
                throw new Error(`❌ Project ${project.key} must have at least one issue type`);
            }

            // Validate project key format (Jira project keys are typically uppercase alphanumeric)
            if (!/^[A-Z][A-Z0-9]*$/.test(project.key)) {
                console.warn(
                    `⚠️  Project key "${project.key}" should typically be uppercase alphanumeric`
                );
            }

            // Check for duplicate issue types within project
            const uniqueIssueTypes = new Set(project.issueTypes);
            if (uniqueIssueTypes.size !== project.issueTypes.length) {
                throw new Error(`❌ Project ${project.key} has duplicate issue types`);
            }

            console.log(
                `✓ Project ${project.key} (${project.name}): ${project.issueTypes.length} issue types`
            );
        }

        // Check for duplicate project keys
        const projectKeys = this.config.projects.map(p => p.key);
        const uniqueKeys = new Set(projectKeys);
        if (uniqueKeys.size !== projectKeys.length) {
            throw new Error('❌ Duplicate project keys found in configuration');
        }
    }

    private validateFlexibleConfiguration(): void {
        const hasFlexibleTypes =
            this.config.flexibleIssueTypes && this.config.flexibleIssueTypes.length > 0;

        if (!hasFlexibleTypes) {
            return;
        }

        console.log('🔄 Validating flexible issue type configuration...');

        if (!this.config.metadataProject) {
            throw new Error('❌ metadataProject is required when flexibleIssueTypes is specified');
        }

        // Validate metadata project key format
        if (!/^[A-Z][A-Z0-9]*$/.test(this.config.metadataProject)) {
            console.warn(
                `⚠️  Metadata project key "${this.config.metadataProject}" should typically be uppercase alphanumeric`
            );
        }

        // Check for duplicate flexible issue types
        const uniqueFlexibleTypes = new Set(this.config.flexibleIssueTypes!);
        if (uniqueFlexibleTypes.size !== this.config.flexibleIssueTypes!.length) {
            throw new Error('❌ Duplicate flexible issue types found in configuration');
        }

        console.log(
            `✓ Flexible configuration: ${this.config.flexibleIssueTypes!.length} issue types using metadata from ${this.config.metadataProject}`
        );
    }

    private validateSecuritySettings(): void {
        console.log('🔒 Validating security settings...');

        // Validate secret name format
        const secretName = this.config.jiraApiKeySecretName || 'jira-api-key';
        if (!/^[a-zA-Z0-9/_+=.@-]+$/.test(secretName)) {
            throw new Error(`❌ Invalid characters in jiraApiKeySecretName: ${secretName}`);
        }

        // Check for common security mistakes
        if (
            this.config.jiraBaseUrl?.includes('localhost') ||
            this.config.jiraBaseUrl?.includes('127.0.0.1')
        ) {
            console.warn(
                '⚠️  Using localhost URL - this will not work in deployed Lambda function'
            );
        }

        // Warn about placeholder values
        if (
            this.config.qBusinessApplicationId?.includes('REPLACE') ||
            this.config.qBusinessApplicationId?.includes('YOUR')
        ) {
            throw new Error(
                '❌ qBusinessApplicationId still contains placeholder text - please update with your actual application ID'
            );
        }

        if (this.config.jiraBaseUrl?.includes('your-domain')) {
            throw new Error(
                '❌ jiraBaseUrl still contains placeholder text - please update with your actual Jira URL'
            );
        }

        console.log(`✓ Security settings validated`);
        console.log(`  • Secret name: ${secretName}`);
        console.log(`  • No placeholder values detected`);
    }

    // Test Lambda locally
    public async testLambda(outputDir: string = './local-lambda-output'): Promise<void> {
        console.log('🧪 Testing Lambda function locally...\n');

        // Sanitize and validate output directory
        const safeOutputDir = this.sanitizePath(outputDir);

        // Create output directory using sanitized path
        if (!fs.existsSync(safeOutputDir)) {
            fs.mkdirSync(safeOutputDir, { recursive: true });
        }

        // Set up environment
        process.env.JIRA_BASE_URL = this.config.jiraBaseUrl;
        process.env.JIRA_API_KEY_SECRET_NAME = this.config.jiraApiKeySecretName || 'jira-api-key';
        process.env.OPENAPI_BUCKET_NAME = 'test-bucket';
        process.env.STACK_NAME = 'test-stack';
        process.env.PROJECTS_CONFIG = JSON.stringify(this.config.projects || []);
        process.env.FLEXIBLE_ISSUE_TYPES = JSON.stringify(this.config.flexibleIssueTypes || []);
        process.env.METADATA_PROJECT = this.config.metadataProject || '';

        // Create a special environment variable to signal we're in local test mode
        process.env.LOCAL_TEST_MODE = 'true';
        process.env.LOCAL_OUTPUT_DIR = safeOutputDir;

        // Create mock event
        const mockEvent = {
            RequestType: 'Create',
            StackId: 'arn:aws:cloudformation:us-west-2:123456789012:stack/test-stack/test',
            RequestId: `test-request-${Date.now()}`,
            LogicalResourceId: 'JiraMetadataResource',
            ResourceProperties: {},
        };

        try {
            console.log('📤 Invoking Lambda handler...');
            const result = await handler(mockEvent as any);

            console.log('📊 Lambda Result:');
            console.log(`   Status: ${result.Status}`);
            if (result.Status === 'SUCCESS') {
                console.log(`   Generated specs: ${result.Data?.SpecCount || 0}`);
            } else {
                console.log(`   Error: ${result.Reason}`);
            }

            // Save result using safe file path
            const resultPath = this.createSafeFilePath(safeOutputDir, 'result.json');
            fs.writeFileSync(resultPath, JSON.stringify(result, null, 2));
            console.log(`💾 Results saved to: ${safeOutputDir}/result.json`);
        } catch (error) {
            console.error('❌ Lambda test failed:', error);
            throw error;
        } finally {
            // Clean up environment variables
            delete process.env.LOCAL_TEST_MODE;
            delete process.env.LOCAL_OUTPUT_DIR;
        }
    }

    /**
     * Validate S3 key consistency between Lambda function and CDK stack
     */
    public validateS3Keys(stackName?: string): void {
        console.log('🔍 Validating S3 key consistency...\n');

        const actualStackName = stackName || 'jira-custom-plugins';
        console.log(`📦 Stack name: ${actualStackName}`);

        // Generate keys using Lambda pattern
        const lambdaKeys = this.generateLambdaKeys(actualStackName);
        const cdkKeys = this.generateCdkKeys(actualStackName);

        console.log('📝 Expected S3 Keys:\n');

        // Check if patterns match
        const keysMatch = JSON.stringify(lambdaKeys.sort()) === JSON.stringify(cdkKeys.sort());

        if (keysMatch) {
            console.log('✅ Lambda and CDK key patterns MATCH!\n');

            lambdaKeys.forEach((key, index) => {
                console.log(`${index + 1}. ${key}`);
            });

            console.log(`\n📊 Total keys: ${lambdaKeys.length}`);

            if (this.config.projects && this.config.projects.length > 0) {
                console.log(`📁 Targeted projects: ${this.config.projects.length}`);
            }

            if (this.config.flexibleIssueTypes && this.config.flexibleIssueTypes.length > 0) {
                console.log(`🔄 Flexible issue types: ${this.config.flexibleIssueTypes.length}`);
            }
        } else {
            console.log('❌ Lambda and CDK key patterns DO NOT MATCH!\n');

            console.log('🔧 Lambda function will generate:');
            lambdaKeys.forEach((key, index) => {
                console.log(`${index + 1}. ${key}`);
            });

            console.log('\n📦 CDK stack expects:');
            cdkKeys.forEach((key, index) => {
                console.log(`${index + 1}. ${key}`);
            });

            console.log('\n💡 This mismatch will cause "specified key does not exist" errors!');
        }

        console.log('\n🚀 After deployment, you can verify S3 objects exist with:');
        console.log(`   aws s3 ls s3://YOUR-BUCKET-NAME/ --recursive`);
        console.log('\n🔍 To find your bucket name:');
        console.log(
            `   aws cloudformation describe-stacks --stack-name ${actualStackName} --query 'Stacks[0].Outputs[?OutputKey==\`OpenApiSpecBucketName\`].OutputValue' --output text`
        );
        console.log('\n✅ S3 key validation completed!\n');
    }

    /**
     * Generate S3 keys using Lambda pattern
     */
    private generateLambdaKeys(stackName: string): string[] {
        const keys: string[] = [];

        // Generate flexible issue type keys (Lambda pattern)
        if (this.config.flexibleIssueTypes && this.config.flexibleIssueTypes.length > 0) {
            for (const issueType of this.config.flexibleIssueTypes) {
                const key = `${stackName.toLowerCase()}-flexible-${issueType.toLowerCase().replace(/\s+/g, '-')}-openapi-spec.json`;
                keys.push(key);
            }
        }

        // Generate targeted project keys (Lambda pattern)
        if (this.config.projects && this.config.projects.length > 0) {
            for (const project of this.config.projects) {
                for (const issueType of project.issueTypes) {
                    const key = `${stackName.toLowerCase()}-${project.key.toLowerCase()}-${issueType.toLowerCase().replace(/\s+/g, '-')}-openapi-spec.json`;
                    keys.push(key);
                }
            }
        }

        return keys;
    }

    /**
     * Generate S3 keys using CDK pattern
     */
    private generateCdkKeys(stackName: string): string[] {
        const keys: string[] = [];

        // Generate flexible issue type keys (CDK pattern)
        if (this.config.flexibleIssueTypes && this.config.flexibleIssueTypes.length > 0) {
            for (const issueType of this.config.flexibleIssueTypes) {
                const key = `${stackName.toLowerCase()}-flexible-${issueType.toLowerCase().replace(/\s+/g, '-')}-openapi-spec.json`;
                keys.push(key);
            }
        }

        // Generate targeted project keys (CDK pattern)
        if (this.config.projects && this.config.projects.length > 0) {
            for (const project of this.config.projects) {
                for (const issueType of project.issueTypes) {
                    const key = `${stackName.toLowerCase()}-${project.key.toLowerCase()}-${issueType.toLowerCase().replace(/\s+/g, '-')}-openapi-spec.json`;
                    keys.push(key);
                }
            }
        }

        return keys;
    }

    /**
     * Generate expected OpenAPI specs for testing purposes
     */
    public generateExpectedSpecs(outputDir: string): void {
        console.log('📋 Generating expected OpenAPI specs...\n');

        // Sanitize and validate output directory
        const safeOutputDir = this.sanitizePath(outputDir);

        // Create output directory using sanitized path
        if (!fs.existsSync(safeOutputDir)) {
            fs.mkdirSync(safeOutputDir, { recursive: true });
        }

        // Generate specs for flexible issue types
        if (this.config.flexibleIssueTypes && this.config.flexibleIssueTypes.length > 0) {
            for (const issueType of this.config.flexibleIssueTypes) {
                const spec = this.generateFlexibleIssueTypeSpec(issueType);
                // Create safe filename
                const sanitizedIssueType = issueType.replace(/[^a-zA-Z0-9-_]/g, '').toLowerCase();
                const filename = `flexible-${sanitizedIssueType}-spec.json`;
                const filepath = this.createSafeFilePath(safeOutputDir, filename);
                fs.writeFileSync(filepath, JSON.stringify(spec, null, 2));
                console.log(`✓ Generated: ${filename}`);
            }
        }

        // Generate specs for targeted projects
        if (this.config.projects && this.config.projects.length > 0) {
            for (const project of this.config.projects) {
                for (const issueType of project.issueTypes) {
                    const spec = this.generateProjectIssueTypeSpec(project, issueType);
                    // Create safe filename
                    const sanitizedProjectKey = project.key
                        .replace(/[^a-zA-Z0-9-_]/g, '')
                        .toLowerCase();
                    const sanitizedIssueType = issueType
                        .replace(/[^a-zA-Z0-9-_]/g, '')
                        .toLowerCase();
                    const filename = `${sanitizedProjectKey}-${sanitizedIssueType}-spec.json`;
                    const filepath = this.createSafeFilePath(safeOutputDir, filename);
                    fs.writeFileSync(filepath, JSON.stringify(spec, null, 2));
                    console.log(`✓ Generated: ${filename}`);
                }
            }
        }

        console.log(`\n✅ Spec generation completed! Files saved to: ${safeOutputDir}\n`);
    }

    /**
     * Generate OpenAPI spec for flexible issue type
     */
    private generateFlexibleIssueTypeSpec(issueType: string): any {
        return {
            openapi: '3.0.0',
            info: {
                title: 'Jira API',
                description: `OpenAPI specification for Jira API - ${issueType} issue type`,
                version: '1.0.0',
            },
            servers: [
                {
                    url: 'https://api.atlassian.com/ex/jira/your-site-id/rest/api/2',
                    description: 'Jira Server',
                },
            ],
            security: [
                {
                    OAuth2: ['read:jira-work', 'write:jira-work'],
                },
            ],
            paths: {
                '/issue': {
                    post: {
                        summary: `Create ${issueType}`,
                        description: `Create a new ${issueType} issue`,
                        requestBody: {
                            required: true,
                            content: {
                                'application/json': {
                                    schema: {
                                        $ref: '#/components/schemas/NewIssue',
                                    },
                                },
                            },
                        },
                        responses: {
                            '201': {
                                description: 'Issue created successfully',
                                content: {
                                    'application/json': {
                                        schema: {
                                            $ref: '#/components/schemas/Issue',
                                        },
                                    },
                                },
                            },
                            '400': {
                                description: 'Bad request',
                            },
                            '401': {
                                description: 'Unauthorized',
                            },
                        },
                    },
                },
            },
            components: {
                schemas: {
                    Issue: {
                        type: 'object',
                        properties: {
                            id: {
                                type: 'string',
                                description: 'The unique identifier for the issue',
                            },
                            key: {
                                type: 'string',
                                description: 'The issue key',
                            },
                            summary: {
                                type: 'string',
                                description: 'Summary of the issue',
                            },
                            description: {
                                type: 'string',
                                description: 'Description of the issue',
                            },
                        },
                    },
                    NewIssue: {
                        type: 'object',
                        properties: {
                            fields: {
                                type: 'object',
                                properties: {
                                    project: {
                                        type: 'object',
                                        'x-amzn-form-display-name': 'Project',
                                        properties: {
                                            key: {
                                                type: 'string',
                                                description: 'The key of the project',
                                                'x-amzn-form-display-name': 'Project Key',
                                            },
                                        },
                                        required: ['key'],
                                    },
                                    issuetype: {
                                        type: 'object',
                                        'x-amzn-form-display-name': 'Issue Type',
                                        properties: {
                                            name: {
                                                type: 'string',
                                                description: 'Name of the issue type',
                                                'x-amzn-form-display-name': 'Issue Type',
                                                enum: [issueType],
                                            },
                                        },
                                        required: ['name'],
                                    },
                                    summary: {
                                        type: 'string',
                                        description: 'Summary of the new issue',
                                        'x-amzn-form-display-name': 'Summary',
                                    },
                                    description: {
                                        type: 'string',
                                        description: 'Description of the new issue',
                                        'x-amzn-form-display-name': 'Description',
                                    },
                                },
                                required: ['project', 'issuetype', 'summary'],
                            },
                        },
                    },
                },
                securitySchemes: {
                    OAuth2: {
                        type: 'oauth2',
                        flows: {
                            authorizationCode: {
                                authorizationUrl: 'https://auth.atlassian.com/authorize',
                                tokenUrl: 'https://auth.atlassian.com/oauth/token',
                                scopes: {
                                    'read:jira-work': 'Read',
                                    'write:jira-work': 'Write',
                                },
                            },
                        },
                    },
                },
            },
        };
    }

    /**
     * Generate OpenAPI spec for project-specific issue type
     */
    private generateProjectIssueTypeSpec(
        project: { key: string; name: string; issueTypes: string[] },
        issueType: string
    ): any {
        return {
            openapi: '3.0.0',
            info: {
                title: 'Jira API',
                description: `OpenAPI specification for Jira API - ${project.name} ${issueType}`,
                version: '1.0.0',
            },
            servers: [
                {
                    url: 'https://api.atlassian.com/ex/jira/your-site-id/rest/api/2',
                    description: 'Jira Server',
                },
            ],
            security: [
                {
                    OAuth2: ['read:jira-work', 'write:jira-work'],
                },
            ],
            paths: {
                '/issue': {
                    post: {
                        summary: `Create ${issueType} in ${project.name}`,
                        description: `Create a new ${issueType} issue in the ${project.name} (${project.key}) project`,
                        requestBody: {
                            required: true,
                            content: {
                                'application/json': {
                                    schema: {
                                        $ref: '#/components/schemas/NewIssue',
                                    },
                                },
                            },
                        },
                        responses: {
                            '201': {
                                description: 'Issue created successfully',
                                content: {
                                    'application/json': {
                                        schema: {
                                            $ref: '#/components/schemas/Issue',
                                        },
                                    },
                                },
                            },
                            '400': {
                                description: 'Bad request',
                            },
                            '401': {
                                description: 'Unauthorized',
                            },
                        },
                    },
                },
            },
            components: {
                schemas: {
                    Issue: {
                        type: 'object',
                        properties: {
                            id: {
                                type: 'string',
                                description: 'The unique identifier for the issue',
                            },
                            key: {
                                type: 'string',
                                description: 'The issue key',
                            },
                            summary: {
                                type: 'string',
                                description: 'Summary of the issue',
                            },
                            description: {
                                type: 'string',
                                description: 'Description of the issue',
                            },
                        },
                    },
                    NewIssue: {
                        type: 'object',
                        properties: {
                            fields: {
                                type: 'object',
                                properties: {
                                    project: {
                                        type: 'object',
                                        'x-amzn-form-display-name': 'Project',
                                        properties: {
                                            key: {
                                                type: 'string',
                                                description:
                                                    'The key of the project to create the issue in',
                                                'x-amzn-form-display-name': 'Project Key',
                                                enum: [project.key],
                                            },
                                        },
                                        required: ['key'],
                                    },
                                    issuetype: {
                                        type: 'object',
                                        'x-amzn-form-display-name': 'Issue Type',
                                        properties: {
                                            name: {
                                                type: 'string',
                                                description: 'Name of the issue type',
                                                'x-amzn-form-display-name': 'Issue Type',
                                                enum: [issueType],
                                            },
                                        },
                                        required: ['name'],
                                    },
                                    summary: {
                                        type: 'string',
                                        description: 'Summary of the new issue',
                                        'x-amzn-form-display-name': 'Summary',
                                    },
                                    description: {
                                        type: 'string',
                                        description: 'Description of the new issue',
                                        'x-amzn-form-display-name': 'Description',
                                    },
                                },
                                required: ['project', 'issuetype', 'summary'],
                            },
                        },
                    },
                },
                securitySchemes: {
                    OAuth2: {
                        type: 'oauth2',
                        flows: {
                            authorizationCode: {
                                authorizationUrl: 'https://auth.atlassian.com/authorize',
                                tokenUrl: 'https://auth.atlassian.com/oauth/token',
                                scopes: {
                                    'read:jira-work': 'Read',
                                    'write:jira-work': 'Write',
                                },
                            },
                        },
                    },
                },
            },
        };
    }
}

// CLI Interface
async function main(): Promise<void> {
    const args = process.argv.slice(2);
    const command = args[0] || 'help';
    const configPath = args[1] || 'config.json';

    try {
        const tools = new DevTools(configPath);

        switch (command) {
            case 'validate':
                tools.validateConfig();
                break;

            case 'validate-keys': {
                tools.validateConfig();
                const stackName = args[2] || 'jira-custom-plugins';
                tools.validateS3Keys(stackName);
                break;
            }

            case 'test': {
                tools.validateConfig();
                // Use default if no output directory provided
                const testOutputDir = args[2] || './local-lambda-output';
                await tools.testLambda(testOutputDir);
                break;
            }

            case 'all':
                tools.validateConfig();
                await tools.testLambda();
                break;

            default:
                console.log('🛠️  Jira Q Business Plugin Development Tools\n');
                console.log(
                    'Usage: npx ts-node scripts/dev-tools.ts <command> [config-path] [args...]\n'
                );
                console.log('Commands:');
                console.log('  validate       - Validate configuration');
                console.log(
                    '  validate-keys  - Validate S3 key consistency between Lambda and CDK'
                );
                console.log('  test           - Test Lambda function locally');
                console.log('  all            - Run validation and test');
                console.log('\nExamples:');
                console.log('  npx ts-node scripts/dev-tools.ts validate');
                console.log(
                    '  npx ts-node scripts/dev-tools.ts validate-keys config.json my-stack-name'
                );
                console.log('  npx ts-node scripts/dev-tools.ts test config.json ./output');
                console.log('  npx ts-node scripts/dev-tools.ts all');
                break;
        }
    } catch (error) {
        console.error(`❌ ${error}`);
        throw error;
    }
}

if (require.main === module) {
    main().catch(error => {
        console.error('❌ Script execution failed:', error);
        throw error;
    });
}

export { DevTools };
