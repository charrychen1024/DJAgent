// Mock for react-markdown in test environment
module.exports = function MockReactMarkdown({ children, remarkPlugins, ...props }) {
  const React = require('react');
  return React.createElement('div', { ...props, className: 'markdown', 'data-testid': 'mock-markdown' }, children);
};


