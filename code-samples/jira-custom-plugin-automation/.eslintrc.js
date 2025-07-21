module.exports = {
    parser: '@typescript-eslint/parser',
    parserOptions: {
        ecmaVersion: 2020,
        sourceType: 'module',
    },
    plugins: ['@typescript-eslint', 'prettier', 'node'],
    extends: [
        'eslint:recommended',
        'plugin:node/recommended',
        'plugin:prettier/recommended',
        'prettier',
    ],
    env: {
        node: true,
        es2020: true,
        jest: true,
    },
    ignorePatterns: [
        '*.js',
        '*.d.ts',
        '*.js.map',
        'cdk.out/',
        'node_modules/',
    ],
    rules: {
        // TypeScript specific rules
        '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
        '@typescript-eslint/explicit-function-return-type': 'off',
        '@typescript-eslint/explicit-module-boundary-types': 'off',
        '@typescript-eslint/no-explicit-any': 'warn',
        '@typescript-eslint/no-non-null-assertion': 'warn',

        // Security rules (temporarily disabled due to plugin compatibility)
        // 'security/detect-object-injection': 'warn',
        // 'security/detect-non-literal-fs-filename': 'off', // We have custom path validation

        // Node.js rules
        'node/no-missing-import': 'off', // TypeScript handles this
        'node/no-unsupported-features/es-syntax': 'off', // We use TypeScript
        'node/no-unpublished-import': 'off', // Allow dev dependencies

        // General rules
        'no-console': 'off', // Allow console in CLI tools
        'prefer-const': 'error',
        'no-var': 'error',

        // Prettier integration
        'prettier/prettier': 'error',
    },
    settings: {
        node: {
            tryExtensions: ['.js', '.ts', '.json'],
        },
    },
    overrides: [
        {
            files: ['*.js'],
            rules: {
                '@typescript-eslint/no-var-requires': 'off',
            },
        },
        {
            files: ['test/**/*'],
            env: {
                jest: true,
            },
            rules: {
                '@typescript-eslint/no-explicit-any': 'off',
            },
        },
    ],
};
