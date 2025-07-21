import * as cdk from 'aws-cdk-lib';
import { CustomPluginJiraStack } from '../lib/custom_plugin_jira-stack';

const app = new cdk.App();

import * as fs from 'fs';
import * as path from 'path';

function validateConfiguration(config: {
    jiraBaseUrl?: string;
    atlassianSiteId?: string;
    qBusinessApplicationId?: string;
    projects?: any[];
    flexibleIssueTypes?: string[];
    metadataProject?: string;
    enableBuiltInJiraPlugin?: boolean;
    enableQBusinessIndex?: boolean;
}): void {
    const projects = config.projects || [];
    const flexibleIssueTypes = config.flexibleIssueTypes || [];
    const enableBuiltInJiraPlugin = config.enableBuiltInJiraPlugin || false;

    // Check that at least one plugin type is configured
    if (projects.length === 0 && flexibleIssueTypes.length === 0 && !enableBuiltInJiraPlugin) {
        throw new Error(
            'Either projects, flexibleIssueTypes, or enableBuiltInJiraPlugin must be configured'
        );
    }

    // Validate required Jira base URL
    if (!config.jiraBaseUrl) {
        throw new Error('jiraBaseUrl is required in config.json');
    }

    // Validate required Atlassian site ID
    if (!config.atlassianSiteId) {
        throw new Error('atlassianSiteId is required in config.json');
    }

    // Validate required Q Business Application ID
    if (!config.qBusinessApplicationId) {
        throw new Error(
            'qBusinessApplicationId is required in config.json. Must specify an existing Q Business application.'
        );
    }

    // Check that metadataProject is provided when flexibleIssueTypes is specified
    if (flexibleIssueTypes.length > 0 && !config.metadataProject) {
        throw new Error('metadataProject is required when flexibleIssueTypes is specified');
    }

    // Validate projects array structure if provided
    if (projects.length > 0) {
        if (!Array.isArray(projects)) {
            throw new Error('Projects configuration must be an array');
        }

        for (const project of projects) {
            if (!project.key || !project.name || !Array.isArray(project.issueTypes)) {
                throw new Error('Each project must have key, name, and issueTypes array');
            }
        }
    }

    // Validate flexibleIssueTypes array structure if provided
    if (flexibleIssueTypes.length > 0) {
        if (!Array.isArray(flexibleIssueTypes)) {
            throw new Error('flexibleIssueTypes must be an array');
        }

        for (const issueType of flexibleIssueTypes) {
            if (typeof issueType !== 'string' || issueType.trim() === '') {
                throw new Error('Each flexible issue type must be a non-empty string');
            }
        }
    }
}

// Get stack name and config file from environment variables (set by deploy.sh)
const stackName = process.env.CDK_STACK_NAME || 'CustomPluginJiraStack';
const configFileName = process.env.CDK_CONFIG_FILE || 'config.json';

// Load configuration from specified config file
const configPath = path.join(__dirname, '..', configFileName);
if (!fs.existsSync(configPath)) {
    throw new Error(
        `${configFileName} not found. Please copy config.example.json to ${configFileName} and update with your settings.`
    );
}

let config: any;
try {
    const configContent = fs.readFileSync(configPath, 'utf8');

    // Validate JSON content before parsing
    if (!configContent.trim()) {
        throw new Error('Configuration file is empty');
    }

    config = JSON.parse(configContent);

    // Validate that config is an object
    if (!config || typeof config !== 'object' || Array.isArray(config)) {
        throw new Error('Configuration must be a JSON object');
    }
} catch (error) {
    throw new Error(`Failed to parse config.json: ${error}`);
}

console.log(`Loaded configuration from ${configFileName}`);

const {
    jiraBaseUrl,
    atlassianSiteId,
    jiraApiKeySecretName = 'jira-api-key',
    qBusinessApplicationId,
    pluginVersion = '1.0.0',
    projects,
    flexibleIssueTypes,
    metadataProject,
    enableBuiltInJiraPlugin,
    enableQBusinessIndex,
} = config;

// Validate configuration
validateConfiguration({
    jiraBaseUrl,
    atlassianSiteId,
    qBusinessApplicationId,
    projects,
    flexibleIssueTypes,
    metadataProject,
    enableBuiltInJiraPlugin,
    enableQBusinessIndex,
});

const projectCount = projects?.length || 0;
const targetedPluginCount =
    projects?.reduce((acc: number, p: any) => acc + p.issueTypes.length, 0) || 0;
const flexiblePluginCount = flexibleIssueTypes?.length || 0;
const builtInPluginCount = enableBuiltInJiraPlugin ? 1 : 0;
const totalPluginCount = targetedPluginCount + flexiblePluginCount + builtInPluginCount;

console.log(
    `Deploying stack '${stackName}' with ${projectCount} projects, ${flexiblePluginCount} flexible issue types${enableBuiltInJiraPlugin ? ', 1 built-in plugin' : ''}, and ${totalPluginCount} total plugins`
);

// Determine the region to use (prioritize environment variables set by deploy script)
const deployRegion =
    process.env.CDK_DEFAULT_REGION ||
    process.env.AWS_DEFAULT_REGION ||
    process.env.CDK_DEPLOY_REGION;
const deployAccount = process.env.CDK_DEFAULT_ACCOUNT || process.env.CDK_DEPLOY_ACCOUNT;

console.log(`Using AWS region: ${deployRegion || 'default'}`);
console.log(`Using AWS account: ${deployAccount || 'default'}`);

new CustomPluginJiraStack(app, stackName, {
    env: {
        account: deployAccount,
        region: deployRegion,
    },
    jiraBaseUrl,
    atlassianSiteId,
    jiraApiKeySecretName,
    qBusinessApplicationId,
    pluginVersion,
    projects,
    flexibleIssueTypes,
    metadataProject,
    enableBuiltInJiraPlugin,
    enableQBusinessIndex,
});
