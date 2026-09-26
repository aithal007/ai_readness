"""Create the small, self-contained Windows video demo package."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "PSTrio_video_demo.zip"
FILES = [
    "submission.zip",
    "start_video_demo.cmd",
    "gui/server.py",
    "round4/VIDEO_DEMO_ENGINE.md",
    "round4/REPLAY_ENGINE.txt",
    *[p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "gui/static").iterdir())
      if p.is_file()],
]

with ZipFile(PACKAGE, "w", ZIP_DEFLATED) as archive:
    for name in FILES:
        archive.write(ROOT / name, name)

print(f"Created {PACKAGE} with {len(FILES)} files")
