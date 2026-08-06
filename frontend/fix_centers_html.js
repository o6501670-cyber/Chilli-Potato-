const fs = require('fs');
const path = 'c:/Users/Dell/OneDrive - CINNTRA INFO TECH SOLUTIONS PRIVATE LIMITED/Desktop/latest chowmein/chowmein/chowmein/chowmein/chowmein/properback/FINAL_POS_CODE_two/frontend/src/app/centers/centers.html';
let html = fs.readFileSync(path, 'utf8');

const brokenBlock = `<div class="services-table-card" *ngIf="isListView">
    <table class="data-table">
      <thead>
        <tr>
          <th style="padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border);">OWNER</th>
          <th style="padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border);">ACTIONS</th>
        </tr>
      </thead>`;

const fixedBlock = `<div class="services-table-card" *ngIf="isListView" style="background: var(--surface); border-radius: var(--radius-xl); border: 1px solid var(--border); overflow: hidden; margin-top: 16px;">
  <table class="data-table" style="width: 100%; border-collapse: collapse;">
    <thead style="background: var(--bg-2); text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.5px; color: var(--text-secondary);">
      <tr>
        <th style="padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border);">NAME</th>
        <th style="padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border);">DISPLAY NAME</th>
        <th style="padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border);">REGION</th>
        <th style="padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border);">PHONE</th>
        <th style="padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border);">OWNER</th>
        <th style="padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border);">ACTIONS</th>
      </tr>
    </thead>`;

// Let's replace regardless of formatting by using regex
html = html.replace(/<div class="services-table-card" \*ngIf="isListView">[\s\S]*?<table class="data-table">[\s\S]*?<thead>[\s\S]*?<tr>[\s\S]*?<th.*?OWNER<\/th>[\s\S]*?<th.*?ACTIONS<\/th>[\s\S]*?<\/tr>[\s\S]*?<\/thead>/, fixedBlock);

fs.writeFileSync(path, html);
console.log('centers.html fixed');
