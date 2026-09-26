"""Create the shareable Gemini agent video package."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "PSTrio_gemini_video_demo.zip"
FILES = [
    "submission.zip",
    "gui/server.py",
    "round4/setup_gemini_demo.py",
    "round4/VIDEO_DEMO_GEMINI.md",
    "round4/VIDEO_SCRIPT.md",
    "round4/REPLAY_PSTrio.txt",
    *[p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "gui/static").iterdir())
      if p.is_file()],
]

with ZipFile(PACKAGE, "w", ZIP_DEFLATED) as archive:
    for name in FILES:
        archive.write(ROOT / name, name)

print(f"Created {PACKAGE} with {len(FILES)} files")
