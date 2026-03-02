import React from 'react';
import { createRoot } from 'react-dom/client';

const div = document.createElement('div');
div.id = 'test';
document.body.appendChild(div);

try {
  const root = createRoot(div);
  root.render(React.createElement('div', null, 'Test'));
  console.log('React works!');
} catch(e) {
  console.error('React error:', e);
}
