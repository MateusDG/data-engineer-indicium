"""Package an allowlist of project files, excluding credentials, state and source data."""
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
destination = root / "delivery/banvic-projeto.zip"
destination.parent.mkdir(exist_ok=True)
directories = ["config", "dags", "docker", "infra", "meltano", "pipeline", "scripts", "sql", "tests", "docs", "evidence"]
files = [root / name for name in ["README.md", ".gitignore", ".gitattributes", ".dockerignore"]]
for directory in directories:
    files.extend(path for path in (root / directory).rglob("*") if path.is_file())
blocked = {".terraform", ".meltano", "__pycache__", "private", ".venv"}
with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(files):
        relative = path.relative_to(root)
        if any(part in blocked for part in relative.parts) or path.name.endswith((".pyc", ".tfstate", ".tfstate.backup")):
            continue
        archive.write(path, relative.as_posix())
    archive.writestr("data/input/.gitkeep", "")
print(destination)
