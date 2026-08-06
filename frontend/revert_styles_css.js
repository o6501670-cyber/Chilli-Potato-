const fs = require('fs');
const path = 'c:/Users/Dell/OneDrive - CINNTRA INFO TECH SOLUTIONS PRIVATE LIMITED/Desktop/latest chowmein/chowmein/chowmein/chowmein/chowmein/properback/FINAL_POS_CODE_two/frontend/src/styles.css';
let css = fs.readFileSync(path, 'utf8');

css = css.replace(
  /\/\*\s*===================================================================\s*DASHBOARD PANEL UTILITIES[\s\S]*?\.dashboard-btn-pill-primary\s*\{[\s\S]*?\}\s*/,
  ''
);

fs.writeFileSync(path, css);
console.log('styles.css reverted');
