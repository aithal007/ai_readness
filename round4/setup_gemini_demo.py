#!/usr/bin/env python3
"""Install the unchanged submitted skills into a fresh Gemini CLI workspace."""

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import shutil
import sys
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "submission.zip"
EXPECTED_SHA256 = "1d5e0f3e4dd12a8c12e205b4723124b4d441cdbf3f76605a2befde9114ec33b1"
PREFIX = "brand-ai-readiness-audit/skills/"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default="demo/gemini_run",
                        help="new folder under this project (default: demo/gemini_run)")
    args = parser.parse_args()

    workspace = (ROOT / args.workspace).resolve()
    if not workspace.is_relative_to(ROOT.resolve()) or workspace == ROOT.resolve():
        parser.error("workspace must be a new folder inside this project")
    if workspace.exists():
        parser.error("workspace already exists; choose another name for a fresh run")
    if not ARCHIVE.is_file():
        parser.error("submission.zip is missing from the project folder")

    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        parser.error("submission.zip SHA-256 does not match the frozen package")

    skills_dir = workspace / ".gemini" / "skills"
    files = 0
    with ZipFile(ARCHIVE) as archive:
        members = [item for item in archive.infolist()
                   if item.filename.startswith(PREFIX) and not item.is_dir()]
        if not members:
            parser.error("submission.zip contains no skills")
        for item in members:
            rel = PurePosixPath(item.filename[len(PREFIX):])
            if not rel.parts or any(part in ("", ".", "..") for part in rel.parts):
                parser.error("submission.zip contains an unsafe skill path")
            target = skills_dir.joinpath(*rel.parts)
            if not target.resolve().is_relative_to(skills_dir.resolve()):
                parser.error("submission.zip contains an unsafe skill path")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(item) as source, target.open("wb") as dest:
                shutil.copyfileobj(source, dest)
            files += 1

    (workspace / "audit_out").mkdir()
    (workspace / "GEMINI.md").write_text(
        "Audit only the URL supplied in the prompt. Activate the audit-orchestrator "
        "skill and follow its procedure. On Windows run its Python scripts with "
        "python if python3 is unavailable. Write generated files only inside "
        "audit_out/. Leave .gemini/skills unchanged. Do not invent web search "
        "results or findings.\n", encoding="utf-8")

    skill_count = sum(1 for _ in skills_dir.glob("*/SKILL.md"))
    print("workspace      :", workspace)
    print("engine SHA-256  :", digest)
    print("skills         :", skill_count, "(%d files copied)" % files)
    print("next           : cd", workspace)
    print("                 gemini")
    return 0


if __name__ == "__main__":
    sys.exit(main())
