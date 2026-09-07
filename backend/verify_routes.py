"""Verify all API routes are registered."""
import sys
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath('..'))
from app.main import app

# Get all routes including sub-apps
all_paths = []
for route in app.routes:
    if hasattr(route, 'path'):
        all_paths.append(route.path)
    if hasattr(route, 'routes'):
        for sub in route.routes:
            if hasattr(sub, 'path'):
                all_paths.append(sub.path)

for p in sorted(all_paths):
    print(p)
print(f"\nTotal: {len(all_paths)} routes")
