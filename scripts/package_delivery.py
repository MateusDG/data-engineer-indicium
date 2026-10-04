"""Package code and public evidence; reject secrets, state, archives and source rows."""
import zipfile
from pathlib import Path

DIRECTORIES = ["config", "dags", "docker", "infra", "meltano", "pipeline", "scripts", "sql", "tests", "docs", "evidence"]
ROOT_FILES = ["README.md", ".gitignore", ".gitattributes", ".dockerignore"]
SAFE_SUFFIXES = {".py", ".sh", ".ps1", ".tf", ".hcl", ".yaml", ".yml", ".json",
                 ".md", ".txt", ".mjs", ".sql", ".html", ".png", ".dockerfile"}
BLOCKED_DIRECTORIES = {".terraform", ".meltano", "__pycache__", "private", ".venv", ".secrets", ".runtime"}


def package_project(root: Path, destination: Path) -> list[str]:
    files = [root / name for name in ROOT_FILES if (root / name).is_file()]
    for directory in DIRECTORIES:
        files.extend(path for path in (root / directory).rglob("*") if path.is_file())
    names = []
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            relative = path.relative_to(root)
            lower = path.name.lower()
            if path.is_symlink() or any(part.lower() in BLOCKED_DIRECTORIES for part in relative.parts):
                continue
            if lower.startswith(".env") or ".tfstate" in lower or ".tfplan" in lower:
                continue
            if path.suffix.lower() == ".json" and any(word in lower for word in ("credential", "secret", "password")):
                continue
            if relative.as_posix() not in ROOT_FILES and path.suffix.lower() not in SAFE_SUFFIXES:
                continue
            archive.write(path, relative.as_posix())
            names.append(relative.as_posix())
        archive.writestr("data/input/.gitkeep", "")
        names.append("data/input/.gitkeep")
    return names


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    destination = root / "delivery/banvic-projeto.zip"
    package_project(root, destination)
    print(destination)
