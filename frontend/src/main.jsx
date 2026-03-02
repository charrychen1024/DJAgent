import { createRoot } from 'react-dom/client'
import React from 'react'
import './index.css'
import App from './App.jsx'

console.log('main.jsx loading...')
console.log('App:', App)

try {
  createRoot(document.getElementById('root')).render(
    React.createElement(App)
  )
  console.log('React rendered successfully')
} catch(e) {
  console.error('Render error:', e)
}
