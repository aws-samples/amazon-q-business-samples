module.exports = {
    preset: 'ts-jest',
    testEnvironment: 'node',
    roots: ['<rootDir>/test'],
    testMatch: ['**/*.test.ts'],
    transform: {
        '^.+\\.ts$': 'ts-jest',
    },
    collectCoverageFrom: ['scripts/**/*.ts', 'lambda/**/*.ts', 'lib/**/*.ts', '!**/*.d.ts'],
    moduleFileExtensions: ['ts', 'js', 'json'],
    setupFilesAfterEnv: ['<rootDir>/test/setup.ts'],
    testTimeout: 30000,
    // Suppress console output during tests
    silent: false,
    verbose: false,
};
