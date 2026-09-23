#!/usr/bin/env python3
"""Local web GUI for the brand-ai-readiness-audit marketplace.

    python3 gui/server.py            # then open http://127.0.0.1:8765

The GUI is a viewer and a launcher, never part of the engine. It runs the
scripts inside submission.zip -- the frozen Round 3 package -- exactly as
shipped: the archive is checked against its published SHA-256, unpacked into a
cache, and executed from there. Nothing in the package is modified.

Two ways to run an audit:

  engine  The scripted pipeline (collect -> six analyzers -> critic ->
          report). Deterministic, no LLM, no account needed.
  agent   Claude Code, headless, driving the audit-orchestrator skill the way
          the SKILL.md intends, including the judgement checks and the review
          the scripts cannot do. Offered only when a Claude Code binary is
          found (set CLAUDE_BIN to point at one explicitly).

A report produced anywhere else -- for example by an interactive agent
session -- can be imported and browsed the same way.

Standard library only. Binds to 127.0.0.1 by default and rejects requests
whose Host header is not local, so other sites in the browser cannot drive it.
"""
import argparse
import datetime
import glob
import hashlib
import http.server
import json
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STATIC = os.path.join(HERE, "static")
RUNS = os.path.join(HERE, "runs")
CACHE = os.path.join(HERE, ".engine")

SUBMISSION_ZIP = os.path.join(REPO, "submission.zip")
SUBMISSION_SHA256 = "1d5e0f3e4dd12a8c12e205b4723124b4d441cdbf3f76605a2befde9114ec33b1"
UNPACKED_FALLBACK = os.path.join(REPO, "brand-ai-readiness-audit")

DEFAULT_MODEL = "claude-sonnet-5"
AGENT_TOOLS = ["Skill", "Bash", "Read", "Write", "Glob", "Grep", "WebSearch"]
AGENT_PROMPT = (
    "Use the audit-orchestrator skill to audit {url} for AI discoverability and "
    "on-site engagement. Use today's real date. Write every output file into "
    "./audit_out/, ending with audit_out/audit_report.json and "
    "audit_out/audit_report.md. Then summarise the critical and high findings and "
    "the remediation roadmap."
)
MAX_CONCURRENT = 2
LOG_CAP = 3000
ANALYZERS = ["crawl-render-audit", "structured-data-entity-audit", "ai-citability-audit",
             "answerability-probe", "freshness-corroboration-audit", "engagement-audit"]
RUN_FILES = ("audit_report.json", "audit_report.md", "evidence.json",
             "raw_findings.json", "adjudicated.json")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,120}$")


# ---------------------------------------------------------------------------
# Engine: the frozen package, verified and unpacked
# ---------------------------------------------------------------------------

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_digest(root):
    """One hash over every file under root, so a run can prove it left the
    engine exactly as it found it."""
    h = hashlib.sha256()
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(files):
            full = os.path.join(base, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            h.update(("%s %s\n" % (rel, sha256_file(full))).encode("utf-8"))
    return h.hexdigest()


def locate_engine():
    """Return engine info. Prefers the verified archive; falls back to the
    unpacked folder only when the archive is absent, and says so."""
    if os.path.isfile(SUBMISSION_ZIP):
        digest = sha256_file(SUBMISSION_ZIP)
        verified = digest == SUBMISSION_SHA256
        target = os.path.join(CACHE, digest[:16])
        if not os.path.isfile(os.path.join(target, ".complete")):
            if os.path.isdir(target):
                shutil.rmtree(target)
            os.makedirs(target)
            with zipfile.ZipFile(SUBMISSION_ZIP) as z:
                z.extractall(target)
            open(os.path.join(target, ".complete"), "w").close()
        root = None
        for base, _dirs, files in os.walk(target):
            if "marketplace.json" in files:
                root = base
                break
        if root is None:
            raise SystemExit("submission.zip contains no marketplace.json")
        return {"source": "submission.zip", "sha256": digest, "verified": verified,
                "root": root, "skills": os.path.join(root, "skills")}
    if os.path.isfile(os.path.join(UNPACKED_FALLBACK, "marketplace.json")):
        return {"source": "brand-ai-readiness-audit/ (archive not found)", "sha256": None,
                "verified": False, "root": UNPACKED_FALLBACK,
                "skills": os.path.join(UNPACKED_FALLBACK, "skills")}
    raise SystemExit("No engine found: expected submission.zip at the repository root.")


def find_claude():
    """A Claude Code binary, if one is installed. Order: $CLAUDE_BIN, PATH,
    then the binary bundled with the VS Code extension (newest version)."""
    env = os.environ.get("CLAUDE_BIN")
    if env and os.path.isfile(env):
        return env
    on_path = shutil.which("claude")
    if on_path:
        return on_path
    exe = "claude.exe" if os.name == "nt" else "claude"
    pattern = os.path.join(os.path.expanduser("~"), ".vscode", "extensions",
                           "anthropic.claude-code-*", "resources", "native-binary", exe)

    def version_key(p):
        m = re.search(r"claude-code-(\d+)\.(\d+)\.(\d+)", p)
        return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)

    found = sorted(glob.glob(pattern), key=version_key)
    return found[-1] if found else None


def claude_version(binary):
    try:
        out = subprocess.run([binary, "--version"], capture_output=True, text=True,
                             timeout=30, encoding="utf-8", errors="replace")
        raw = (out.stdout or out.stderr).strip().splitlines()[0]
    except Exception:
        return None
    m = re.match(r"^(\d+\.\d+\.\d+)\s*\(Claude Code\)", raw)
    return "Claude Code %s" % m.group(1) if m else raw


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

JOBS = {}              # run id -> live meta dict (while the server runs)
PROCS = {}             # run id -> Popen, for cancellation
LOCK = threading.Lock()


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalise_url(raw):
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Enter a URL or domain.")
    if not re.match(r"^[a-z][a-z0-9+.-]*://", raw, re.I):
        raw = "https://" + raw
    u = urllib.parse.urlparse(raw)
    if u.scheme not in ("http", "https"):
        raise ValueError("Only http and https URLs can be audited.")
    if not u.netloc or " " in raw:
        raise ValueError("That does not look like a URL.")
    return urllib.parse.urlunparse((u.scheme, u.netloc, u.path or "/", "", u.query, ""))


def new_run_id(host):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^a-z0-9.-]", "-", host.lower())[:60] or "site"
    return "%s-%s-%04x" % (stamp, slug, random.randint(0, 0xFFFF))


def run_dir(run_id):
    if not RUN_ID_RE.match(run_id or ""):
        raise KeyError(run_id)
    return os.path.join(RUNS, run_id)


def save_meta(meta):
    d = run_dir(meta["id"])
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, "meta.json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    os.replace(tmp, os.path.join(d, "meta.json"))


def load_meta(run_id):
    with LOCK:
        if run_id in JOBS:
            return JOBS[run_id]
    path = os.path.join(run_dir(run_id), "meta.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise KeyError(run_id)


def log(meta, text, kind="log", **extra):
    entry = {"t": round(time.time() - meta["_t0"], 1), "kind": kind, "text": text}
    entry.update(extra)
    with LOCK:
        meta["log"].append(entry)
        if len(meta["log"]) > LOG_CAP:
            del meta["log"][: len(meta["log"]) - LOG_CAP]


def set_stage(meta, stage, **extra):
    with LOCK:
        meta["stage"] = stage
        meta.update(extra)
    save_meta(meta)


def kill_tree(proc):
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                       capture_output=True)
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            proc.terminate()


def child_env():
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def popen(meta, cmd, cwd):
    kwargs = dict(cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                  text=True, encoding="utf-8", errors="replace", env=child_env(), bufsize=1)
    if os.name != "nt":
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kwargs)
    with LOCK:
        PROCS[meta["id"]] = proc
    return proc


def cancelled(meta):
    return meta.get("status") == "cancelled"


# --- engine mode ------------------------------------------------------------

def run_engine(meta, engine):
    d = run_dir(meta["id"])
    scripts = engine["skills"]
    py = sys.executable
    today = datetime.date.today().isoformat()
    host = urllib.parse.urlparse(meta["url"]).netloc

    set_stage(meta, "crawl")
    log(meta, "Collecting evidence from %s (up to %d pages)" % (meta["url"], meta["max_pages"]),
        kind="stage")
    proc = popen(meta, [py, os.path.join(scripts, "audit-orchestrator", "scripts", "run_audit.py"),
                        meta["url"], "--out", "raw_findings.json",
                        "--evidence-out", "evidence.json", "--today", today,
                        "--max-pages", str(meta["max_pages"])], d)
    for line in proc.stdout:
        line = line.rstrip()
        if not line:
            continue
        log(meta, line)
        m = re.search(r"\[orchestrator\] collected (\d+) page", line)
        if m:
            set_stage(meta, "analyze", pages=int(m.group(1)))
        m = re.search(r"\[orchestrator\] ([a-z-]+): (\d+) finding", line)
        if m and m.group(1) in ANALYZERS:
            with LOCK:
                meta["analyzers"][m.group(1)] = int(m.group(2))
        m = re.search(r"\[orchestrator\] ([a-z-]+) FAILED", line)
        if m and m.group(1) in ANALYZERS:
            with LOCK:
                meta["analyzers"][m.group(1)] = "failed"
        if "not crawlable" in line:
            with LOCK:
                meta["short_circuited"] = True
    proc.wait()
    if cancelled(meta):
        return
    if proc.returncode != 0 or not os.path.isfile(os.path.join(d, "raw_findings.json")):
        raise RuntimeError("Evidence collection failed (exit %s). See the log." % proc.returncode)

    set_stage(meta, "critic")
    log(meta, "Adjudicating findings with evidence-critic", kind="stage")
    proc = popen(meta, [py, os.path.join(scripts, "evidence-critic", "scripts", "critique_findings.py"),
                        "--findings", "raw_findings.json", "--evidence", "evidence.json",
                        "--out", "adjudicated.json"], d)
    for line in proc.stdout:
        if line.strip():
            log(meta, line.rstrip())
    proc.wait()
    if cancelled(meta):
        return
    if proc.returncode != 0:
        raise RuntimeError("The evidence critic failed (exit %s)." % proc.returncode)

    set_stage(meta, "report")
    log(meta, "Finalizing report", kind="stage")
    proc = popen(meta, [py, os.path.join(scripts, "audit-orchestrator", "scripts", "finalize_report.py"),
                        "adjudicated.json", "--site", host, "--evidence", "evidence.json",
                        "--out", "audit_report.json", "--md", "audit_report.md"], d)
    out = proc.stdout.read()
    proc.wait()
    if proc.returncode != 0 or not os.path.isfile(os.path.join(d, "audit_report.json")):
        for line in out.splitlines()[-10:]:
            log(meta, line)
        raise RuntimeError("Report finalization failed (exit %s)." % proc.returncode)


# --- agent mode -------------------------------------------------------------

def describe_tool(name, inp):
    inp = inp or {}
    if name == "Skill":
        return "Invoked skill: %s" % inp.get("skill", "?")
    if name in ("Bash", "PowerShell"):
        return (inp.get("command") or "").strip().splitlines()[0][:220]
    if name in ("Read", "Write", "Edit"):
        return os.path.basename(inp.get("file_path", "") or "")
    if name == "WebSearch":
        return inp.get("query", "")
    if name in ("Glob", "Grep"):
        return inp.get("pattern", "")
    return json.dumps(inp)[:200]


def run_agent(meta, engine, binary):
    d = run_dir(meta["id"])
    ws = os.path.join(d, "workspace")
    skills_dst = os.path.join(ws, ".claude", "skills")
    shutil.copytree(engine["skills"], skills_dst, ignore=shutil.ignore_patterns("__pycache__"))
    os.makedirs(os.path.join(ws, "audit_out"), exist_ok=True)
    before = tree_digest(skills_dst)
    with LOCK:
        meta["engine_digest_before"] = before

    set_stage(meta, "agent")
    log(meta, "Starting %s with model %s" % (meta.get("harness") or "Claude Code", meta["model"]),
        kind="stage")
    cmd = [binary, "-p", AGENT_PROMPT.format(url=meta["url"]), "--model", meta["model"],
           "--allowedTools"] + AGENT_TOOLS + ["--output-format", "stream-json", "--verbose"]
    proc = popen(meta, cmd, ws)
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            log(meta, line[:300])
            continue
        etype = ev.get("type")
        if etype == "system" and ev.get("subtype") == "init":
            skills = [s for s in (ev.get("skills") or []) if s in ANALYZERS + ["audit-orchestrator", "evidence-critic"]]
            log(meta, "Harness ready. Marketplace skills discovered: %d" % len(skills), kind="stage")
        msg = ev.get("message") if isinstance(ev.get("message"), dict) else {}
        for c in msg.get("content") or []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                name = c.get("name", "?")
                log(meta, describe_tool(name, c.get("input")), kind="tool", tool=name)
                if name == "Skill":
                    set_stage(meta, "agent")
            elif c.get("type") == "text" and etype == "assistant":
                text = (c.get("text") or "").strip()
                if text:
                    log(meta, text[:600], kind="thought")
            elif c.get("type") == "tool_result" and c.get("is_error"):
                log(meta, str(c.get("content"))[:300], kind="error")
        if etype == "result":
            with LOCK:
                meta["agent_summary"] = ev.get("result") or ""
                meta["agent_cost_usd"] = ev.get("total_cost_usd")
    proc.wait()
    if cancelled(meta):
        return

    after = tree_digest(skills_dst)
    with LOCK:
        meta["engine_unchanged"] = before == after
    if before != after:
        log(meta, "WARNING: the skills in the agent workspace changed during the run.", kind="error")

    out = os.path.join(ws, "audit_out")
    copied = []
    for name in sorted(os.listdir(out)):
        if name.lower().endswith((".json", ".md")):
            target = name
            if name.startswith("adjudicated") and name.endswith(".json"):
                target = "adjudicated.json"
            shutil.copy2(os.path.join(out, name), os.path.join(d, target))
            copied.append(name)
    log(meta, "Collected from audit_out: %s" % (", ".join(copied) or "nothing"), kind="stage")
    if not os.path.isfile(os.path.join(d, "audit_report.json")):
        raise RuntimeError("The agent finished without writing audit_out/audit_report.json.")


# --- job wrapper ------------------------------------------------------------

def job(meta, engine, binary):
    try:
        if meta["mode"] == "agent":
            run_agent(meta, engine, binary)
        else:
            run_engine(meta, engine)
        if cancelled(meta):
            log(meta, "Run cancelled.", kind="error")
        else:
            with LOCK:
                meta["status"] = "done"
            log(meta, "Audit complete.", kind="stage")
    except Exception as e:
        with LOCK:
            meta["status"] = "failed"
            meta["error"] = str(e)
        log(meta, str(e), kind="error")
    finally:
        with LOCK:
            meta["finished_at"] = now_iso()
            meta["stage"] = "done" if meta["status"] == "done" else meta["stage"]
            PROCS.pop(meta["id"], None)
        save_meta(meta)
        with LOCK:
            JOBS.pop(meta["id"], None)


def start_run(url, mode, max_pages, model, engine, agent):
    url = normalise_url(url)
    if mode not in ("engine", "agent"):
        raise ValueError("Unknown mode.")
    if mode == "agent" and not agent.get("available"):
        raise ValueError("Agent mode needs Claude Code. Set CLAUDE_BIN or install the claude CLI.")
    with LOCK:
        active = sum(1 for m in JOBS.values() if m.get("status") == "running")
    if active >= MAX_CONCURRENT:
        raise ValueError("Two audits are already running. Wait for one to finish.")
    host = urllib.parse.urlparse(url).netloc
    meta = {
        "id": new_run_id(host), "url": url, "site": host, "mode": mode,
        "status": "running", "stage": "queued", "started_at": now_iso(),
        "finished_at": None, "max_pages": max(3, min(int(max_pages or 15), 15)),
        "model": (model or DEFAULT_MODEL) if mode == "agent" else None,
        "harness": agent.get("version") if mode == "agent" else None,
        "engine_sha256": engine["sha256"], "engine_verified": engine["verified"],
        "analyzers": {}, "log": [], "_t0": time.time(),
    }
    save_meta(meta)
    with LOCK:
        JOBS[meta["id"]] = meta
    threading.Thread(target=job, args=(meta, engine, agent.get("bin")), daemon=True).start()
    return meta["id"]


def cancel_run(run_id):
    with LOCK:
        meta = JOBS.get(run_id)
        proc = PROCS.get(run_id)
    if not meta:
        raise ValueError("That run is not active.")
    with LOCK:
        meta["status"] = "cancelled"
    if proc:
        kill_tree(proc)
    save_meta(meta)


def recover_interrupted():
    """Runs left 'running' by a previous server process can never finish."""
    if not os.path.isdir(RUNS):
        return
    for rid in os.listdir(RUNS):
        path = os.path.join(RUNS, rid, "meta.json")
        try:
            with open(path, encoding="utf-8") as fh:
                meta = json.load(fh)
        except Exception:
            continue
        if meta.get("status") == "running":
            meta["status"] = "interrupted"
            meta["error"] = "The server stopped before this run finished."
            save_meta(meta)


_SUMMARY_CACHE = {}


def run_summary(run_id):
    """Headline numbers for the history list, cached on report mtime."""
    path = os.path.join(run_dir(run_id), "audit_report.json")
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    hit = _SUMMARY_CACHE.get(run_id)
    if hit and hit[0] == mtime:
        return hit[1]
    try:
        with open(path, encoding="utf-8") as fh:
            r = json.load(fh)
        s = r.get("summary", {})
        out = {"score": (r.get("readiness") or {}).get("overall"),
               "critical": s.get("critical", 0), "high": s.get("high", 0),
               "medium": s.get("medium", 0), "low": s.get("low", 0),
               "total": s.get("total_findings", len(r.get("findings", [])))}
    except Exception:
        out = None
    _SUMMARY_CACHE[run_id] = (mtime, out)
    return out


def list_runs():
    out = []
    if not os.path.isdir(RUNS):
        return out
    for rid in os.listdir(RUNS):
        try:
            meta = load_meta(rid)
        except Exception:
            continue
        row = {k: v for k, v in meta.items() if k not in ("log", "_t0", "agent_summary")}
        row["summary"] = run_summary(rid)
        out.append(row)
    out.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    return out


def import_report(body):
    report = body.get("report")
    if not isinstance(report, dict) or "findings" not in report or "summary" not in report:
        raise ValueError("That file is not an audit report: it needs 'summary' and 'findings'.")
    site = report.get("site") or report["summary"].get("site") or "imported"
    host = urllib.parse.urlparse(site).netloc or site
    meta = {
        "id": new_run_id(host + "-imported"), "url": site, "site": host, "mode": "imported",
        "status": "done", "stage": "done", "started_at": report.get("audited_at") or now_iso(),
        "finished_at": now_iso(), "label": (body.get("name") or "")[:120],
        "source_dir": (body.get("source_dir") or None),
        "engine_sha256": None, "engine_verified": None, "analyzers": {}, "log": [],
    }
    d = run_dir(meta["id"])
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "audit_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    if isinstance(body.get("evidence"), dict):
        with open(os.path.join(d, "evidence.json"), "w", encoding="utf-8") as fh:
            json.dump(body["evidence"], fh)
    if isinstance(body.get("markdown"), str):
        with open(os.path.join(d, "audit_report.md"), "w", encoding="utf-8") as fh:
            fh.write(body["markdown"])
    save_meta(meta)
    return meta["id"]


def read_output_dir(path):
    """Build an import body from an audit output folder, such as the
    audit_out/ an agent session writes. Only audit_report.json is required."""
    path = os.path.abspath(path)
    report_path = os.path.join(path, "audit_report.json")
    if not os.path.isfile(report_path):
        raise ValueError("No audit_report.json in %s" % path)
    body = {"source_dir": path, "name": "audit_report.json"}
    with open(report_path, encoding="utf-8") as fh:
        body["report"] = json.load(fh)
    ev = os.path.join(path, "evidence.json")
    if os.path.isfile(ev):
        with open(ev, encoding="utf-8") as fh:
            body["evidence"] = json.load(fh)
    md = os.path.join(path, "audit_report.md")
    if os.path.isfile(md):
        with open(md, encoding="utf-8") as fh:
            body["markdown"] = fh.read()
    return body


def open_in_running_server(port, body):
    """--open while another GUI already owns the port: hand it the report."""
    import urllib.request
    req = urllib.request.Request(
        "http://127.0.0.1:%d/api/import" % port, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Audit-GUI": "1"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)["id"]


def delete_run(run_id):
    with LOCK:
        if run_id in JOBS:
            raise ValueError("Cancel the run before deleting it.")
    d = run_dir(run_id)
    if not os.path.isdir(d):
        raise KeyError(run_id)
    shutil.rmtree(d)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

CONTENT_TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
                 ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml",
                 ".json": "application/json; charset=utf-8", ".md": "text/markdown; charset=utf-8"}


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "BrandAuditGUI/1.0"
    engine = None
    agent = None
    allowed_hosts = set()

    def log_message(self, fmt, *args):
        pass

    # --- helpers --------------------------------------------------------
    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj))

    def _error(self, code, message):
        self._json(code, {"error": message})

    def _host_ok(self):
        return (self.headers.get("Host") or "").lower() in self.allowed_hosts

    def _write_ok(self):
        # A custom header cannot be sent cross-origin without a CORS preflight,
        # which this server never grants, so this blocks drive-by requests.
        return self._host_ok() and self.headers.get("X-Audit-GUI") == "1"

    def _body(self, limit=25 * 1024 * 1024):
        n = int(self.headers.get("Content-Length") or 0)
        if n > limit:
            raise ValueError("Request too large.")
        raw = self.rfile.read(n) if n else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def _file(self, path, ctype=None, download=None):
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return self._error(404, "Not found.")
        ctype = ctype or CONTENT_TYPES.get(os.path.splitext(path)[1], "application/octet-stream")
        extra = {"Content-Disposition": 'attachment; filename="%s"' % download} if download else None
        self._send(200, data, ctype, extra)

    # --- routes ---------------------------------------------------------
    def do_GET(self):
        if not self._host_ok():
            return self._error(403, "Forbidden host.")
        path = urllib.parse.urlparse(self.path).path
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        try:
            if path in ("/", "/index.html"):
                return self._file(os.path.join(STATIC, "index.html"))
            if path.startswith("/static/"):
                rel = os.path.normpath(path[len("/static/"):])
                full = os.path.join(STATIC, rel)
                if rel.startswith("..") or not os.path.abspath(full).startswith(os.path.abspath(STATIC)):
                    return self._error(404, "Not found.")
                return self._file(full)
            if path == "/api/meta":
                e = self.engine
                return self._json(200, {
                    "engine": {"source": e["source"], "sha256": e["sha256"],
                               "verified": e["verified"], "expected": SUBMISSION_SHA256},
                    "agent": {"available": self.agent["available"],
                              "version": self.agent.get("version"),
                              "default_model": DEFAULT_MODEL},
                    "today": datetime.date.today().isoformat()})
            if path == "/api/runs":
                return self._json(200, {"runs": list_runs()})
            m = re.match(r"^/api/runs/([^/]+)$", path)
            if m:
                meta = load_meta(m.group(1))
                since = int((query.get("since") or ["0"])[0])
                with LOCK:
                    out = {k: v for k, v in meta.items() if k != "_t0"}
                    out["log"] = list(meta.get("log", []))[since:]
                    out["log_total"] = len(meta.get("log", []))
                out["summary"] = run_summary(m.group(1))
                out["files"] = [f for f in RUN_FILES
                                if os.path.isfile(os.path.join(run_dir(m.group(1)), f))]
                return self._json(200, out)
            m = re.match(r"^/api/runs/([^/]+)/(report|evidence)$", path)
            if m:
                name = "audit_report.json" if m.group(2) == "report" else "evidence.json"
                return self._file(os.path.join(run_dir(m.group(1)), name))
            m = re.match(r"^/api/runs/([^/]+)/download/([a-z_.]+)$", path)
            if m and m.group(2) in RUN_FILES:
                meta = load_meta(m.group(1))
                stem = re.sub(r"[^A-Za-z0-9.-]", "_", meta.get("site") or "site")
                return self._file(os.path.join(run_dir(m.group(1)), m.group(2)),
                                  download="%s_%s" % (stem, m.group(2)))
            return self._error(404, "Not found.")
        except KeyError:
            return self._error(404, "No such run.")
        except (OSError, ValueError) as e:
            return self._error(400, str(e))

    def do_POST(self):
        if not self._write_ok():
            return self._error(403, "Forbidden.")
        path = urllib.parse.urlparse(self.path).path
        try:
            body = self._body()
            if path == "/api/runs":
                rid = start_run(body.get("url"), body.get("mode", "engine"),
                                body.get("max_pages", 15), body.get("model"),
                                self.engine, self.agent)
                return self._json(201, {"id": rid})
            if path == "/api/import":
                return self._json(201, {"id": import_report(body)})
            m = re.match(r"^/api/runs/([^/]+)/cancel$", path)
            if m:
                cancel_run(m.group(1))
                return self._json(200, {"ok": True})
            return self._error(404, "Not found.")
        except KeyError:
            return self._error(404, "No such run.")
        except (ValueError, json.JSONDecodeError) as e:
            return self._error(400, str(e))

    def do_DELETE(self):
        if not self._write_ok():
            return self._error(403, "Forbidden.")
        m = re.match(r"^/api/runs/([^/]+)$", urllib.parse.urlparse(self.path).path)
        if not m:
            return self._error(404, "Not found.")
        try:
            delete_run(m.group(1))
            return self._json(200, {"ok": True})
        except KeyError:
            return self._error(404, "No such run.")
        except ValueError as e:
            return self._error(409, str(e))


class Server(http.server.ThreadingHTTPServer):
    # On Windows, SO_REUSEADDR lets a second process bind a port that is
    # already listening, so two GUIs would silently share 8765. Refuse it there;
    # a busy port must fail so --open can hand the report to the running GUI.
    allow_reuse_address = os.name != "nt"
    daemon_threads = True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--open", metavar="DIR",
                    help="import an audit output folder (e.g. demo/audit_out) and open it")
    args = ap.parse_args()

    open_body = None
    if args.open:
        try:
            open_body = read_output_dir(args.open)
        except (ValueError, OSError) as e:
            raise SystemExit("--open: %s" % e)

    engine = locate_engine()
    binary = find_claude()
    agent = {"available": bool(binary), "bin": binary,
             "version": claude_version(binary) if binary else None}
    os.makedirs(RUNS, exist_ok=True)
    recover_interrupted()

    Handler.engine = engine
    Handler.agent = agent
    Handler.allowed_hosts = {"%s:%d" % (h, args.port) for h in ("127.0.0.1", "localhost", args.host)}

    url = "http://127.0.0.1:%d/" % args.port
    try:
        httpd = Server((args.host, args.port), Handler)
    except OSError:
        if open_body is None:
            raise SystemExit("Port %d is in use. Is the GUI already running? Try --port." % args.port)
        rid = open_in_running_server(args.port, open_body)
        target = "%s#/run/%s/overview" % (url, rid)
        print("The GUI is already running; opened the report there: %s" % target, flush=True)
        if not args.no_browser:
            webbrowser.open(target)
        return
    if open_body is not None:
        rid = import_report(open_body)
        url = "%s#/run/%s/overview" % (url, rid)
        print("opened : %s" % open_body["source_dir"], flush=True)
    state = "verified" if engine["verified"] else "NOT VERIFIED"
    print("engine : %s (%s)" % (engine["source"], state), flush=True)
    if engine["sha256"]:
        print("sha256 : %s" % engine["sha256"], flush=True)
    print("agent  : %s" % (agent["version"] or "unavailable (engine mode only)"), flush=True)
    print("open   : %s   (Ctrl+C to stop)" % url, flush=True)
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        with LOCK:
            procs = list(PROCS.values())
        for p in procs:
            kill_tree(p)
        httpd.server_close()


if __name__ == "__main__":
    main()
