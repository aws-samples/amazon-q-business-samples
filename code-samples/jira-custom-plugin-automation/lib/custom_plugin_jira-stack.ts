import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as qbusiness from 'aws-cdk-lib/aws-qbusiness';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';

import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import * as crypto from 'crypto';

export interface JiraProject {
    key: string;
    name: string;
    issueTypes: string[];
}

export interface CustomPluginJiraStackProps extends cdk.StackProps {
    jiraBaseUrl?: string;
    atlassianSiteId?: string;
    jiraApiKeySecretName?: string;
    qBusinessApplicationId: string; // Required - must be an existing Q Business application
    projects?: JiraProject[];
    flexibleIssueTypes?: string[];
    metadataProject?: string;
    enableBuiltInJiraPlugin?: boolean;
    enableQBusinessIndex?: boolean; // Controls whether to create a Q Business index and retriever
    pluginVersion?: string; // Increment this to force plugin updates
}

export class CustomPluginJiraStack extends cdk.Stack {
    public readonly qBusinessApplicationId: string;
    public readonly customPlugins: qbusiness.CfnPlugin[];
    public readonly openApiSpecBucket: s3.Bucket;

    public readonly qBusinessIndex?: qbusiness.CfnIndex;
    public readonly qBusinessRetriever?: qbusiness.CfnRetriever;

    constructor(scope: Construct, id: string, props: CustomPluginJiraStackProps) {
        super(scope, id, props);

        // Generate a unique, safe bucket name for this stack
        const stackHash = crypto
            .createHash('sha256')
            .update(`${this.stackName}-${this.account}-${this.region}`)
            .digest('hex')
            .substring(0, 8);

        const safeBucketName = `qbusiness-jira-openapi-${stackHash}-${this.account}-${this.region}`;

        // S3 bucket to store the dynamically generated OpenAPI spec (unique per stack)
        this.openApiSpecBucket = new s3.Bucket(this, 'OpenApiSpecBucket', {
            bucketName: safeBucketName,
            versioned: true,
            encryption: s3.BucketEncryption.S3_MANAGED,
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
            removalPolicy: cdk.RemovalPolicy.DESTROY,
            autoDeleteObjects: true,
        });

        // Secret for Jira API key (used by custom resource for metadata collection)
        const jiraApiKeySecret = secretsmanager.Secret.fromSecretNameV2(
            this,
            'JiraApiKeySecret',
            props?.jiraApiKeySecretName || `jira-api-key-${this.stackName.toLowerCase()}`
        );

        // OAuth secret for custom plugins (managed by CDK, user updates values)
        const jiraOAuthSecret = new secretsmanager.Secret(this, 'JiraOAuthSecret', {
            secretName: `jira-oauth-${this.stackName.toLowerCase()}`,
            description: 'Jira OAuth credentials for Q Business custom plugins',
            generateSecretString: {
                secretStringTemplate: JSON.stringify({
                    client_id: 'temporary-client-id-replace-after-deployment',
                    client_secret: 'temporary-client-secret-replace-after-deployment',
                    redirect_uri: 'https://example.com/oauth/callback',
                }),
                generateStringKey: 'placeholder',
                excludeCharacters: '"@/\\',
            },
        });

        // Validate and extract configuration
        this.validateConfiguration(props);
        const { projects = [], flexibleIssueTypes = [], metadataProject } = props || {};

        // Lambda function to query Jira and generate OpenAPI specs
        const jiraMetadataFunction = new NodejsFunction(this, 'JiraMetadataFunction', {
            runtime: lambda.Runtime.NODEJS_20_X,
            handler: 'handler',
            entry: 'lambda/jira-metadata-handler.ts',
            timeout: cdk.Duration.minutes(5),
            memorySize: 512,
            environment: {
                JIRA_BASE_URL: props?.jiraBaseUrl || '',
                ATLASSIAN_SITE_ID: props?.atlassianSiteId || '',
                JIRA_API_KEY_SECRET_NAME: jiraApiKeySecret.secretName,
                OPENAPI_BUCKET_NAME: this.openApiSpecBucket.bucketName,
                PROJECTS_CONFIG: JSON.stringify(projects),
                FLEXIBLE_ISSUE_TYPES: JSON.stringify(flexibleIssueTypes || []),
                METADATA_PROJECT: metadataProject || 'none',
                STACK_NAME: this.stackName,
            },
            bundling: {
                externalModules: ['@aws-sdk/*'],
                forceDockerBundling: false,
            },
        });

        // Grant permissions to the Lambda function
        jiraApiKeySecret.grantRead(jiraMetadataFunction);
        this.openApiSpecBucket.grantReadWrite(jiraMetadataFunction);

        // Note: Custom resource provider handles Lambda permissions automatically

        // Create a hash of the configuration to detect changes
        const configHash = crypto
            .createHash('sha256')
            .update(
                JSON.stringify({
                    jiraBaseUrl: props?.jiraBaseUrl || '',
                    projects,
                    flexibleIssueTypes,
                    metadataProject,
                    stackName: this.stackName, // Include stack name in hash
                    // Include timestamp to force update on every deployment
                    timestamp: Date.now(),
                })
            )
            .digest('hex');

        const jiraMetadataCustomResource = new cdk.CustomResource(
            this,
            'JiraMetadataCustomResource',
            {
                serviceToken: jiraMetadataFunction.functionArn, // Direct Lambda ARN instead of Provider
                properties: {
                    JiraBaseUrl: props?.jiraBaseUrl || '',
                    ProjectsConfig: JSON.stringify(projects),
                    FlexibleIssueTypes: JSON.stringify(flexibleIssueTypes || []),
                    MetadataProject: metadataProject || 'none',
                    StackName: this.stackName, // Include stack name for S3 key generation
                    ConfigurationHash: configHash, // This will change on every deployment
                    Timestamp: Date.now(), // Additional timestamp for logging
                    Version: props?.pluginVersion || '1.0.0', // Use configurable version
                },
            }
        );

        // Grant CloudFormation permission to invoke the Lambda directly
        jiraMetadataFunction.addPermission('AllowCloudFormationInvoke', {
            principal: new iam.ServicePrincipal('cloudformation.amazonaws.com'),
            action: 'lambda:InvokeFunction',
        });

        // Ensure custom resource depends on S3 bucket being ready
        jiraMetadataCustomResource.node.addDependency(this.openApiSpecBucket);

        // Use existing Q Business application
        this.qBusinessApplicationId = props.qBusinessApplicationId;

        // Create Q Business index and retriever if enabled
        if (props?.enableQBusinessIndex) {
            // Create the index
            this.qBusinessIndex = new qbusiness.CfnIndex(this, 'JiraIndex', {
                applicationId: this.qBusinessApplicationId,
                displayName: `${this.stackName}-jira-index`,
                description: 'Index for Jira data created by the custom plugin automation',
            });

            // Create the retriever that uses the index
            this.qBusinessRetriever = new qbusiness.CfnRetriever(this, 'JiraRetriever', {
                applicationId: this.qBusinessApplicationId,
                displayName: `${this.stackName}-jira-retriever`,
                type: 'NATIVE_INDEX',
                configuration: {
                    nativeIndexConfiguration: {
                        indexId: this.qBusinessIndex.attrIndexId,
                    },
                },
            });

            // Ensure the retriever depends on the index
            this.qBusinessRetriever.addDependency(this.qBusinessIndex);
        }

        // Create custom plugins for both flexible and targeted types
        this.customPlugins = [];
        const pluginExecutionRole = this.createPluginExecutionRole();

        // Grant OAuth secret access to the plugin execution role and get the policy
        const oauthSecretPolicy = this.grantOAuthSecretAccess(pluginExecutionRole, jiraOAuthSecret);

        // Create flexible plugins
        if (flexibleIssueTypes.length > 0) {
            for (const issueType of flexibleIssueTypes) {
                const plugin = this.createFlexiblePlugin(
                    issueType,
                    pluginExecutionRole,
                    jiraOAuthSecret,
                    jiraMetadataCustomResource
                );
                this.customPlugins.push(plugin);
            }
        }

        // Create targeted plugins (existing logic)
        if (projects.length > 0) {
            for (const project of projects) {
                for (const issueType of project.issueTypes) {
                    const plugin = this.createTargetedPlugin(
                        project,
                        issueType,
                        pluginExecutionRole,
                        jiraOAuthSecret,
                        jiraMetadataCustomResource
                    );
                    this.customPlugins.push(plugin);
                }
            }
        }

        // Create built-in Jira plugin if enabled
        let builtInJiraPlugin: qbusiness.CfnPlugin | undefined;
        if (props?.enableBuiltInJiraPlugin) {
            builtInJiraPlugin = this.createBuiltInJiraPlugin(
                pluginExecutionRole,
                jiraOAuthSecret,
                props.jiraBaseUrl,
                oauthSecretPolicy
            );
        }

        // Outputs
        new cdk.CfnOutput(this, 'QBusinessApplicationId', {
            value: this.qBusinessApplicationId,
            description: 'Q Business Application ID (existing)',
        });

        // Output all plugin IDs
        let pluginIndex = 0;

        // Output flexible plugin IDs
        for (const issueType of flexibleIssueTypes) {
            const plugin = this.customPlugins[pluginIndex];
            new cdk.CfnOutput(this, `FlexiblePlugin${issueType.replace(/\s+/g, '')}Id`, {
                value: plugin.attrPluginId,
                description: `Plugin ID for flexible ${issueType} issue creation`,
            });
            pluginIndex++;
        }

        // Output targeted plugin IDs
        for (const project of projects) {
            for (const issueType of project.issueTypes) {
                const plugin = this.customPlugins[pluginIndex];
                new cdk.CfnOutput(
                    this,
                    `CustomPlugin${project.key}${issueType.replace(/\s+/g, '')}Id`,
                    {
                        value: plugin.attrPluginId,
                        description: `Plugin ID for ${issueType} in ${project.key}`,
                    }
                );
                pluginIndex++;
            }
        }

        // Output built-in plugin ID if created
        if (builtInJiraPlugin) {
            new cdk.CfnOutput(this, 'BuiltInJiraPluginId', {
                value: builtInJiraPlugin.attrPluginId,
                description: 'Built-in Jira plugin ID',
            });
        }

        const totalPlugins = this.customPlugins.length + (builtInJiraPlugin ? 1 : 0);
        new cdk.CfnOutput(this, 'TotalPluginsCreated', {
            value: totalPlugins.toString(),
            description: `Total plugins created: ${this.customPlugins.length} custom${builtInJiraPlugin ? ' + 1 built-in' : ''}`,
        });

        new cdk.CfnOutput(this, 'JiraOAuthSecretName', {
            value: jiraOAuthSecret.secretName,
            description:
                'OAuth secret name - update this in AWS Secrets Manager with your Jira OAuth credentials',
        });

        new cdk.CfnOutput(this, 'JiraOAuthSecretArn', {
            value: jiraOAuthSecret.secretArn,
            description: 'OAuth secret ARN',
        });

        new cdk.CfnOutput(this, 'OpenApiSpecBucketName', {
            value: this.openApiSpecBucket.bucketName,
            description: `S3 bucket for stack '${this.stackName}' containing the generated OpenAPI specs`,
        });

        new cdk.CfnOutput(this, 'OpenApiSpecBucketArn', {
            value: this.openApiSpecBucket.bucketArn,
            description: 'S3 bucket ARN for the OpenAPI specs',
        });

        // Output Q Business index and retriever IDs if created
        if (this.qBusinessIndex) {
            new cdk.CfnOutput(this, 'QBusinessIndexId', {
                value: this.qBusinessIndex.attrIndexId,
                description: 'Q Business Index ID created for Jira data',
            });
        }

        if (this.qBusinessRetriever) {
            new cdk.CfnOutput(this, 'QBusinessRetrieverId', {
                value: this.qBusinessRetriever.attrRetrieverId,
                description: 'Q Business Retriever ID created for the Jira index',
            });
        }
    }

    private createFlexiblePlugin(
        issueType: string,
        pluginExecutionRole: iam.Role,
        jiraOAuthSecret: secretsmanager.Secret,
        jiraMetadataCustomResource: cdk.CustomResource
    ): qbusiness.CfnPlugin {
        const pluginId = `Flexible${issueType.replace(/\s+/g, '')}Plugin`;
        const pluginName = `Jira-Create-${issueType.replace(/\s+/g, '-')}-Issue`;
        const pluginDescription = `Create ${issueType} issues in any Jira project`;
        const openApiKey = `${this.stackName.toLowerCase()}-flexible-${issueType.toLowerCase().replace(/\s+/g, '-')}-openapi-spec.json`;

        const customPlugin = new qbusiness.CfnPlugin(this, pluginId, {
            applicationId: this.qBusinessApplicationId,
            displayName: pluginName,
            type: 'CUSTOM',
            authConfiguration: {
                oAuth2ClientCredentialConfiguration: {
                    secretArn: jiraOAuthSecret.secretArn,
                    roleArn: pluginExecutionRole.roleArn,
                    authorizationUrl: 'https://auth.atlassian.com/authorize',
                    tokenUrl: 'https://auth.atlassian.com/oauth/token',
                },
            },
            customPluginConfiguration: {
                description: pluginDescription,
                apiSchema: {
                    s3: {
                        bucket: this.openApiSpecBucket.bucketName,
                        key: openApiKey,
                    },
                },
                apiSchemaType: 'OPEN_API_V3',
            },
        });

        // Ensure the custom resource completes before plugin creation
        customPlugin.node.addDependency(jiraMetadataCustomResource);

        return customPlugin;
    }

    private createTargetedPlugin(
        project: JiraProject,
        issueType: string,
        pluginExecutionRole: iam.Role,
        jiraOAuthSecret: secretsmanager.Secret,
        jiraMetadataCustomResource: cdk.CustomResource
    ): qbusiness.CfnPlugin {
        const pluginId = `${project.key}${issueType.replace(/\s+/g, '')}Plugin`;
        const pluginName = `Jira-Create-${issueType.replace(/\s+/g, '-')}-in-${project.key}-Project`;
        const pluginDescription = `Create ${issueType} issues in the ${project.name} (${project.key}) project`;
        const openApiKey = `${this.stackName.toLowerCase()}-${project.key.toLowerCase()}-${issueType.toLowerCase().replace(/\s+/g, '-')}-openapi-spec.json`;

        const customPlugin = new qbusiness.CfnPlugin(this, pluginId, {
            applicationId: this.qBusinessApplicationId,
            displayName: pluginName,
            type: 'CUSTOM',
            authConfiguration: {
                oAuth2ClientCredentialConfiguration: {
                    secretArn: jiraOAuthSecret.secretArn,
                    roleArn: pluginExecutionRole.roleArn,
                    authorizationUrl: 'https://auth.atlassian.com/authorize',
                    tokenUrl: 'https://auth.atlassian.com/oauth/token',
                },
            },
            customPluginConfiguration: {
                description: `${pluginDescription}`,
                apiSchema: {
                    s3: {
                        bucket: this.openApiSpecBucket.bucketName,
                        key: openApiKey,
                    },
                },
                apiSchemaType: 'OPEN_API_V3',
            },
        });

        // Ensure the custom resource completes before plugin creation
        customPlugin.node.addDependency(jiraMetadataCustomResource);

        return customPlugin;
    }

    private createBuiltInJiraPlugin(
        pluginExecutionRole: iam.Role,
        jiraOAuthSecret: secretsmanager.Secret,
        jiraBaseUrl?: string,
        oauthSecretPolicy?: iam.Policy
    ): qbusiness.CfnPlugin {
        const builtInPlugin = new qbusiness.CfnPlugin(this, 'BuiltInJiraPlugin', {
            applicationId: this.qBusinessApplicationId,
            displayName: `Jira-Built-In-Plugin`,
            type: 'JIRA_CLOUD',
            authConfiguration: {
                oAuth2ClientCredentialConfiguration: {
                    secretArn: jiraOAuthSecret.secretArn,
                    roleArn: pluginExecutionRole.roleArn,
                    authorizationUrl: 'https://auth.atlassian.com/authorize',
                    tokenUrl: 'https://auth.atlassian.com/oauth/token',
                },
            },
            serverUrl: jiraBaseUrl,
            state: 'ENABLED',
        });

        // Ensure IAM policy is ready before plugin creation
        if (oauthSecretPolicy) {
            builtInPlugin.node.addDependency(oauthSecretPolicy);
        }

        return builtInPlugin;
    }

    private createPluginExecutionRole(): iam.Role {
        const role = new iam.Role(this, 'PluginExecutionRole', {
            assumedBy: new iam.ServicePrincipal('qbusiness.amazonaws.com'),
            description: 'Execution role for Q Business custom plugin',
        });

        return role;
    }

    private grantOAuthSecretAccess(role: iam.Role, secret: secretsmanager.Secret): iam.Policy {
        // Grant specific access to the OAuth secret only
        const policy = new iam.Policy(this, 'OAuthSecretAccessPolicy', {
            statements: [
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: ['secretsmanager:GetSecretValue'],
                    resources: [secret.secretArn],
                }),
            ],
        });

        policy.attachToRole(role);
        return policy;
    }

    private validateConfiguration(props?: CustomPluginJiraStackProps): void {
        const projects = props?.projects || [];
        const flexibleIssueTypes = props?.flexibleIssueTypes || [];
        const metadataProject = props?.metadataProject;
        const enableBuiltInJiraPlugin = props?.enableBuiltInJiraPlugin || false;
        const enableQBusinessIndex = props?.enableQBusinessIndex || false;

        // Check that at least one plugin type is configured
        if (projects.length === 0 && flexibleIssueTypes.length === 0 && !enableBuiltInJiraPlugin) {
            throw new Error(
                'Either projects, flexibleIssueTypes, or enableBuiltInJiraPlugin must be configured'
            );
        }

        // Check that metadataProject is provided when flexibleIssueTypes is specified
        if (flexibleIssueTypes.length > 0 && !metadataProject) {
            throw new Error('metadataProject is required when flexibleIssueTypes is specified');
        }

        // Check that jiraBaseUrl is provided when built-in plugin is enabled
        if (enableBuiltInJiraPlugin && !props?.jiraBaseUrl) {
            throw new Error('jiraBaseUrl is required when enableBuiltInJiraPlugin is enabled');
        }

        // Check that qBusinessApplicationId is provided when Q Business index is enabled
        if (enableQBusinessIndex && !props?.qBusinessApplicationId) {
            throw new Error(
                'qBusinessApplicationId is required when enableQBusinessIndex is enabled'
            );
        }
    }
}
