import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.urls import get_resolver

resolver = get_resolver()
with open("urls_mapping.txt", "w") as f:
    for p in resolver.url_patterns:
        if hasattr(p, 'url_patterns'):
            for p2 in p.url_patterns:
                cb = getattr(p2, "callback", None)
                cb_name = cb.__name__ if cb else str(cb)
                f.write(f"/{p.pattern}{p2.pattern} -> {cb_name}\n")
        else:
            cb = getattr(p, "callback", None)
            cb_name = cb.__name__ if cb else str(cb)
            f.write(f"/{p.pattern} -> {cb_name}\n")
