import {
    CloudFormationCustomResourceEvent,
    CloudFormationCustomResourceResponse,
} from 'aws-lambda';
import { SecretsManagerClient, GetSecretValueCommand } from '@aws-sdk/client-secrets-manager';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import axios from 'axios';
import * as fs from 'fs';
import * as path from 'path';

// Removed unused JiraProject interface

interface JiraIssueType {
    id: string;
    name: string;
    description?: string;
    fields: Record<string, JiraField>;
}

interface JiraField {
    required: boolean;
    name: string;
    fieldId: string;
    schema: {
        type: string;
        system?: string;
        items?: string;
        custom?: string;
    };
    allowedValues?: Array<{
        id: string;
        name: string;
        value: string;
    }>;
}

const secretsManager = new SecretsManagerClient({});
const s3Client = new S3Client({});

// Function to send response to CloudFormation
async function sendResponseToCloudFormation(
    event: CloudFormationCustomResourceEvent,
    response: CloudFormationCustomResourceResponse
): Promise<void> {
    const responseBody = JSON.stringify(response);

    console.log('📤 Sending response to CloudFormation:', responseBody);

    // Skip sending response in local test mode
    if (process.env.LOCAL_TEST_MODE === 'true') {
        console.log('✅ Skipping CloudFormation response in local test mode');
        return;
    }

    try {
        const putResponse = await axios.put(event.ResponseURL, responseBody, {
            headers: {
                'Content-Type': '',
                'Content-Length': responseBody.length.toString(),
            },
        });

        console.log('✅ Successfully sent response to CloudFormation:', putResponse.status);
    } catch (error) {
        console.error('❌ Failed to send response to CloudFormation:', error);
        throw error;
    }
}

// Function to upload or write OpenAPI spec based on environment
async function uploadOrWriteSpec(
    bucketName: string,
    specKey: string,
    openApiSpec: any,
    description: string
): Promise<void> {
    console.log(`Processing ${description} spec: ${specKey}`);
    console.log(`Spec size: ${JSON.stringify(openApiSpec, null, 2).length} bytes`);

    // Check if we're in local test mode
    if (process.env.LOCAL_TEST_MODE === 'true' && process.env.LOCAL_OUTPUT_DIR) {
        // Write to local file instead of S3
        const localPath = path.join(process.env.LOCAL_OUTPUT_DIR, specKey);
        fs.writeFileSync(localPath, JSON.stringify(openApiSpec, null, 2));
        console.log(`✅ Wrote ${description} spec to local file: ${localPath}`);
    } else {
        // Normal S3 upload
        console.log(`Uploading ${description} spec to S3: ${bucketName}/${specKey}`);
        await s3Client.send(
            new PutObjectCommand({
                Bucket: bucketName,
                Key: specKey,
                Body: JSON.stringify(openApiSpec, null, 2),
                ContentType: 'application/json',
            })
        );
        console.log(`✅ Successfully uploaded ${description} spec to S3: ${bucketName}/${specKey}`);
    }
}

interface ProjectConfig {
    key: string;
    name: string;
    issueTypes: string[];
}

// Custom error classes for better error handling
class JiraAuthenticationError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'JiraAuthenticationError';
    }
}

class JiraApiError extends Error {
    constructor(
        message: string,
        public statusCode?: number
    ) {
        super(message);
        this.name = 'JiraApiError';
    }
}

class InsufficientDataError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'InsufficientDataError';
    }
}

export const handler = async (
    event: CloudFormationCustomResourceEvent
): Promise<CloudFormationCustomResourceResponse> => {
    console.log('Event:', JSON.stringify(event, null, 2));

    // Extract these early for error handling
    const { StackId, RequestId, LogicalResourceId } = event;

    // Add timeout protection to prevent silent failures
    const timeoutId = setTimeout(
        () => {
            console.error('❌ Lambda timeout approaching - this will cause CloudFormation to fail');
            throw new Error(
                'Lambda timeout - Jira API calls took too long. Check your API credentials and network connectivity.'
            );
        },
        4.5 * 60 * 1000
    ); // 4.5 minutes (before 5 minute timeout)

    // Ensure we always return a response, even in catastrophic failure
    process.on('uncaughtException', error => {
        console.error('❌ UNCAUGHT EXCEPTION:', error);
        clearTimeout(timeoutId);
        // Note: In a real scenario, you'd want to send the failure response to the ResponseURL
        // but since we can't return from here, CloudFormation will timeout and fail
    });

    process.on('unhandledRejection', (reason, promise) => {
        console.error('❌ UNHANDLED REJECTION at:', promise, 'reason:', reason);
        clearTimeout(timeoutId);
        // Note: In a real scenario, you'd want to send the failure response to the ResponseURL
    });

    // Extract environment variables outside try block for error handling
    const jiraBaseUrl = process.env.JIRA_BASE_URL;
    const secretName = process.env.JIRA_API_KEY_SECRET_NAME;
    const bucketName = process.env.OPENAPI_BUCKET_NAME;
    const projectsConfigStr = process.env.PROJECTS_CONFIG;
    const flexibleIssueTypesStr = process.env.FLEXIBLE_ISSUE_TYPES;
    const metadataProject = process.env.METADATA_PROJECT;
    const stackName = process.env.STACK_NAME;

    try {
        const { RequestType, StackId, RequestId, LogicalResourceId, ResourceProperties } = event;

        // Log deployment information for tracking
        console.log('Deployment Info:', {
            RequestType,
            Timestamp: ResourceProperties?.Timestamp,
            DeploymentId: ResourceProperties?.DeploymentId,
            JiraBaseUrl: ResourceProperties?.JiraBaseUrl,
        });

        if (RequestType === 'Delete') {
            const deleteResponse = {
                Status: 'SUCCESS' as const,
                PhysicalResourceId: 'jira-metadata-resource',
                StackId,
                RequestId,
                LogicalResourceId,
                Data: {},
            };

            console.log('🗑️ Delete request - sending SUCCESS response');
            await sendResponseToCloudFormation(event, deleteResponse);
            return deleteResponse;
        }

        if (!jiraBaseUrl || !secretName || !bucketName || !stackName) {
            throw new Error(
                'Missing required environment variables: JIRA_BASE_URL, JIRA_API_KEY_SECRET_NAME, OPENAPI_BUCKET_NAME, STACK_NAME'
            );
        }

        const projectsConfig: ProjectConfig[] = projectsConfigStr
            ? JSON.parse(projectsConfigStr)
            : [];
        const flexibleIssueTypes: string[] = flexibleIssueTypesStr
            ? JSON.parse(flexibleIssueTypesStr)
            : [];

        console.log('Projects configuration:', projectsConfig);
        console.log('Flexible issue types:', flexibleIssueTypes);
        console.log('Metadata project:', metadataProject);

        // Get Jira API credentials from Secrets Manager
        const secretResponse = await secretsManager.send(
            new GetSecretValueCommand({ SecretId: secretName })
        );

        const secretString = secretResponse.SecretString;
        if (!secretString) {
            throw new Error('Failed to retrieve Jira API credentials');
        }

        // Parse the secret - it must contain JSON with email and apiToken
        let secretData: { email: string; apiToken: string };
        try {
            secretData = JSON.parse(secretString);
        } catch (parseError) {
            throw new Error('Secret must be valid JSON format');
        }

        if (!secretData.email || !secretData.apiToken) {
            throw new Error('Secret must contain both "email" and "apiToken" fields');
        }

        // Create Basic Auth header (email:apiToken base64 encoded)
        const authString = Buffer.from(`${secretData.email}:${secretData.apiToken}`).toString(
            'base64'
        );
        const authHeaders = {
            Authorization: `Basic ${authString}`,
            Accept: 'application/json',
            'Content-Type': 'application/json',
        };

        // Validate configuration
        if (flexibleIssueTypes.length > 0 && !metadataProject) {
            throw new Error(
                'METADATA_PROJECT environment variable is required when FLEXIBLE_ISSUE_TYPES is specified'
            );
        }

        if (projectsConfig.length === 0 && flexibleIssueTypes.length === 0) {
            throw new Error('Either PROJECTS_CONFIG or FLEXIBLE_ISSUE_TYPES must be configured');
        }

        // Test authentication before proceeding
        console.log('🔐 Testing Jira authentication...');
        try {
            await testJiraAuthentication(jiraBaseUrl, authHeaders);
            console.log('✅ Jira authentication successful');
        } catch (authError) {
            console.error(
                '❌ Authentication test failed - this should cause CloudFormation to fail'
            );
            console.error('❌ Auth error details:', authError);
            throw authError; // Re-throw to trigger main catch block
        }

        // Get comprehensive field definitions from Jira
        console.log('Getting comprehensive field definitions from Jira...');
        const fieldDefinitions = await getJiraFieldDefinitions(jiraBaseUrl, authHeaders);

        // Query Jira for metadata with strict validation
        const issueTypesMetadata = await getConfiguredProjectsMetadata(
            jiraBaseUrl,
            authHeaders,
            projectsConfig,
            flexibleIssueTypes,
            metadataProject
        );

        // Validate we got sufficient data before generating specs
        validateMetadataCompleteness(
            issueTypesMetadata,
            projectsConfig,
            flexibleIssueTypes,
            metadataProject
        );

        // Generate separate OpenAPI specs
        const uploadedSpecs: string[] = [];

        // Generate specs for flexible issue types
        if (flexibleIssueTypes.length > 0 && metadataProject) {
            for (const issueType of flexibleIssueTypes) {
                const issueTypeMetadata = issueTypesMetadata[metadataProject]?.find(
                    it => it.name === issueType
                );

                // **CRITICAL FIX**: Fail if we don't have metadata for configured issue types
                if (!issueTypeMetadata) {
                    throw new InsufficientDataError(
                        `No metadata found for flexible issue type '${issueType}' in project '${metadataProject}'. This indicates an API failure or configuration issue.`
                    );
                }

                const openApiSpec = generateFlexibleIssueTypeOpenApiSpec(
                    issueType,
                    issueTypeMetadata,
                    fieldDefinitions
                );

                const specKey = `${stackName.toLowerCase()}-flexible-${issueType.toLowerCase().replace(/\s+/g, '-')}-openapi-spec.json`;

                await uploadOrWriteSpec(bucketName, specKey, openApiSpec, `flexible ${issueType}`);

                uploadedSpecs.push(specKey);
                console.log(
                    '✅ Successfully uploaded flexible OpenAPI spec for issue type:',
                    issueType,
                    'with key:',
                    specKey
                );
            }
        }

        // Generate specs for targeted project-issue type combinations
        for (const project of projectsConfig) {
            for (const issueType of project.issueTypes) {
                const issueTypeMetadata = issueTypesMetadata[project.key]?.find(
                    it => it.name === issueType
                );

                // **CRITICAL FIX**: Fail if we don't have metadata for configured issue types
                if (!issueTypeMetadata) {
                    throw new InsufficientDataError(
                        `No metadata found for issue type '${issueType}' in project '${project.key}'. This indicates an API failure or configuration issue.`
                    );
                }

                const openApiSpec = generateProjectIssueTypeOpenApiSpec(
                    project,
                    issueType,
                    issueTypeMetadata,
                    fieldDefinitions
                );

                const specKey = `${stackName.toLowerCase()}-${project.key.toLowerCase()}-${issueType.toLowerCase().replace(/\s+/g, '-')}-openapi-spec.json`;

                await uploadOrWriteSpec(
                    bucketName,
                    specKey,
                    openApiSpec,
                    `${project.key} ${issueType}`
                );

                uploadedSpecs.push(specKey);
                console.log(
                    '✅ Successfully uploaded targeted OpenAPI spec for project:',
                    project.key,
                    'issue type:',
                    issueType,
                    'with key:',
                    specKey
                );
            }
        }

        // Clear timeout since we succeeded
        clearTimeout(timeoutId);

        const successResponse = {
            Status: 'SUCCESS' as const,
            PhysicalResourceId: 'jira-metadata-resource',
            StackId,
            RequestId,
            LogicalResourceId,
            Data: {
                UploadedSpecs: uploadedSpecs.join(', '),
                SpecCount: uploadedSpecs.length,
                ProjectCount: projectsConfig.length,
                FlexibleIssueTypesCount: flexibleIssueTypes.length,
                MetadataProject: metadataProject || 'none',
            },
        };

        console.log('✅ Lambda execution successful, sending SUCCESS response to CloudFormation');
        await sendResponseToCloudFormation(event, successResponse);
        return successResponse;
    } catch (error) {
        // Clear timeout to prevent additional errors
        clearTimeout(timeoutId);

        console.error('❌ CRITICAL ERROR - Lambda execution failed:', error);
        console.error(
            '❌ Error type:',
            error instanceof Error ? error.constructor.name : typeof error
        );
        console.error(
            '❌ Stack trace:',
            error instanceof Error ? error.stack : 'No stack trace available'
        );

        // Provide more specific error messages
        let reason = 'Unknown error occurred during Jira metadata processing';
        if (error instanceof JiraAuthenticationError) {
            reason = `Jira authentication failed: ${error.message}. Please verify your API token is valid and not expired.`;
        } else if (error instanceof JiraApiError) {
            reason = `Jira API error: ${error.message}. Check your Jira instance URL and permissions.`;
        } else if (error instanceof InsufficientDataError) {
            reason = `Insufficient data retrieved: ${error.message}. This usually indicates API authentication or permission issues.`;
        } else if (error instanceof Error) {
            reason = `Lambda execution error: ${error.message}`;
        }

        const failedResponse = {
            Status: 'FAILED' as const,
            PhysicalResourceId: 'jira-metadata-resource',
            StackId,
            RequestId,
            LogicalResourceId,
            Reason: reason,
            Data: {
                ErrorType: error instanceof Error ? error.constructor.name : 'UnknownError',
                ErrorMessage: error instanceof Error ? error.message : String(error),
                Timestamp: new Date().toISOString(),
                FailureContext:
                    'Custom resource failed during Jira metadata collection and S3 object creation',
                JiraBaseUrl: jiraBaseUrl || 'not-configured',
                ConfiguredProjects: projectsConfigStr || '[]',
                ConfiguredFlexibleTypes: flexibleIssueTypesStr || '[]',
                MetadataProject: metadataProject || 'none',
                StackName: stackName || 'unknown',
                // These will be empty/zero on failure but provide context
                SpecCount: 0,
                ProjectCount: 0,
                FlexibleIssueTypesCount: 0,
                UploadedSpecs: 'none - custom resource failed',
            },
        };

        console.error('❌ Sending FAILED response to CloudFormation');
        console.error('❌ This should cause the CloudFormation deployment to FAIL');

        try {
            await sendResponseToCloudFormation(event, failedResponse);
            console.error('✅ Successfully sent FAILED response to CloudFormation');
        } catch (responseError) {
            console.error('❌ CRITICAL: Failed to send response to CloudFormation:', responseError);
            // CloudFormation will timeout if we can't send the response
        }

        return failedResponse;
    }
};

async function validateAndSanitizeFields(
    fields: Record<string, JiraField>,
    issueType: string,
    projectKey: string
): Promise<Record<string, JiraField>> {
    const sanitizedFields: Record<string, JiraField> = {};

    for (const [fieldId, field] of Object.entries(fields)) {
        try {
            // Skip system fields that are not user-editable
            if (isSystemOnlyField(fieldId)) {
                continue;
            }

            // Validate field schema
            if (!field.schema?.type) {
                console.warn(
                    'Field has invalid schema, skipping. Field ID:',
                    fieldId,
                    'Project:',
                    projectKey,
                    'Issue Type:',
                    issueType
                );
                continue;
            }

            // Sanitize field data
            sanitizedFields[fieldId] = {
                required: Boolean(field.required),
                name: field.name || fieldId,
                fieldId,
                schema: {
                    type: field.schema.type,
                    ...(field.schema.system && { system: field.schema.system }),
                    ...(field.schema.items && { items: field.schema.items }),
                    ...(field.schema.custom && { custom: field.schema.custom }),
                },
                ...(field.allowedValues && { allowedValues: field.allowedValues }),
            };
        } catch (error) {
            console.warn(`Error processing field ${fieldId} in ${projectKey}-${issueType}:`, error);
        }
    }

    return sanitizedFields;
}

function isSystemOnlyField(fieldId: string): boolean {
    const systemOnlyFields = [
        'created',
        'updated',
        'creator',
        'reporter',
        'status',
        'resolution',
        'resolutiondate',
        'worklog',
        'comment',
        'votes',
        'watches',
        'issuelinks',
        'subtasks',
        'attachment',
        'timetracking',
    ];
    return systemOnlyFields.includes(fieldId);
}

// Get comprehensive field definitions from Jira
async function getJiraFieldDefinitions(
    baseUrl: string,
    authHeaders: Record<string, string>
): Promise<Map<string, { name: string; custom: boolean; schema: any }>> {
    const fieldMap = new Map();

    try {
        console.log('Fetching all field definitions from /rest/api/3/field');
        const fieldsResponse = await retryWithBackoff(async () => {
            return await axios.get(`${baseUrl}/rest/api/3/field`, { headers: authHeaders });
        });

        const fields = fieldsResponse.data || [];
        console.log(`Retrieved ${fields.length} field definitions from Jira`);

        for (const field of fields) {
            fieldMap.set(field.id, {
                name: field.name,
                custom: field.custom || false,
                schema: field.schema || {},
            });
        }

        console.log('Processed field definitions. Count:', fieldMap.size);
    } catch (error: any) {
        if (error.response?.status === 401) {
            throw new JiraAuthenticationError(
                'Authentication failed while fetching field definitions'
            );
        } else {
            console.warn('Failed to fetch field definitions, will use fallback naming:', error);
        }
    }

    return fieldMap;
}

// Simplified field processing - removed complex compatibility checks

async function retryWithBackoff<T>(
    operation: () => Promise<T>,
    maxRetries: number = 3,
    baseDelay: number = 1000
): Promise<T> {
    let lastError: Error;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            return await operation();
        } catch (error) {
            lastError = error as Error;

            // Don't retry authentication errors
            if ((error as any).response?.status === 401) {
                throw error;
            }

            if (attempt === maxRetries) {
                throw lastError;
            }

            // Exponential backoff with jitter
            const delay = baseDelay * Math.pow(2, attempt) + Math.random() * 1000;
            console.log(`Attempt ${attempt + 1} failed, retrying in ${delay}ms:`, error);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }

    throw lastError!;
}

// Test authentication before proceeding
async function testJiraAuthentication(
    baseUrl: string,
    authHeaders: Record<string, string>
): Promise<void> {
    try {
        const response = await retryWithBackoff(async () => {
            return await axios.get(`${baseUrl}/rest/api/3/myself`, { headers: authHeaders });
        });

        console.log(
            `Authenticated as: ${response.data.displayName} (${response.data.emailAddress})`
        );
    } catch (error: any) {
        if (error.response?.status === 401) {
            throw new JiraAuthenticationError(
                'Invalid Jira credentials. Please check your API token and email address.'
            );
        } else if (error.response?.status === 403) {
            throw new JiraAuthenticationError(
                'Jira access forbidden. Please check your permissions.'
            );
        } else {
            throw new JiraApiError(
                `Failed to authenticate with Jira: ${error.message}`,
                error.response?.status
            );
        }
    }
}

// Validate metadata completeness
function validateMetadataCompleteness(
    metadata: Record<string, JiraIssueType[]>,
    projectsConfig: ProjectConfig[],
    flexibleIssueTypes: string[],
    metadataProject?: string
): void {
    console.log('🔍 Validating metadata completeness...');

    // Validate flexible issue types
    if (flexibleIssueTypes.length > 0 && metadataProject) {
        const metadataProjectData = metadata[metadataProject];
        if (!metadataProjectData || metadataProjectData.length === 0) {
            throw new InsufficientDataError(
                `No metadata retrieved for metadata project '${metadataProject}'. This indicates an API failure.`
            );
        }

        for (const issueType of flexibleIssueTypes) {
            const issueTypeData = metadataProjectData.find(it => it.name === issueType);
            if (!issueTypeData) {
                throw new InsufficientDataError(
                    `No metadata found for flexible issue type '${issueType}' in project '${metadataProject}'`
                );
            }

            const fieldCount = Object.keys(issueTypeData.fields).length;
            if (fieldCount < 3) {
                // Minimum expected fields: summary, description, project
                console.warn(
                    `⚠️  Very few fields (${fieldCount}) found for ${metadataProject}-${issueType}. This may indicate an API issue.`
                );
            }
        }
    }

    // Validate targeted projects
    for (const project of projectsConfig) {
        const projectData = metadata[project.key];
        if (!projectData || projectData.length === 0) {
            throw new InsufficientDataError(
                `No metadata retrieved for project '${project.key}'. This indicates an API failure.`
            );
        }

        for (const issueType of project.issueTypes) {
            const issueTypeData = projectData.find(it => it.name === issueType);
            if (!issueTypeData) {
                throw new InsufficientDataError(
                    `No metadata found for issue type '${issueType}' in project '${project.key}'`
                );
            }

            const fieldCount = Object.keys(issueTypeData.fields).length;
            if (fieldCount < 3) {
                // Minimum expected fields
                console.warn(
                    `⚠️  Very few fields (${fieldCount}) found for ${project.key}-${issueType}. This may indicate an API issue.`
                );
            }
        }
    }

    console.log('✅ Metadata completeness validation passed');
}

async function getConfiguredProjectsMetadata(
    baseUrl: string,
    authHeaders: Record<string, string>,
    projectsConfig: ProjectConfig[],
    flexibleIssueTypes: string[] = [],
    metadataProject?: string
): Promise<Record<string, JiraIssueType[]>> {
    const metadata: Record<string, JiraIssueType[]> = {};

    // Get metadata for the metadata project (used for flexible issue types)
    if (flexibleIssueTypes.length > 0 && metadataProject) {
        try {
            console.log(`Getting enhanced metadata for metadata project: ${metadataProject}`);

            // Get issue types for the metadata project with retry logic
            const issueTypesResponse = await retryWithBackoff(async () => {
                return await axios.get(
                    `${baseUrl}/rest/api/3/issue/createmeta/${metadataProject}/issuetypes`,
                    {
                        headers: authHeaders,
                    }
                );
            });

            const issueTypes: JiraIssueType[] = [];
            const availableIssueTypes = issueTypesResponse.data.issueTypes || [];

            // Get metadata for configured flexible issue types
            for (const configuredIssueType of flexibleIssueTypes) {
                const matchingIssueType = availableIssueTypes.find(
                    (it: any) => it.name.toLowerCase() === configuredIssueType.toLowerCase()
                );

                if (matchingIssueType) {
                    console.log(
                        'Getting enhanced fields for metadata project:',
                        metadataProject,
                        'issue type:',
                        configuredIssueType
                    );

                    // Get field details with retry logic
                    const fieldsResponse = await retryWithBackoff(async () => {
                        return await axios.get(
                            `${baseUrl}/rest/api/3/issue/createmeta/${metadataProject}/issuetypes/${matchingIssueType.id}`,
                            { headers: authHeaders }
                        );
                    });

                    const rawFields = fieldsResponse.data.fields || {};

                    // Validate we got fields
                    if (Object.keys(rawFields).length === 0) {
                        throw new InsufficientDataError(
                            `No fields returned for ${metadataProject}-${configuredIssueType}. This indicates an API failure or permission issue.`
                        );
                    }

                    // Validate and sanitize fields with comprehensive field definitions
                    const sanitizedFields = await validateAndSanitizeFields(
                        rawFields,
                        configuredIssueType,
                        metadataProject
                    );

                    console.log('Field analysis for issue type:', configuredIssueType, {
                        totalFields: Object.keys(sanitizedFields).length,
                        processedFields: Object.keys(sanitizedFields).length,
                    });

                    issueTypes.push({
                        id: matchingIssueType.id,
                        name: matchingIssueType.name,
                        description: matchingIssueType.description,
                        fields: sanitizedFields,
                    });
                } else {
                    throw new InsufficientDataError(
                        `Issue type '${configuredIssueType}' not found in metadata project '${metadataProject}'`
                    );
                }
            }

            metadata[metadataProject] = issueTypes;
        } catch (error: any) {
            if (error instanceof InsufficientDataError) {
                throw error; // Re-throw our custom errors
            }

            if (error.response?.status === 401) {
                throw new JiraAuthenticationError(
                    'Authentication failed while fetching metadata project'
                );
            } else if (error.response?.status === 403) {
                throw new JiraApiError(`Access forbidden to metadata project '${metadataProject}'`);
            } else if (error.response?.status === 404) {
                throw new JiraApiError(`Metadata project '${metadataProject}' not found`);
            } else {
                throw new JiraApiError(
                    `Failed to fetch metadata for project '${metadataProject}': ${error.message}`,
                    error.response?.status
                );
            }
        }
    }

    // Get metadata for targeted projects
    for (const projectConfig of projectsConfig) {
        try {
            console.log(`Getting enhanced metadata for project: ${projectConfig.key}`);

            // Get issue types for the specific project with retry logic
            const issueTypesResponse = await retryWithBackoff(async () => {
                return await axios.get(
                    `${baseUrl}/rest/api/3/issue/createmeta/${projectConfig.key}/issuetypes`,
                    {
                        headers: authHeaders,
                    }
                );
            });

            const issueTypes: JiraIssueType[] = [];
            const availableIssueTypes = issueTypesResponse.data.issueTypes || [];

            // Only get metadata for configured issue types
            for (const configuredIssueType of projectConfig.issueTypes) {
                const matchingIssueType = availableIssueTypes.find(
                    (it: any) => it.name.toLowerCase() === configuredIssueType.toLowerCase()
                );

                if (matchingIssueType) {
                    console.log(
                        'Getting enhanced fields for project:',
                        projectConfig.key,
                        'issue type:',
                        configuredIssueType
                    );

                    // Get field details with retry logic
                    const fieldsResponse = await retryWithBackoff(async () => {
                        return await axios.get(
                            `${baseUrl}/rest/api/3/issue/createmeta/${projectConfig.key}/issuetypes/${matchingIssueType.id}`,
                            { headers: authHeaders }
                        );
                    });

                    const rawFields = fieldsResponse.data.fields || {};

                    // **CRITICAL FIX**: Validate we got fields
                    if (Object.keys(rawFields).length === 0) {
                        throw new InsufficientDataError(
                            `No fields returned for ${projectConfig.key}-${configuredIssueType}. This indicates an API failure or permission issue.`
                        );
                    }

                    // Validate and sanitize fields with comprehensive field definitions
                    const sanitizedFields = await validateAndSanitizeFields(
                        rawFields,
                        configuredIssueType,
                        projectConfig.key
                    );

                    console.log(
                        'Field analysis for project:',
                        projectConfig.key,
                        'issue type:',
                        configuredIssueType,
                        {
                            totalFields: Object.keys(rawFields).length,
                            processedFields: Object.keys(sanitizedFields).length,
                            requiredFields: Object.values(sanitizedFields).filter(f => f.required)
                                .length,
                        }
                    );

                    issueTypes.push({
                        id: matchingIssueType.id,
                        name: matchingIssueType.name,
                        description: matchingIssueType.description,
                        fields: sanitizedFields,
                    });
                } else {
                    throw new InsufficientDataError(
                        `Issue type '${configuredIssueType}' not found in project '${projectConfig.key}'`
                    );
                }
            }

            metadata[projectConfig.key] = issueTypes;
        } catch (error: any) {
            if (error instanceof InsufficientDataError) {
                throw error; // Re-throw our custom errors
            }

            if (error.response?.status === 401) {
                throw new JiraAuthenticationError(
                    'Authentication failed while fetching project metadata'
                );
            } else if (error.response?.status === 403) {
                throw new JiraApiError(`Access forbidden to project '${projectConfig.key}'`);
            } else if (error.response?.status === 404) {
                throw new JiraApiError(`Project '${projectConfig.key}' not found`);
            } else {
                throw new JiraApiError(
                    `Failed to fetch metadata for project '${projectConfig.key}': ${error.message}`,
                    error.response?.status
                );
            }
        }
    }

    return metadata;
}

function generateFlexibleIssueTypeOpenApiSpec(
    issueType: string,
    issueTypeMetadata?: JiraIssueType,
    fieldDefinitions?: Map<string, { name: string; custom: boolean; schema: any }>
): any {
    // Q Business compliant spec following best practices
    console.log(`Generating Q Business-compliant flexible spec for ${issueType}`);

    const openApiSpec = {
        openapi: '3.0.0',
        info: {
            title: `Jira Custom Plugin for creating ${issueType} issues within Amazon Q Business`,
            description: `Custom Jira plugin integration for Amazon Q Business that enables automated ${issueType} issue creation. This plugin is specific to ${issueType} issues only.`,
            version: '1.0.0',
        },
        servers: [
            {
                url: `https://api.atlassian.com/ex/jira/${process.env.ATLASSIAN_SITE_ID}/rest/api/2`,
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
                    summary: `Create Jira ${issueType}`,
                    description: `Create a new ${issueType} issue in Jira through the Amazon Q Business custom plugin. This endpoint enables users to create Jira ${issueType} issues directly from their Q Business conversations using natural language.`,
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
                    },
                },
            },
        },
        components: {
            schemas: {
                Project: {
                    type: 'object',
                    properties: {
                        id: {
                            type: 'string',
                            description: 'The unique identifier for the project',
                        },
                        key: {
                            type: 'string',
                            description: 'The project key',
                        },
                        name: {
                            type: 'string',
                            description: 'The project name',
                        },
                        projectTypeKey: {
                            type: 'string',
                            description: 'The type of the project',
                        },
                    },
                },
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
                        status: {
                            type: 'object',
                            properties: {
                                name: {
                                    type: 'string',
                                    description: 'Name of the status',
                                },
                            },
                        },
                    },
                },
                NewIssue: generateQBusinessCompliantFlexibleSchema(
                    issueType,
                    issueTypeMetadata,
                    fieldDefinitions
                ),
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

    // Log the generated spec for debugging
    console.log(`Generated flexible spec for ${issueType}:`, JSON.stringify(openApiSpec, null, 2));

    return openApiSpec;
}

function generateProjectIssueTypeOpenApiSpec(
    project: ProjectConfig,
    issueType: string,
    issueTypeMetadata?: JiraIssueType,
    fieldDefinitions?: Map<string, { name: string; custom: boolean; schema: any }>
): any {
    console.log(`Generating Q Business-compliant project spec for ${project.key}-${issueType}`);
    console.log(`Metadata available for ${project.key}-${issueType}:`, {
        hasMetadata: !!issueTypeMetadata,
        fieldCount: issueTypeMetadata?.fields ? Object.keys(issueTypeMetadata.fields).length : 0,
        requiredFieldCount: issueTypeMetadata?.fields
            ? Object.values(issueTypeMetadata.fields).filter(f => f.required).length
            : 0,
    });

    const openApiSpec = {
        openapi: '3.0.0',
        info: {
            title: `Jira Custom Plugin for creating ${issueType} issues for the Jira ${project.name} (${project.key}) project within Amazon Q Business`,
            description: `Custom Jira plugin integration for Amazon Q Business that enables automated ${issueType} issue creation for the Jira ${project.name} (${project.key}) project. This should only be used for the Jira ${project.name} (${project.key}) project and ${issueType} issues.`,
            version: '1.0.0',
        },
        servers: [
            {
                url: `https://api.atlassian.com/ex/jira/${process.env.ATLASSIAN_SITE_ID}/rest/api/2`,
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
                    summary: `Create Jira ${issueType} issues types in ${project.name}`,
                    description: `Create a new Jira ${issueType} issue in the Jira ${project.name} (${project.key}) project. This operation is specifically for ${project.name} project.`,
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
                Project: {
                    type: 'object',
                    properties: {
                        id: {
                            type: 'string',
                            description: 'The unique identifier for the project',
                        },
                        key: {
                            type: 'string',
                            description: 'The project key',
                        },
                        name: {
                            type: 'string',
                            description: 'The project name',
                        },
                    },
                },
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
                        status: {
                            type: 'object',
                            properties: {
                                name: {
                                    type: 'string',
                                    description: 'Name of the status',
                                },
                            },
                        },
                    },
                },
                NewIssue: generateQBusinessCompliantProjectSchema(
                    project,
                    issueType,
                    issueTypeMetadata,
                    fieldDefinitions
                ),
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

    return openApiSpec;
}

function generateQBusinessCompliantFlexibleSchema(
    issueType: string,
    issueTypeMetadata?: JiraIssueType,
    fieldDefinitions?: Map<string, { name: string; custom: boolean; schema: any }>
): any {
    const properties: any = {
        project: {
            type: 'object',
            'x-amzn-form-display-name': 'Project',
            properties: {
                key: {
                    type: 'string',
                    description: 'The key of the project to create the issue in',
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
    };

    const requiredFields = ['project', 'issuetype'];
    const processedFieldNames = new Set(['project', 'issuetype']); // Track processed fields to avoid duplicates

    // Add fields from Jira metadata
    if (issueTypeMetadata?.fields) {
        console.log(
            `Processing ${Object.keys(issueTypeMetadata.fields).length} fields for flexible ${issueType}`
        );

        for (const [fieldId, field] of Object.entries(issueTypeMetadata.fields)) {
            console.log(`Processing field: ${fieldId} (${field.name})`);

            // Find the actual field ID from comprehensive field definitions
            let actualFieldId = fieldId;
            if (fieldDefinitions && field.name) {
                // Look for a field with matching name in the comprehensive definitions
                for (const [realFieldId, fieldDef] of fieldDefinitions.entries()) {
                    if (fieldDef.name === field.name) {
                        actualFieldId = realFieldId;
                        console.log(`Mapped field: ${fieldId} (${field.name}) -> ${actualFieldId}`);
                        break;
                    }
                }
            }

            // Skip if we've already processed this field (avoid duplicates)
            if (processedFieldNames.has(actualFieldId)) {
                console.log(`Skipping duplicate field: ${actualFieldId} (${field.name})`);
                continue;
            }

            const openApiProperty = convertJiraFieldToOpenApiProperty(field);
            if (openApiProperty) {
                // Use the actual field ID that Jira expects
                properties[actualFieldId] = openApiProperty;
                processedFieldNames.add(actualFieldId);

                // Add to required array if field is required in Jira
                if (field.required) {
                    requiredFields.push(actualFieldId);
                }
            }
        }
    } else {
        // Fallback to basic fields if no metadata available
        properties.summary = {
            type: 'string',
            description: 'Summary of the new issue',
            'x-amzn-form-display-name': 'Summary',
        };
        properties.description = {
            type: 'string',
            description: 'Description of the new issue',
            'x-amzn-form-display-name': 'Description',
        };
        requiredFields.push('summary', 'description');
    }

    return {
        type: 'object',
        properties: {
            fields: {
                type: 'object',
                properties,
                required: requiredFields,
            },
        },
    };
}

function generateQBusinessCompliantProjectSchema(
    project: ProjectConfig,
    issueType: string,
    issueTypeMetadata?: JiraIssueType,
    fieldDefinitions?: Map<string, { name: string; custom: boolean; schema: any }>
): any {
    const properties: any = {
        project: {
            type: 'object',
            'x-amzn-form-display-name': 'Project',
            properties: {
                key: {
                    type: 'string',
                    description: 'The key of the project to create the issue in',
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
    };

    const requiredFields = ['project', 'issuetype'];
    const processedFieldNames = new Set(['project', 'issuetype']); // Track processed fields to avoid duplicates

    // Add fields from Jira metadata
    if (issueTypeMetadata?.fields) {
        console.log(
            `Processing ${Object.keys(issueTypeMetadata.fields).length} fields for ${project.key}-${issueType}`
        );

        for (const [fieldId, field] of Object.entries(issueTypeMetadata.fields)) {
            console.log(`Processing field: ${fieldId} (${field.name})`);

            // Find the actual field ID from comprehensive field definitions
            let actualFieldId = fieldId;
            if (fieldDefinitions && field.name) {
                // Look for a field with matching name in the comprehensive definitions
                for (const [realFieldId, fieldDef] of fieldDefinitions.entries()) {
                    if (fieldDef.name === field.name) {
                        actualFieldId = realFieldId;
                        console.log(`Mapped field: ${fieldId} (${field.name}) -> ${actualFieldId}`);
                        break;
                    }
                }
            }

            // Skip if we've already processed this field (avoid duplicates)
            if (processedFieldNames.has(actualFieldId)) {
                console.log(`Skipping duplicate field: ${actualFieldId} (${field.name})`);
                continue;
            }

            const openApiProperty = convertJiraFieldToOpenApiProperty(field);
            if (openApiProperty) {
                // Use the actual field ID that Jira expects
                properties[actualFieldId] = openApiProperty;
                processedFieldNames.add(actualFieldId);

                // Add to required array if field is required in Jira
                if (field.required) {
                    requiredFields.push(actualFieldId);
                }
            }
        }

        console.log(
            `Final field count for ${project.key}-${issueType}: ${Object.keys(properties).length}`
        );
        console.log(`Required fields: ${requiredFields.join(', ')}`);
    } else {
        // Fallback to basic fields if no metadata available
        if (!processedFieldNames.has('summary')) {
            properties.summary = {
                type: 'string',
                description: 'Summary of the new issue',
                'x-amzn-form-display-name': 'Summary',
            };
            requiredFields.push('summary');
            processedFieldNames.add('summary');
        }

        if (!processedFieldNames.has('description')) {
            properties.description = {
                type: 'string',
                description: 'Description of the new issue',
                'x-amzn-form-display-name': 'Description',
            };
            requiredFields.push('description');
            processedFieldNames.add('description');
        }
    }

    return {
        type: 'object',
        properties: {
            fields: {
                type: 'object',
                properties,
                required: requiredFields,
            },
        },
    };
}

function convertJiraFieldToOpenApiProperty(field: JiraField): any {
    const baseProperty: any = {
        description: field.name || `Field ${field.fieldId}`,
    };

    // Handle different Jira field types
    switch (field.schema.type) {
        case 'string':
            baseProperty.type = 'string';
            break;
        case 'number':
            baseProperty.type = 'number';
            break;
        case 'date':
        case 'datetime':
            baseProperty.type = 'string';
            baseProperty.format = field.schema.type === 'date' ? 'date' : 'date-time';
            break;
        case 'array':
            baseProperty.type = 'array';
            if (field.schema.items === 'string') {
                baseProperty.items = { type: 'string' };
            } else if (field.schema.items === 'option') {
                baseProperty.items = { type: 'object' };
            } else {
                baseProperty.items = { type: 'string' }; // fallback
            }
            break;
        case 'option':
        case 'priority':
        case 'issuetype':
        case 'project':
        case 'user':
        case 'group':
            baseProperty.type = 'object';
            baseProperty.properties = {
                id: { type: 'string' },
                name: { type: 'string' },
            };
            break;
        case 'timetracking':
            baseProperty.type = 'object';
            baseProperty.properties = {
                originalEstimate: { type: 'string' },
                remainingEstimate: { type: 'string' },
            };
            break;
        default:
            // For unknown types, default to string
            baseProperty.type = 'string';
            break;
    }

    // Add allowed values if available (for select fields)
    if (field.allowedValues && field.allowedValues.length > 0) {
        if (baseProperty.type === 'string') {
            baseProperty.enum = field.allowedValues.map(v => v.value || v.name);
        } else if (baseProperty.type === 'object') {
            // For object types, add description of allowed values
            const allowedNames = field.allowedValues.map(v => v.name).join(', ');
            baseProperty.description += ` (Allowed values: ${allowedNames})`;
        }
    }

    // Always add Q Business form display name for better UX
    baseProperty['x-amzn-form-display-name'] = field.name || field.fieldId;

    return baseProperty;
}
