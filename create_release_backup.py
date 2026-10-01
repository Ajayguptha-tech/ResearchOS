"""Create a secure timestamped release backup of ResearchOS."""
import os
import zipfile
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = os.path.abspath("backups")
os.makedirs(backup_dir, exist_ok=True)
zip_path = os.path.join(backup_dir, f"researchos_release_backup_{timestamp}.zip")

# Directories and files to include
include_items = [
    "ai",
    "backend/app",
    "backend/tests",
    "backend/data/researchos.db",
    "backend/data/uploads",
    "backend/requirements.txt",
    "backend/.env.example",
    "backend/*.py",
    "frontend/app",
    "frontend/components",
    "frontend/lib",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/tsconfig.json",
    "frontend/tailwind.config.js",
    "frontend/postcss.config.js",
    "docs",
    "infra",
    "knowledge_graph",
    ".env.example",
    ".gitignore",
    "README.md",
    "IMPLEMENTATION_PLAN.md",
    "docker-compose.yml",
]

# Strict exclusions
exclude_patterns = [
    ".env", ".env.local", ".venv", "node_modules", ".next",
    "__pycache__", ".pytest_cache", ".git", ".freebuff", ".tmp"
]

def should_exclude(path):
    parts = path.replace("\\", "/").split("/")
    for p in parts:
        if p in [".env", ".env.local", ".venv", "node_modules", ".next", "__pycache__", ".pytest_cache", ".git"]:
            return True
        if p.endswith(".pyc") or p.endswith(".pyo"):
            return True
    return False

print(f"Creating secure release backup at: {zip_path}")
file_count = 0

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    # 1. Add database
    db_file = "backend/data/researchos.db"
    if os.path.exists(db_file):
        zf.write(db_file, arcname="database/researchos.db")
        file_count += 1
        print("  Added database/researchos.db")
    
    # 2. Add uploads
    upload_dir = "backend/data/uploads"
    if os.path.exists(upload_dir):
        for root, _, files in os.walk(upload_dir):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, upload_dir)
                zf.write(full, arcname=f"uploads/{rel}")
                file_count += 1
        print("  Added uploads/")

    # 3. Add source code and templates
    for item in ["ai", "backend", "frontend", "docs", "infra", "knowledge_graph"]:
        if not os.path.exists(item):
            continue
        for root, dirs, files in os.walk(item):
            # Prune excluded dirs in-place
            dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]
            for f in files:
                full = os.path.join(root, f)
                if should_exclude(full):
                    continue
                # Never include any .env file
                if f.startswith(".env") and not f.endswith(".example"):
                    continue
                rel = full.replace("\\", "/")
                zf.write(full, arcname=f"source/{rel}")
                file_count += 1

    # 4. Add root files
    for rf in [".env.example", ".gitignore", "README.md", "IMPLEMENTATION_PLAN.md", "docker-compose.yml"]:
        if os.path.exists(rf):
            zf.write(rf, arcname=f"config_and_docs/{rf}")
            file_count += 1

print(f"Backup created successfully! Total files: {file_count}, Size: {os.path.getsize(zip_path)} bytes")
print(f"Backup archive location: {zip_path}")
