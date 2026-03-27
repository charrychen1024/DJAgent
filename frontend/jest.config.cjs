module.exports = {
  testEnvironment: 'jsdom',
  roots: ['<rootDir>/src'],
  testMatch: ['**/__tests__/**/*.{js,jsx}', '**/?(*.)+(spec|test).{js,jsx}'],
  moduleFileExtensions: ['js', 'jsx', 'json'],
  transform: {
    '^.+\\.(jsx?)$': 'babel-jest',
    '.+\\.(css|styl|less|sass|scss|gif|eot|svg|ttf|woff|woff2|mp4|webm)$': 'jest-transform-stub',
  },
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.js'],
  collectCoverageFrom: [
    'src/**/*.{js,jsx}',
    '!src/main.jsx',
    '!src/**/*.test.{js,jsx}',
    '!src/**/__tests__/**',
  ],
  coverageThreshold: {
    global: {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85,
    },
  },
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '^react-markdown$': '<rootDir>/src/__mocks__/react-markdown.js',
    '^remark-gfm$': '<rootDir>/src/__mocks__/remark-gfm.js',
  },
  testPathIgnorePatterns: ['/node_modules/', '/dist/'],
  transformIgnorePatterns: [
    'node_modules/(?!(react-markdown|remark-gfm|escape-string-regexp|markdown-table|unist-.*|unified|ccount|char-regex|micromark.*|decode-named-character-reference|character-entities-legacy)/)'
  ],
};
