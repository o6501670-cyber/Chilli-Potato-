import re

ts_file = 'frontend/src/app/dashboard/dashboard.ts'
with open(ts_file, 'r', encoding='utf-8') as f:
    content = f.read()

new_defaults = """    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.95)';
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 12;
    Chart.defaults.scale.grid.display = false;
    Chart.defaults.scale.ticks.color = '#94a3b8';
    Chart.defaults.elements.bar.borderRadius = 100;
    Chart.defaults.elements.bar.borderSkipped = false;
    Chart.defaults.elements.line.tension = 0.4;
    Chart.defaults.elements.point.radius = 0;
    Chart.defaults.elements.point.hoverRadius = 6;
"""

# Replace existing defaults block
content = re.sub(
    r'Chart\.defaults\.font\.family = [^;]+;[\s\S]*?(?=this\.startDate =)',
    new_defaults + '\n    ',
    content
)

with open(ts_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated Chart.js defaults")
