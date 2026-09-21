#!/usr/bin/env python3
"""Build the Round 4 demo workspace from the submitted Round 3 package.

Claude Code discovers project skills under <workspace>/.claude/skills/, while
the marketplace keeps them under skills/. This copies the submitted skills
across unchanged and then proves it: every file is hashed on both sides and
the run fails if a single byte differs. That check is the answer to "is the
demo running the engine that was submitted?".

    python3 setup_demo.py --source final_adobe --workspace demo
    python3 setup_demo.py --source final_adobe --workspace demo --verify-only

--source may be the submitted archive (with or without a .zip extension) or an
already-extracted marketplace directory. Standard library only, read-only with
respect to the source.
"""
import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import zipfile


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_hashes(root):
    out = {}
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(files):
            full = os.path.join(base, name)
            out[os.path.relpath(full, root).replace(os.sep, "/")] = sha256(full)
    return out


def fingerprint(hashes):
    h = hashlib.sha256()
    for rel in sorted(hashes):
        h.update(("%s %s\n" % (rel, hashes[rel])).encode("utf-8"))
    return h.hexdigest()


def find_marketplace_root(start):
    """The directory holding marketplace.json, tolerating a wrapper folder."""
    for base, _dirs, files in os.walk(start):
        if "marketplace.json" in files:
            return base
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", required=True,
                    help="submitted archive, or an extracted marketplace directory")
    ap.add_argument("--workspace", default="demo")
    ap.add_argument("--verify-only", action="store_true",
                    help="do not copy; check an existing workspace against the source "
                         "and exit non-zero on any difference")
    args = ap.parse_args()

    scratch = None
    src = args.source
    if os.path.isfile(src):
        if not zipfile.is_zipfile(src):
            print("error: %s is not a zip archive" % src, file=sys.stderr)
            return 2
        scratch = tempfile.mkdtemp(prefix="r3_")
        with zipfile.ZipFile(src) as z:
            z.extractall(scratch)
        src = scratch

    root = find_marketplace_root(src)
    if not root:
        print("error: no marketplace.json found under %s" % args.source, file=sys.stderr)
        return 2

    skills_src = os.path.join(root, "skills")
    skills_dst = os.path.join(args.workspace, ".claude", "skills")
    if args.verify_only:
        if not os.path.isdir(skills_dst):
            print("error: no installed skills at %s" % skills_dst, file=sys.stderr)
            return 2
    else:
        if os.path.exists(skills_dst):
            shutil.rmtree(skills_dst)
        os.makedirs(os.path.dirname(skills_dst), exist_ok=True)
        shutil.copytree(skills_src, skills_dst, ignore=shutil.ignore_patterns("__pycache__"))

    want, got = tree_hashes(skills_src), tree_hashes(skills_dst)
    if want != got:
        diff = sorted(k for k in set(want) | set(got) if want.get(k) != got.get(k))
        print("INTEGRITY FAILURE: workspace differs from the submitted skills:", file=sys.stderr)
        for k in diff:
            print("  " + k, file=sys.stderr)
        return 1

    print("workspace        : %s" % os.path.abspath(args.workspace))
    print("skills installed : %d" % len(os.listdir(skills_dst)))
    print("files compared   : %d (all byte-identical to the submitted package)" % len(got))
    print("engine SHA-256   : %s" % fingerprint(got))
    if not args.verify_only:
        print("\nnext: cd %s  and start your agent harness there." % args.workspace)

    if scratch:
        shutil.rmtree(scratch, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
