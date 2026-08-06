const fs = require('fs');
const path = require('path');

const adminDir = 'c:/Users/Dell/OneDrive - CINNTRA INFO TECH SOLUTIONS PRIVATE LIMITED/Desktop/latest chowmein/chowmein/chowmein/chowmein/chowmein/properback/FINAL_POS_CODE_two/frontend/src/app/admin';
const otherDirs = ['users', 'roles', 'services'].map(d => path.join('c:/Users/Dell/OneDrive - CINNTRA INFO TECH SOLUTIONS PRIVATE LIMITED/Desktop/latest chowmein/chowmein/chowmein/chowmein/chowmein/properback/FINAL_POS_CODE_two/frontend/src/app', d));

function getHtmlFiles(dir, files = []) {
  if (!fs.existsSync(dir)) return files;
  const entries = fs.readdirSync(dir);
  for (const entry of entries) {
    const fullPath = path.join(dir, entry);
    if (fs.statSync(fullPath).isDirectory()) {
      getHtmlFiles(fullPath, files);
    } else if (fullPath.endsWith('.html') && !fullPath.includes('admin.html')) {
      files.push(fullPath);
    }
  }
  return files;
}

let allFiles = getHtmlFiles(adminDir);
otherDirs.forEach(dir => {
  allFiles = allFiles.concat(getHtmlFiles(dir));
});

allFiles.forEach(file => {
  let content = fs.readFileSync(file, 'utf8');
  let changed = false;

  if (content.includes('dashboard-panel')) {
    content = content.replace(/class="card dashboard-panel"/g, 'class="card"');
    content = content.replace(/class="services-table-card dashboard-panel"/g, 'class="services-table-card"');
    content = content.replace(/<thead class="dashboard-panel-header"/g, '<thead');
    changed = true;
  }
  if (content.includes('dashboard-btn-pill-primary')) {
    content = content.replace(/btn-primary dashboard-btn-pill-primary/g, 'btn-primary');
    changed = true;
  }
  if (content.includes('dashboard-btn-pill')) {
    content = content.replace(/btn-outline dashboard-btn-pill/g, 'btn-outline');
    changed = true;
  }

  if (changed) {
    fs.writeFileSync(file, content);
    console.log('Reverted:', path.basename(file));
  }
});
