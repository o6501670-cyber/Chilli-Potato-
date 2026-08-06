const fs = require('fs');
const path = 'c:/Users/Dell/OneDrive - CINNTRA INFO TECH SOLUTIONS PRIVATE LIMITED/Desktop/latest chowmein/chowmein/chowmein/chowmein/chowmein/properback/FINAL_POS_CODE_two/frontend/src/app/admin/admin.css';
let css = fs.readFileSync(path, 'utf8');

css = css.replace(
  /\.admin-subnav\s*\{[\s\S]*?\}/,
  `.admin-subnav {
  display: flex;
  align-items: center;
  padding: 0 24px 16px;
  overflow-x: auto;
  flex-shrink: 0;
  gap: 8px;
}`
);

css = css.replace(
  /\.subnav-tab\s*\{[\s\S]*?\}/g,
  `.subnav-tab {
  display: inline-flex;
  align-items: center;
  padding: 8px 16px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: 20px;
  white-space: nowrap;
  cursor: pointer;
  transition: all 150ms ease;
  background: transparent;
  border: none;
}`
);

css = css.replace(
  /\.subnav-tab:hover\s*\{[\s\S]*?\}/,
  `.subnav-tab:hover { background: var(--bg-2); color: var(--text-primary); }`
);

css = css.replace(
  /\.subnav-tab\.active\s*\{[\s\S]*?\}/,
  `.subnav-tab.active { background: var(--black); color: var(--white); font-weight: 600; }`
);

// We also added a ::after pseudo-element that we need to remove
css = css.replace(
  /\.subnav-tab\.active::after\s*\{[\s\S]*?\}/,
  ''
);

fs.writeFileSync(path, css);
console.log('admin.css reverted');
