import os
import ast
import json

backend_dir = r"backend"

def get_classes_from_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            node = ast.parse(f.read())
        return [n.name for n in node.body if isinstance(n, ast.ClassDef)]
    except Exception as e:
        return []

def scan_backend():
    apps = [d for d in os.listdir(backend_dir) if os.path.isdir(os.path.join(backend_dir, d)) and d not in ('__pycache__', 'venv', 'venv_old', 'pos_backend', 'media')]
    
    results = {}
    
    for app in apps:
        app_path = os.path.join(backend_dir, app)
        results[app] = {
            'models': [],
            'views': [],
            'urls': False
        }
        
        models_path = os.path.join(app_path, 'models.py')
        if os.path.exists(models_path):
            results[app]['models'] = get_classes_from_file(models_path)
            
        views_path = os.path.join(app_path, 'views.py')
        if os.path.exists(views_path):
            results[app]['views'] = get_classes_from_file(views_path)
            
        urls_path = os.path.join(app_path, 'urls.py')
        if os.path.exists(urls_path):
            results[app]['urls'] = True

    return results

if __name__ == "__main__":
    out = scan_backend()
    with open("backend_scan_results.json", 'w') as f:
        json.dump(out, f, indent=4)
    print("Backend scan completed.")
