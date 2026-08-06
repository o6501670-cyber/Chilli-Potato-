
with open('src/app/admin/admin.ts', 'r', encoding='utf-8') as f:
    text = f.read()

old_init = '''    // Theme logic
    const savedTheme = localStorage.getItem('theme') || 'default';
    this.isDarkMode = savedTheme === 'dark';
    this.applyTheme();'''

new_init = '''    // Theme logic
    const savedTheme = localStorage.getItem('theme') || 'light';
    this.currentTheme = (savedTheme === 'default' || savedTheme === 'light') ? 'light' : savedTheme;
    this.applyTheme();'''

text = text.replace(old_init, new_init)

old_logic = '''  isDarkMode = false;

  toggleDarkMode() {
    this.isDarkMode = !this.isDarkMode;
    this.applyTheme();
    localStorage.setItem('theme', this.isDarkMode ? 'dark' : 'default');
  }

  applyTheme() {
    if (!this.isDarkMode) {
      document.body.removeAttribute('data-theme');
    } else {
      document.body.setAttribute('data-theme', 'dark');
    }
  }'''

new_logic = '''  currentTheme = 'light';

  toggleTheme() {
    if (this.currentTheme === 'light') {
      this.currentTheme = 'dark';
    } else if (this.currentTheme === 'dark') {
      this.currentTheme = 'colorful';
    } else {
      this.currentTheme = 'light';
    }
    this.applyTheme();
    localStorage.setItem('theme', this.currentTheme);
  }

  applyTheme() {
    if (this.currentTheme === 'light' || this.currentTheme === 'default') {
      document.body.removeAttribute('data-theme');
    } else {
      document.body.setAttribute('data-theme', this.currentTheme);
    }
  }'''

text = text.replace(old_logic, new_logic)

with open('src/app/admin/admin.ts', 'w', encoding='utf-8') as f:
    f.write(text)

print('admin.ts patched for colorful theme.')

