"""Build a clean manual-install ZIP from tracked release files."""

import json
import os
import subprocess
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = json.loads((root / "custom_components/ihome_iss50/manifest.json").read_text())["version"]
tag = os.environ.get("RELEASE_TAG", f"v{version}")
if tag != f"v{version}":
    raise SystemExit(f"Tag {tag} does not match manifest version {version}")
paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
dist = root / "dist"
dist.mkdir(exist_ok=True)
target = dist / f"ihome_iss50_direct-{version}.zip"
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in paths:
        if path and (
            path.startswith(("custom_components/", "licenses/"))
            or path
            in {"README.md", "LICENSE", "NOTICE.md", "CHANGELOG.md", "VALIDATION.md", "hacs.json"}
        ):
            archive.write(root / path, path)
print(target)
