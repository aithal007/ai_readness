#!/usr/bin/env python3
"""Build the published showcase of the GUI as a static site.

    python3 gui/build_static.py --out docs --runs RUN_ID [RUN_ID ...]

The page is the same index.html and app.js as the local app. With no server
behind it, the app switches to its static mode: it reads the bundled reports
from data/, cannot start audits, and keeps any report a visitor opens inside
that browser tab only.

Only whitelisted run metadata is published. Every output file is then scanned
for the builder's home directory and user name, and the build fails if either
appears, so a local path can never be published by accident.

Standard library only.
"""
import argparse
import datetime
import getpass
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
RUNS = os.path.join(HERE, "runs")
REPORT_FILES = ("audit_report.json", "evidence.json", "audit_report.md")
META_FIELDS = ("id", "url", "site", "mode", "status", "started_at", "finished_at", "harness",
               "model", "engine_verified", "engine_unchanged", "agent_summary", "max_pages")
DEFAULT_REPO = "https://github.com/aithal007/ai_readness"
ENGINE_SHA256 = "1d5e0f3e4dd12a8c12e205b4723124b4d441cdbf3f76605a2befde9114ec33b1"


def private_markers():
    home = os.path.expanduser("~")
    user = getpass.getuser()
    marks = {home, home.replace("\\", "/"), home.replace("\\", "\\\\")}
    if len(user) >= 4:
        marks.add(user)
    return sorted(m for m in marks if m)


def summarise(report):
    s = report.get("summary", {})
    return {"score": (report.get("readiness") or {}).get("overall"),
            "critical": s.get("critical", 0), "high": s.get("high", 0),
            "medium": s.get("medium", 0), "low": s.get("low", 0),
            "total": s.get("total_findings", len(report.get("findings", [])))}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="docs")
    ap.add_argument("--runs", nargs="+", required=True, help="run ids from gui/runs, in display order")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "data", "runs"))

    # The app itself: the page, the stylesheet, the script and the fonts.
    shutil.copy2(os.path.join(STATIC, "index.html"), os.path.join(out, "index.html"))
    shutil.copytree(STATIC, os.path.join(out, "static"),
                    ignore=shutil.ignore_patterns("index.html", "__pycache__"))
    open(os.path.join(out, ".nojekyll"), "w").close()

    # Cache-bust: a changed stylesheet or script gets a new URL, so a visitor
    # who saw an older build never gets stale CSS next to a newer script.
    index_path = os.path.join(out, "index.html")
    with open(index_path, encoding="utf-8") as fh:
        index = fh.read()
    for asset in ("static/app.css", "static/app.js"):
        with open(os.path.join(out, asset), "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()[:10]
        index = index.replace('"%s"' % asset, '"%s?v=%s"' % (asset, digest))
    with open(index_path, "w", encoding="utf-8") as fh:
        fh.write(index)

    published = []
    for rid in args.runs:
        src = os.path.join(RUNS, rid)
        meta_path = os.path.join(src, "meta.json")
        if not os.path.isfile(meta_path):
            sys.exit("No such run: %s" % rid)
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
        if meta.get("status") != "done":
            sys.exit("Run %s is not finished (status %s)." % (rid, meta.get("status")))
        with open(os.path.join(src, "audit_report.json"), encoding="utf-8") as fh:
            report = json.load(fh)
        dst = os.path.join(out, "data", "runs", rid)
        os.makedirs(dst)
        files = []
        for name in REPORT_FILES:
            if os.path.isfile(os.path.join(src, name)):
                shutil.copy2(os.path.join(src, name), os.path.join(dst, name))
                files.append(name)
        row = {k: meta[k] for k in META_FIELDS if meta.get(k) is not None}
        row["files"] = files
        row["summary"] = summarise(report)
        published.append(row)

    site = {"static": True, "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "repo": args.repo, "engine": {"source": "submission.zip", "sha256": ENGINE_SHA256}, "runs": published}
    with open(os.path.join(out, "data", "site.json"), "w", encoding="utf-8") as fh:
        json.dump(site, fh, indent=1)

    # Refuse to publish anything that names this machine's user or home path.
    marks = private_markers()
    leaks = []
    for base, _dirs, names in os.walk(out):
        for name in names:
            path = os.path.join(base, name)
            if name.endswith(".woff2"):
                continue
            try:
                text = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for m in marks:
                if m in text:
                    leaks.append((os.path.relpath(path, out), m))
    if leaks:
        shutil.rmtree(out)
        for path, m in leaks:
            print("PRIVATE STRING %r in %s" % (m, path), file=sys.stderr)
        sys.exit("Build refused: remove the private strings above and rebuild.")

    total = sum(os.path.getsize(os.path.join(b, n)) for b, _d, ns in os.walk(out) for n in ns)
    print("built  : %s" % out)
    print("runs   : %d (%s)" % (len(published), ", ".join(r["site"] + " " + r["mode"] for r in published)))
    print("size   : %.2f MB" % (total / 1048576.0))
    print("privacy: no home path or user name in any file")


if __name__ == "__main__":
    main()
