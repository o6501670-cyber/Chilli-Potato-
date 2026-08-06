import os

ts_file = 'frontend/src/app/dashboard/dashboard.ts'
with open(ts_file, 'r', encoding='utf-8') as f:
    content = f.read()

chart_config = '''
    // Apply Global Cinematic Chart Settings
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.color = '#64748b';
    
    // Hide all grid lines for cleaner UI
    Chart.defaults.scale.grid.display = false;
    
    // Round all bar charts for modern feel
    Chart.defaults.elements.bar.borderRadius = 6;
    
    // Beautiful tooltips
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.9)';
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.plugins.tooltip.titleFont = { size: 14, weight: 'bold', family: 'Inter' };
    Chart.defaults.plugins.tooltip.bodyFont = { size: 13, family: 'Inter' };
'''

if "Chart.defaults.font.family" not in content:
    content = content.replace(
        "ngOnInit() {",
        "ngOnInit() {\n" + chart_config
    )

with open(ts_file, 'w', encoding='utf-8') as f:
    f.write(content)

print('Injected Chart global configuration into dashboard.ts')
