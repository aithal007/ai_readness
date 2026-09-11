#!/usr/bin/env python3
"""Pre-submission gate: the mechanical checks an automated grader would run.

Everything here is a pass/fail a script can decide without judgement --
packaging, frontmatter, and the report contract. Run it before zipping.

    python tests/validate_spec.py

Exits non-zero if any check fails.
"""
import io
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOWED_KEYS = {"name", "description", "license", "allowed-tools",
                "metadata", "compatibility"}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

failures = []
notes = []


def fail(msg):
    failures.append(msg)


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def split_frontmatter(raw_bytes, rel):
    """Return the frontmatter block, or None after recording why it failed."""
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        fail("%s: starts with a UTF-8 BOM, which breaks frontmatter parsing" % rel)
        return None
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        fail("%s: not valid UTF-8 (%s)" % (rel, e))
        return None
    if not text.startswith("---"):
        fail("%s: does not open with a '---' frontmatter fence" % rel)
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        fail("%s: frontmatter fence is not closed" % rel)
        return None
    return parts[1]


def parse_simple_yaml(block):
    """Parse the flat subset of YAML the skill spec allows.

    Top-level 'key: value' pairs, plus one level of nesting under a key with
    an empty value. That is all the spec permits, so anything else is a
    finding rather than something to accommodate.
    """
    data = {}
    current = None
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indented = line[0] in " \t"
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if indented:
            if current is not None:
                data.setdefault(current, {})
                if isinstance(data[current], dict):
                    data[current][key] = value
            continue
        if value == "":
            data[key] = {}
            current = key
        else:
            data[key] = value
            current = None
    return data


def check_skill(dirname):
    rel = os.path.join("skills", dirname, "SKILL.md")
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        fail("%s: missing SKILL.md" % rel)
        return None

    block = split_frontmatter(read_bytes(path), rel)
    if block is None:
        return None
    meta = parse_simple_yaml(block)

    extra = set(meta) - ALLOWED_KEYS
    if extra:
        fail("%s: frontmatter has keys outside the closed set: %s"
             % (rel, ", ".join(sorted(extra))))

    for required in ("name", "description"):
        if not meta.get(required):
            fail("%s: frontmatter is missing '%s'" % (rel, required))

    name = meta.get("name", "")
    if name:
        if not NAME_RE.match(name):
            fail("%s: name %r is not lowercase-hyphenated" % (rel, name))
        if unicodedata.normalize("NFKC", name) != unicodedata.normalize("NFKC", dirname):
            fail("%s: name %r does not match its directory %r" % (rel, name, dirname))

    desc = meta.get("description", "")
    if desc and len(desc) > 1024:
        fail("%s: description is %d chars, over the 1024 limit" % (rel, len(desc)))

    tools = meta.get("allowed-tools")
    if isinstance(tools, str) and "," in tools:
        fail("%s: allowed-tools is comma-separated; the spec wants spaces" % rel)

    return name


REF_RE = re.compile(r"(?:references|scripts)/[A-Za-z0-9_.\-]+\.(?:md|py)")


def check_references(dirname):
    """Every references/ or scripts/ path named in a SKILL.md must exist.

    Skills cite each other's files as well as their own, so a path resolves
    against its own skill first and then against any skill in the marketplace.
    """
    rel = os.path.join("skills", dirname, "SKILL.md")
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        return
    try:
        body = io.open(path, encoding="utf-8").read()
    except UnicodeDecodeError:
        return  # already reported by check_skill

    skills_dir = os.path.join(ROOT, "skills")
    others = sorted(d for d in os.listdir(skills_dir)
                    if os.path.isdir(os.path.join(skills_dir, d)))

    for ref in sorted(set(REF_RE.findall(body))):
        if os.path.isfile(os.path.join(skills_dir, dirname, ref)):
            continue
        if any(os.path.isfile(os.path.join(skills_dir, o, ref)) for o in others):
            continue
        fail("%s: references %r, which exists in no skill" % (rel, ref))


def check_marketplace():
    path = os.path.join(ROOT, "marketplace.json")
    if not os.path.isfile(path):
        fail("marketplace.json: missing")
        return []
    try:
        mp = json.loads(io.open(path, encoding="utf-8").read())
    except ValueError as e:
        fail("marketplace.json: not valid JSON (%s)" % e)
        return []

    skills = mp.get("skills", [])
    flagged = [s for s in skills if s.get("entrypoint")]
    if len(flagged) != 1:
        fail("marketplace.json: needs exactly one entrypoint skill, found %d"
             % len(flagged))
    elif mp.get("entrypoint") and mp["entrypoint"] != flagged[0].get("id"):
        fail("marketplace.json: top-level entrypoint %r disagrees with the "
             "skill flagged as entrypoint (%r)"
             % (mp["entrypoint"], flagged[0].get("id")))

    for s in skills:
        p = os.path.join(ROOT, s.get("path", ""))
        if not os.path.isdir(p):
            fail("marketplace.json: %r points at a missing directory %r"
                 % (s.get("id"), s.get("path")))
    return [s.get("id") for s in skills]


def check_report_contract():
    """The report fields the brief names as required must be emitted."""
    sys.path.insert(0, os.path.join(ROOT, "skills", "audit-orchestrator", "scripts"))
    try:
        import finalize_report
    except Exception as e:
        fail("finalize_report.py: will not import (%s: %s)" % (type(e).__name__, e))
        return

    src = io.open(finalize_report.__file__, encoding="utf-8").read()
    summary_block = src.split('"summary": {', 1)
    if len(summary_block) < 2:
        fail("finalize_report.py: could not locate the summary block")
        return
    body = summary_block[1].split("}", 1)[0]
    for field in ("site", "audited_at", "critical", "high", "medium", "low"):
        if '"%s"' % field not in body:
            fail("finalize_report.py: summary does not carry %r" % field)


def check_size():
    total = 0
    biggest = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for f in files:
            p = os.path.join(base, f)
            size = os.path.getsize(p)
            total += size
            biggest.append((size, os.path.relpath(p, ROOT)))
    mb = total / (1024.0 * 1024.0)
    if mb > 50:
        fail("submission is %.1f MB, over the 50 MB limit" % mb)
    notes.append("unpacked size: %.2f MB across %d files" % (mb, len(biggest)))

    for size, rel in biggest:
        if size > 5 * 1024 * 1024:
            fail("%s is %.1f MB -- check this is not a model weight" % (rel, size / 1048576.0))


def main():
    skills_dir = os.path.join(ROOT, "skills")
    dirs = sorted(d for d in os.listdir(skills_dir)
                  if os.path.isdir(os.path.join(skills_dir, d)))
    names = [check_skill(d) for d in dirs]
    for d in dirs:
        check_references(d)
    notes.append("skills validated: %d" % len(dirs))

    declared = check_marketplace()
    for d in dirs:
        if d not in declared:
            fail("skills/%s exists but is not declared in marketplace.json" % d)

    check_report_contract()
    check_size()

    for n in notes:
        print("  " + n)
    if failures:
        print("\n%d CHECK(S) FAILED\n" % len(failures))
        for f in failures:
            print("  FAIL  " + f)
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
