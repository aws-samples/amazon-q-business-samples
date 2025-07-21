/**
 * Jest test setup file
 * Configures test environment and mocks console output to reduce noise
 */

// Mock console.log during tests to reduce output noise
const originalConsoleLog = console.log;

beforeAll(() => {
    // Suppress console.log during tests unless explicitly needed
    console.log = jest.fn();
});

afterAll(() => {
    // Restore original console.log
    console.log = originalConsoleLog;
});
