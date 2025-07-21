/**
 * Comprehensive Test Suite for Jira Q Business Plugin
 *
 * Consolidated tests for configuration validation, Lambda function, and integration
 */

import * as fs from 'fs';
import { DevTools } from '../scripts/dev-tools';

describe('Jira Q Business Plugin', () => {
    const testConfigDir = './test-configs';

    beforeAll(() => {
        // Ensure test configs directory exists
        if (!fs.existsSync(testConfigDir)) {
            fs.mkdirSync(testConfigDir, { recursive: true });
        }
    });

    describe('Configuration Validation', () => {
        test('should validate flexible-only configuration', () => {
            const config = {
                jiraBaseUrl: 'https://test.atlassian.net',
                jiraApiKeySecretName: 'test-secret',
                qBusinessApplicationId: '12345678-1234-1234-1234-123456789012',
                flexibleIssueTypes: ['Bug', 'Story', 'Epic'],
                metadataProject: 'SAMPLE',
            };

            const configPath = `${testConfigDir}/flexible-only.json`;
            fs.writeFileSync(configPath, JSON.stringify(config, null, 2));

            const tools = new DevTools(configPath);
            expect(() => tools.validateConfig()).not.toThrow();
        });

        test('should validate targeted-only configuration', () => {
            const config = {
                jiraBaseUrl: 'https://test.atlassian.net',
                jiraApiKeySecretName: 'test-secret',
                qBusinessApplicationId: '12345678-1234-1234-1234-123456789012',
                projects: [
                    { key: 'WEBAPP', name: 'Web Application', issueTypes: ['Bug', 'Feature'] },
                    { key: 'API', name: 'Backend API', issueTypes: ['Bug', 'Story'] },
                ],
            };

            const configPath = `${testConfigDir}/targeted-only.json`;
            fs.writeFileSync(configPath, JSON.stringify(config, null, 2));

            const tools = new DevTools(configPath);
            expect(() => tools.validateConfig()).not.toThrow();
        });

        test('should validate mixed configuration', () => {
            const config = {
                jiraBaseUrl: 'https://test.atlassian.net',
                jiraApiKeySecretName: 'test-secret',
                qBusinessApplicationId: '12345678-1234-1234-1234-123456789012',
                projects: [
                    { key: 'WEBAPP', name: 'Web Application', issueTypes: ['Bug', 'Feature'] },
                ],
                flexibleIssueTypes: ['Story', 'Epic'],
                metadataProject: 'SAMPLE',
            };

            const configPath = `${testConfigDir}/mixed.json`;
            fs.writeFileSync(configPath, JSON.stringify(config, null, 2));

            const tools = new DevTools(configPath);
            expect(() => tools.validateConfig()).not.toThrow();
        });

        test('should reject configuration without plugins', () => {
            const config = {
                jiraBaseUrl: 'https://test.atlassian.net',
                jiraApiKeySecretName: 'test-secret',
                qBusinessApplicationId: '12345678-1234-1234-1234-123456789012',
            };

            const configPath = `${testConfigDir}/invalid-no-plugins.json`;
            fs.writeFileSync(configPath, JSON.stringify(config, null, 2));

            const tools = new DevTools(configPath);
            expect(() => tools.validateConfig()).toThrow(
                '❌ At least one plugin type must be configured:'
            );
        });

        test('should reject flexible types without metadata project', () => {
            const config = {
                jiraBaseUrl: 'https://test.atlassian.net',
                jiraApiKeySecretName: 'test-secret',
                qBusinessApplicationId: '12345678-1234-1234-1234-123456789012',
                flexibleIssueTypes: ['Bug', 'Story'],
            };

            const configPath = `${testConfigDir}/invalid-no-metadata.json`;
            fs.writeFileSync(configPath, JSON.stringify(config, null, 2));

            const tools = new DevTools(configPath);
            expect(() => tools.validateConfig()).toThrow(
                'metadataProject is required when flexibleIssueTypes is specified'
            );
        });

        test('should reject configuration without qBusinessApplicationId', () => {
            const config = {
                jiraBaseUrl: 'https://test.atlassian.net',
                jiraApiKeySecretName: 'test-secret',
                projects: [
                    { key: 'WEBAPP', name: 'Web Application', issueTypes: ['Bug', 'Feature'] },
                ],
            };

            const configPath = `${testConfigDir}/invalid-no-qbusiness-id.json`;
            fs.writeFileSync(configPath, JSON.stringify(config, null, 2));

            const tools = new DevTools(configPath);
            expect(() => tools.validateConfig()).toThrow(
                'qBusinessApplicationId is required - must specify an existing Q Business application'
            );
        });
    });

    describe('OpenAPI Spec Generation', () => {
        test('should generate expected flexible specs', () => {
            const config = {
                jiraBaseUrl: 'https://test.atlassian.net',
                qBusinessApplicationId: '12345678-1234-1234-1234-123456789012',
                flexibleIssueTypes: ['Bug', 'Task'],
                metadataProject: 'SAMPLE',
            };

            const configPath = `${testConfigDir}/spec-test.json`;
            fs.writeFileSync(configPath, JSON.stringify(config, null, 2));

            const tools = new DevTools(configPath);
            const outputDir = `${testConfigDir}/expected-specs`;

            tools.generateExpectedSpecs(outputDir);

            // Verify files were created
            expect(fs.existsSync(`${outputDir}/flexible-bug-spec.json`)).toBe(true);
            expect(fs.existsSync(`${outputDir}/flexible-task-spec.json`)).toBe(true);

            // Verify spec structure
            const bugSpec = JSON.parse(
                fs.readFileSync(`${outputDir}/flexible-bug-spec.json`, 'utf8')
            );
            expect(bugSpec.openapi).toBe('3.0.0');
            expect(bugSpec.info.title).toBe('Jira API');
            expect(bugSpec.components.schemas.NewIssue).toBeDefined();
            expect(bugSpec.components.securitySchemes.OAuth2).toBeDefined();
        });

        test('should generate expected targeted specs', () => {
            const config = {
                jiraBaseUrl: 'https://test.atlassian.net',
                qBusinessApplicationId: '12345678-1234-1234-1234-123456789012',
                projects: [{ key: 'TEST', name: 'Test Project', issueTypes: ['Bug'] }],
            };

            const configPath = `${testConfigDir}/targeted-spec-test.json`;
            fs.writeFileSync(configPath, JSON.stringify(config, null, 2));

            const tools = new DevTools(configPath);
            const outputDir = `${testConfigDir}/targeted-specs`;

            tools.generateExpectedSpecs(outputDir);

            // Verify files were created
            expect(fs.existsSync(`${outputDir}/test-bug-spec.json`)).toBe(true);

            // Verify spec structure
            const spec = JSON.parse(fs.readFileSync(`${outputDir}/test-bug-spec.json`, 'utf8'));
            expect(spec.openapi).toBe('3.0.0');
            expect(
                spec.components.schemas.NewIssue.properties.fields.properties.project.properties.key
                    .enum
            ).toEqual(['TEST']);
        });
    });

    afterAll(() => {
        // Clean up test files
        if (fs.existsSync(testConfigDir)) {
            fs.rmSync(testConfigDir, { recursive: true, force: true });
        }
    });
});
