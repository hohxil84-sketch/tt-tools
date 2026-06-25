/**
 * TT Tools Admin — Apple-inspired design system.
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const style = document.createElement('style');
style.textContent = `
  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --blue: #0071e3;
    --blue-hover: #0077ed;
    --gray-100: #f5f5f7;
    --gray-200: #e8e8ed;
    --gray-300: #d2d2d7;
    --gray-400: #aeaeb2;
    --gray-500: #86868b;
    --gray-600: #6e6e73;
    --gray-700: #424245;
    --gray-800: #1d1d1f;
    --red: #ff3b30;
    --orange: #ff9500;
    --green: #34c759;
    --white: #ffffff;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 2px 8px rgba(0,0,0,0.06);
    --shadow-lg: 0 8px 32px rgba(0,0,0,0.08);
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --radius-xl: 20px;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 14px;
    font-weight: 400;
    letter-spacing: -0.01em;
    color: var(--gray-800);
    background: var(--gray-100);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  a { color: inherit; text-decoration: none; }
  button { font-family: inherit; cursor: pointer; }
  input, select, textarea { font-family: inherit; font-size: inherit; }
  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--gray-300); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--gray-400); }
`;
document.head.appendChild(style);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App /></React.StrictMode>
);
