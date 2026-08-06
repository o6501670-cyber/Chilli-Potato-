import os
import django
from django.conf import settings
from django.urls import get_resolver

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

def get_urls(patterns, prefix=''):
    urls = []
    for p in patterns:
        if hasattr(p, 'url_patterns'):
            # it's an include()
            urls.extend(get_urls(p.url_patterns, prefix + str(p.pattern)))
        else:
            urls.append(prefix + str(p.pattern))
    return urls

urls = get_urls(get_resolver().url_patterns)
for u in sorted(urls):
    print(f"/{u}")
