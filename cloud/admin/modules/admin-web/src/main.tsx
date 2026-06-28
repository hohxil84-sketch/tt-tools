/**
 * Alphoria Admin — Apple-inspired design system.
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
    font-family: "PingFang SC", "苹方", -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", "Microsoft YaHei", sans-serif;
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
  /* 全局强制苹方 */
  h1, h2, h3, h4, h5, h6, th, td, label, code, pre, span, div, p, a, button, input, select, textarea, option {
    font-family: "PingFang SC", "苹方", -apple-system, BlinkMacSystemFont, "Helvetica Neue", "Microsoft YaHei", sans-serif;
  }
  input:focus, select:focus, textarea:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.12);
    outline: none;
  }
  /* 输入框过渡动画 */
  input, select, textarea {
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }
  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--gray-300); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--gray-400); }

  /* 表格行样式 — 淡蓝间隔 + 悬停效果 */
  .admin-table tbody tr {
    border-bottom: 1px solid rgba(0, 113, 227, 0.14);
    transition: background 0.12s ease;
  }
  .admin-table tbody tr:last-child {
    border-bottom: none;
  }
  .admin-table tbody tr:hover {
    background: rgba(0, 113, 227, 0.10);
  }
  .admin-table tbody td {
    padding: 12px 16px;
    vertical-align: middle;
    word-break: break-all;
    overflow-wrap: break-word;
    max-width: 0;
  }
  .admin-table thead th {
    padding: 10px 16px;
    font-weight: 600;
    font-size: 11px;
    color: var(--blue);
    letter-spacing: 0.02em;
    text-transform: uppercase;
    border-bottom: 2px solid rgba(0, 113, 227, 0.30);
    background: rgba(0, 113, 227, 0.08);
    white-space: nowrap;
  }
  /* 偶数行淡蓝底色 */
  .admin-table tbody tr:nth-child(even) {
    background: rgba(0, 113, 227, 0.05);
  }
  .admin-table tbody tr:nth-child(even):hover {
    background: rgba(0, 113, 227, 0.12);
  }
`;
document.head.appendChild(style);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App /></React.StrictMode>
);
