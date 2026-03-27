import '@testing-library/jest-dom';

// Mock window.confirm
global.confirm = jest.fn(() => true);

// Mock window.alert
global.alert = jest.fn();

// Setup any other global test utilities
beforeEach(() => {
  jest.clearAllMocks();
});
