const fs = require('fs');
const path = 'c:/Users/Dell/OneDrive - CINNTRA INFO TECH SOLUTIONS PRIVATE LIMITED/Desktop/latest chowmein/chowmein/chowmein/chowmein/chowmein/properback/FINAL_POS_CODE_two/frontend/src/app/centers/centers.css';
let css = fs.readFileSync(path, 'utf8');

// 1. Remove .top-bar and tabs CSS
css = css.replace(
  /\.top-bar\s*\{[\s\S]*?\}\s*\.top-bar-left\s*\{[\s\S]*?\}\s*\.tabs-bar\s*\{[\s\S]*?\}\s*\.tab-btn\s*\{[\s\S]*?\}\s*\.tab-btn:hover\s*\{[\s\S]*?\}\s*\.tab-btn\.active\s*\{[\s\S]*?\}\s*\.tab-btn\.active::after\s*\{[\s\S]*?\}\s*\.top-bar-right\s*\{[\s\S]*?\}\s*/,
  ''
);

// 2. Revert .btn
css = css.replace(
  /\.btn\s*\{[\s\S]*?\}/,
  `.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: 0.2s;
  border: 1px solid transparent;
}`
);

// 3. Revert .btn-outline
css = css.replace(
  /\.btn-outline\s*\{[\s\S]*?\}\s*\.btn-outline:hover\s*\{[\s\S]*?\}/,
  ''
);

// 4. Revert .center-card
css = css.replace(
  /\.center-card\s*\{[\s\S]*?\}/,
  `.center-card {
  background: var(--surface);
  border-radius: 16px;
  border: 1px solid var(--border);
  overflow: hidden;
  transition: var(--transition);
  box-shadow: var(--shadow-xs);
}`
);

// 5. Revert .center-badge
css = css.replace(
  /\.center-badge\s*\{[\s\S]*?\}/,
  `.center-badge {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.25rem 0.65rem;
  border-radius: 16px;
  font-size: 0.75rem;
  font-weight: 600;
}`
);

// 6. Revert .center-modal
css = css.replace(
  /\.center-modal\s*\{[\s\S]*?\}/,
  `.center-modal {
  background: var(--surface);
  border-radius: 12px;
  width: 100%;
  max-width: 650px;
  max-height: 85vh;
  overflow-y: auto;
  padding: 24px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.1);
  position: relative;
}`
);

fs.writeFileSync(path, css);
console.log('centers.css reverted');
