import os
import ast
import json

backend_dir = r"backend"

def get_model_fields(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            node = ast.parse(f.read())
        
        models = {}
        for n in node.body:
            if isinstance(n, ast.ClassDef):
                fields = []
                for child in n.body:
                    if isinstance(child, ast.Assign) and len(child.targets) == 1:
                        target = child.targets[0]
                        if isinstance(target, ast.Name):
                            field_name = target.id
                            if isinstance(child.value, ast.Call) and hasattr(child.value.func, 'attr'):
                                field_type = child.value.func.attr
                                fields.append(f"{field_name} ({field_type})")
                            else:
                                fields.append(field_name)
                models[n.name] = fields
        return models
    except Exception as e:
        return {}

def scan_model_fields():
    apps = ['billing', 'appointments', 'clients', 'finance', 'staff', 'marketing', 'inventory']
    
    results = {}
    
    for app in apps:
        models_path = os.path.join(backend_dir, app, 'models.py')
        if os.path.exists(models_path):
            results[app] = get_model_fields(models_path)

    return results

if __name__ == "__main__":
    out = scan_model_fields()
    with open("backend_model_fields.json", 'w') as f:
        json.dump(out, f, indent=4)
    print("Model fields scan completed.")
