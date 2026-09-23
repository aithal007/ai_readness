/* Brand AI-Readiness Audit - local GUI.
   Plain JavaScript, no dependencies. Every string that originates in a report
   or a crawled page is escaped before it reaches the DOM: reports quote text
   scraped from arbitrary websites. */
(function () {
  "use strict";

  // --- constants ------------------------------------------------------------
  var SEV = ["critical", "high", "medium", "low"];
  var SEV_RANK = { critical: 0, high: 1, medium: 2, low: 3 };
  var EFFORT_RANK = { quick: 0, moderate: 1, project: 2 };
  var PILLARS = [
    { key: "crawl_access", label: "Reachable", q: "Can a crawler reach and read the page?", skills: ["crawl-render-audit"] },
    { key: "machine_readable", label: "Readable", q: "Is it clear who this is, and does markup agree?", skills: ["crawl-render-audit", "structured-data-entity-audit"] },
    { key: "citability", label: "Quotable", q: "Is it the kind of page answer engines quote?", skills: ["ai-citability-audit"] },
    { key: "answerability", label: "Answerable", q: "Can real questions be answered from it?", skills: ["answerability-probe"] },
    { key: "trust_freshness", label: "Current & corroborated", q: "Is it current, consistent and corroborated?", skills: ["freshness-corroboration-audit"] },
    { key: "engagement", label: "Engaging", q: "Does a visitor orient and act?", skills: ["engagement-audit"] }
  ];
  var SKILL_NAMES = {
    "crawl-render-audit": "Crawl & render",
    "structured-data-entity-audit": "Structured data & entity",
    "ai-citability-audit": "AI citability",
    "answerability-probe": "Answerability",
    "freshness-corroboration-audit": "Freshness & corroboration",
    "engagement-audit": "Engagement",
    "audit-orchestrator": "Orchestrator",
    "evidence-critic": "Evidence critic"
  };
  var ANALYZERS = ["crawl-render-audit", "structured-data-entity-audit", "ai-citability-audit",
    "answerability-probe", "freshness-corroboration-audit", "engagement-audit"];
  var IMPACT = {
    removes: { text: "Removes citations", cls: "removes" },
    intent: { text: "Blocks live answers", cls: "intent" },
    none: { text: "None (training only)", cls: "none" }
  };
  var TABS = [
    { key: "overview", label: "Overview" },
    { key: "findings", label: "Findings" },
    { key: "roadmap", label: "Roadmap" },
    { key: "evidence", label: "Evidence" },
    { key: "review", label: "Review" },
    { key: "compare", label: "Compare" },
    { key: "markdown", label: "Markdown" }
  ];

  // --- state ----------------------------------------------------------------
  var S = {
    meta: null,          // /api/meta
    runs: [],            // history rows
    runId: null,
    run: null,           // run meta incl. log
    report: null,
    evidence: null,
    evidenceLoaded: false,
    markdown: null,
    tab: "overview",
    filters: { q: "", sev: { critical: true, high: true, medium: true, low: true }, pillar: "", skill: "", sort: "severity" },
    compareWith: "",
    compareReport: null,
    pollTimer: null,
    historyTimer: null,
    tickTimer: null
  };

  // --- helpers --------------------------------------------------------------
  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  function h(v) {
    return String(v === null || v === undefined ? "" : v)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function safeUrl(u) {
    return /^https?:\/\//i.test(String(u || "")) ? h(u) : "#";
  }
  function icon(name) {
    var p = {
      info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
      check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
      chev: '<path d="M6 9l6 6 6-6"/>',
      search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
      download: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
      trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
      stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
      retry: '<path d="M4 12a8 8 0 1 0 3-6.2M4 4v5h5"/>',
      shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
      sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
      moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
      ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>'
    }[name] || "";
    return '<svg viewBox="0 0 24 24" aria-hidden="true">' + p + "</svg>";
  }
  function sevBadge(sev) {
    sev = SEV.indexOf(sev) >= 0 ? sev : "low";
    return '<span class="sev ' + sev + '"><i aria-hidden="true"></i>' + sev + "</span>";
  }
  function fmtDate(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d)) return h(iso);
    return d.toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }
  function ago(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return "";
    var s = Math.max(0, (Date.now() - d.getTime()) / 1000);
    if (s < 60) return "just now";
    if (s < 3600) return Math.floor(s / 60) + " min ago";
    if (s < 86400) return Math.floor(s / 3600) + " h ago";
    return Math.floor(s / 86400) + " d ago";
  }
  function fmtElapsed(sec) {
    sec = Math.max(0, Math.floor(sec));
    var m = Math.floor(sec / 60), s = sec % 60;
    return m + ":" + (s < 10 ? "0" : "") + s;
  }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : (many || one + "s")); }
  function skillName(s) { return SKILL_NAMES[s] || s || "Agent"; }
  function toast(msg) {
    var t = $("#toast");
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { t.hidden = true; }, 3600);
  }

  function api(method, path, body) {
    var opt = { method: method, headers: { "X-Audit-GUI": "1" } };
    if (body !== undefined) {
      opt.headers["Content-Type"] = "application/json";
      opt.body = JSON.stringify(body);
    }
    return fetch(path, opt).then(function (r) {
      var ct = r.headers.get("Content-Type") || "";
      var p = ct.indexOf("json") >= 0 ? r.json() : r.text();
      return p.then(function (data) {
        if (!r.ok) throw new Error((data && data.error) || ("HTTP " + r.status));
        return data;
      });
    });
  }

  // --- theme ----------------------------------------------------------------
  function storedTheme() { try { return localStorage.getItem("bra-theme"); } catch (e) { return null; } }
  function applyTheme(t) {
    if (t) document.documentElement.setAttribute("data-theme", t);
    else document.documentElement.removeAttribute("data-theme");
    var dark = t ? t === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    $("#theme-toggle").innerHTML = icon(dark ? "sun" : "moon");
  }
  $("#theme-toggle").addEventListener("click", function () {
    var cur = document.documentElement.getAttribute("data-theme");
    var dark = cur ? cur === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    var next = dark ? "light" : "dark";
    try { localStorage.setItem("bra-theme", next); } catch (e) { /* storage blocked */ }
    applyTheme(next);
  });
  applyTheme(storedTheme());

  // --- sidebar (narrow screens) --------------------------------------------
  $("#nav-toggle").addEventListener("click", function () {
    var open = $("#sidebar").classList.toggle("open");
    this.setAttribute("aria-expanded", open ? "true" : "false");
  });
  function closeNav() {
    $("#sidebar").classList.remove("open");
    $("#nav-toggle").setAttribute("aria-expanded", "false");
  }

  // --- engine badge & form --------------------------------------------------
  function renderEngineBadge() {
    var e = S.meta.engine, b = $("#engine-badge");
    b.hidden = false;
    b.classList.toggle("warn", !e.verified);
    var sha = e.sha256 ? e.sha256.slice(0, 8) : "n/a";
    b.innerHTML = '<span class="dot" aria-hidden="true"></span>' +
      '<span>Engine <span class="long">' + h(e.source) + " · </span>" +
      '<span class="mono">' + h(sha) + "</span> " + (e.verified ? "verified" : "unverified") + "</span>";
    b.title = e.verified
      ? "Running the frozen Round 3 package. SHA-256 " + e.sha256 + " matches the published hash."
      : "The engine could not be verified against the published SHA-256 " + e.expected + ".";
  }

  function setupForm() {
    var agent = S.meta.agent;
    var opt = $("#agent-option");
    if (!agent.available) {
      opt.classList.add("disabled");
      opt.querySelector("input").disabled = true;
      opt.title = "Agent mode needs Claude Code. Install the claude CLI or set CLAUDE_BIN, then restart the GUI.";
    }
    $("#model-input").value = agent.default_model || "";
    $$('#mode-picker input').forEach(function (r) { r.addEventListener("change", updateModeHint); });
    updateModeHint();

    $("#new-audit").addEventListener("submit", function (ev) {
      ev.preventDefault();
      var mode = $('#mode-picker input:checked').value;
      startRun({
        url: $("#url-input").value,
        mode: mode,
        max_pages: parseInt($("#pages-input").value, 10),
        model: mode === "agent" ? $("#model-input").value.trim() : null
      }, $("#run-btn"), $("#form-error"), function () { $("#url-input").value = ""; });
    });
  }

  // One launcher for both the sidebar form and the landing search.
  function startRun(params, btn, err, onOk) {
    err.hidden = true;
    btn.disabled = true;
    api("POST", "/api/runs", params).then(function (r) {
      if (onOk) onOk();
      closeNav();
      location.hash = "#/run/" + r.id;
      refreshHistory();
    }).catch(function (e) {
      err.textContent = e.message;
      err.hidden = false;
    }).then(function () { btn.disabled = false; });
  }

  function ring(score, size, stroke) {
    var r = (size - stroke) / 2, c = 2 * Math.PI * r;
    var has = typeof score === "number";
    var off = has ? c * (1 - Math.max(0, Math.min(100, score)) / 100) : c;
    return '<svg viewBox="0 0 ' + size + " " + size + '" aria-hidden="true">' +
      '<circle class="trk" cx="' + size / 2 + '" cy="' + size / 2 + '" r="' + r + '" fill="none"/>' +
      '<circle class="val" cx="' + size / 2 + '" cy="' + size / 2 + '" r="' + r + '" fill="none" stroke-linecap="round" ' +
      'stroke-dasharray="' + c.toFixed(2) + '" stroke-dashoffset="' + off.toFixed(2) + '" data-target="' + off.toFixed(2) + '" data-full="' + c.toFixed(2) + '"/></svg>';
  }

  function shortPath(p) {
    p = String(p || "");
    var sep = p.indexOf("\\") >= 0 ? "\\" : "/";
    var parts = p.split(sep).filter(Boolean);
    return parts.length > 2 ? "…" + sep + parts.slice(-2).join(sep) : p;
  }

  function reducedMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function countUp(el, to) {
    if (!el || typeof to !== "number") return;
    if (reducedMotion()) { el.textContent = to; return; }
    var t0 = null, dur = 900;
    var step = function (ts) {
      if (t0 === null) t0 = ts;
      var p = Math.min(1, (ts - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(to * e);
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  function updateModeHint() {
    var mode = $('#mode-picker input:checked').value;
    var agent = S.meta.agent;
    $("#model-field").hidden = mode !== "agent";
    $("#mode-hint").textContent = mode === "agent"
      ? (agent.version || "Claude Code") + " drives the skill: judgement checks, web corroboration and a review of every finding. 2 to 7 minutes."
      : "Scripted pipeline. Deterministic, no LLM, about a minute.";
  }

  // --- history --------------------------------------------------------------
  function refreshHistory() {
    return api("GET", "/api/runs").then(function (d) {
      S.runs = d.runs || [];
      renderHistory();
      var busy = S.runs.some(function (r) { return r.status === "running"; });
      clearTimeout(S.historyTimer);
      if (busy) S.historyTimer = setTimeout(refreshHistory, 3000);
    }).catch(function () { /* server restarting */ });
  }

  function renderHistory() {
    var ul = $("#history-list");
    $("#history-count").textContent = S.runs.length ? String(S.runs.length) : "";
    if (!S.runs.length) {
      ul.innerHTML = '<li class="history-empty">No audits yet.</li>';
      return;
    }
    ul.innerHTML = S.runs.map(function (r) {
      var sm = r.summary, score;
      var hasScore = sm && typeof sm.score === "number";
      if (r.status === "running") score = '<span class="ring-mini"><span class="spinner" aria-label="running">' + icon("retry") + "</span></span>";
      else score = '<span class="ring-mini' + (hasScore ? "" : " na") + '">' + ring(hasScore ? sm.score : null, 42, 4) +
        "<b>" + (hasScore ? h(sm.score) : "&ndash;") + "</b></span>";
      var tag = r.mode === "agent" ? '<span class="tag agent">agent</span>'
        : r.mode === "imported" ? '<span class="tag">imported</span>' : '<span class="tag">engine</span>';
      var status = r.status === "running" ? '<span class="tag run">running</span>'
        : (r.status === "failed" || r.status === "cancelled" || r.status === "interrupted")
          ? '<span class="tag fail">' + h(r.status) + "</span>" : "";
      var counts = sm ? (sm.critical ? sm.critical + " crit · " : "") + (sm.high ? sm.high + " high · " : "") + plural(sm.total || 0, "finding") : "";
      return '<li><a class="history-item' + (r.id === S.runId ? " active" : "") + '" href="#/run/' + h(r.id) + '">' +
        score +
        '<span><span class="site">' + h(r.site || r.url) + "</span>" +
        '<span class="sub">' + tag + status + "<span>" + h(ago(r.started_at)) + "</span>" +
        (counts ? "<span>· " + h(counts) + "</span>" : "") + "</span></span></a></li>";
    }).join("");
  }

  // --- router ---------------------------------------------------------------
  function route() {
    var m = location.hash.match(/^#\/run\/([A-Za-z0-9._-]+)(?:\/([a-z]+))?/);
    stopPolling();
    if (!m) {
      S.runId = null;
      renderHistory();
      renderEmpty();
      return;
    }
    var id = m[1], tab = m[2];
    if (tab && TABS.some(function (t) { return t.key === tab; })) S.tab = tab;
    if (id !== S.runId) {
      S.runId = id;
      S.report = null; S.evidence = null; S.evidenceLoaded = false; S.markdown = null;
      S.compareWith = ""; S.compareReport = null;
      if (!tab) S.tab = "overview";
    }
    renderHistory();
    loadRun();
  }
  window.addEventListener("hashchange", route);

  function stopPolling() {
    clearTimeout(S.pollTimer);
    clearInterval(S.tickTimer);
  }

  function loadRun() {
    var id = S.runId;
    api("GET", "/api/runs/" + id).then(function (run) {
      if (id !== S.runId) return;
      S.run = run;
      if (run.status === "running") {
        renderRunning();
        poll();
      } else if (run.status === "done") {
        loadReport();
      } else {
        renderFailed();
      }
    }).catch(function (e) {
      $("#main").innerHTML = '<div class="banner">' + icon("info") + "<span>" + h(e.message) + "</span></div>";
    });
  }

  function loadReport() {
    var id = S.runId;
    if (S.report) { renderReport(); return; }
    api("GET", "/api/runs/" + id + "/report").then(function (rep) {
      if (id !== S.runId) return;
      S.report = rep;
      renderReport();
    }).catch(function (e) {
      $("#main").innerHTML = '<div class="banner">' + icon("info") + "<span>Could not load the report: " + h(e.message) + "</span></div>";
    });
  }

  // --- empty state ----------------------------------------------------------
  function renderEmpty() {
    var main = $("#main");
    main.innerHTML = "";
    main.appendChild($("#tpl-empty").content.cloneNode(true));
    $("#chain").innerHTML = PILLARS.map(function (p, i) {
      var skill = p.skills[p.skills.length - 1];
      return '<li><span class="n">' + (i + 1) + "</span><strong>" + h(p.label) + '</strong><span class="q">' + h(p.q) +
        '</span><span class="sk">' + h(skill) + "</span></li>";
    }).join("");
    document.title = "Brand AI-Readiness Audit";

    var agent = S.meta.agent;
    var opt = $("#hero-agent-option");
    if (!agent.available) {
      opt.classList.add("disabled");
      opt.querySelector("input").disabled = true;
      opt.title = "Agent mode needs Claude Code.";
    }
    var foot = function () {
      var mode = $('input[name="hero-mode"]:checked').value;
      $("#hero-foot").textContent = mode === "agent"
        ? (agent.version || "Claude Code") + " with " + agent.default_model + " drives the skills, including web corroboration and a review of every finding. 2 to 7 minutes."
        : "Scripted engine: deterministic, no LLM, about a minute. Frozen package " + (S.meta.engine.sha256 || "").slice(0, 8) + ", SHA-256 verified.";
    };
    $$('input[name="hero-mode"]').forEach(function (r) { r.addEventListener("change", foot); });
    foot();
    $("#hero-form").addEventListener("submit", function (ev) {
      ev.preventDefault();
      var mode = $('input[name="hero-mode"]:checked').value;
      startRun({ url: $("#hero-url").value, mode: mode, max_pages: 15, model: mode === "agent" ? agent.default_model : null },
        $("#hero-run"), $("#hero-error"));
    });
    setTimeout(function () { var u = $("#hero-url"); if (u && window.innerWidth > 900) u.focus(); }, 50);
  }

  // --- running --------------------------------------------------------------
  function runSteps(run) {
    var stageOrder, steps;
    if (run.mode === "agent") {
      var tools = (run._allLog || []).filter(function (l) { return l.kind === "tool"; });
      var saw = function (re) { return tools.some(function (l) { return re.test(l.text || ""); }); };
      var skill = tools.some(function (l) { return l.tool === "Skill"; });
      var crawl = saw(/run_audit\.py/), critic = saw(/critique_findings\.py/), fin = saw(/finalize_report\.py/);
      var done = run.status === "done";
      steps = [
        { label: "Load skill", sub: "audit-orchestrator entrypoint", state: skill ? "done" : "active" },
        { label: "Crawl & analyze", sub: "Evidence + six analyzers", state: critic || fin || done ? "done" : crawl ? "active" : skill ? "active" : "todo" },
        { label: "Judge & review", sub: "Corroboration, orientation, critic", state: fin || done ? "done" : critic ? "active" : "todo" },
        { label: "Report", sub: "Scores, roadmap, markdown", state: done ? "done" : fin ? "active" : "todo" }
      ];
      if (crawl && !critic && !fin) steps[0].state = "done";
      return steps;
    }
    stageOrder = ["crawl", "analyze", "critic", "report", "done"];
    var at = stageOrder.indexOf(run.stage);
    if (at < 0) at = 0;
    var st = function (i) { return run.status === "done" || at > i ? "done" : at === i ? "active" : "todo"; };
    return [
      { label: "Crawl", sub: run.pages ? plural(run.pages, "page") + " collected" : "Up to " + run.max_pages + " pages, robots.txt honoured", state: st(0) },
      { label: "Analyze", sub: "Six skills over one snapshot", state: st(1), analyzers: true },
      { label: "Critic", sub: "Drop, merge, recalibrate", state: st(2) },
      { label: "Report", sub: "Scores and roadmap", state: st(3) }
    ];
  }

  function renderSteps() {
    var run = S.run;
    var html = runSteps(run).map(function (s) {
      var extra = "";
      if (s.analyzers) {
        extra = '<div class="analyzers">' + ANALYZERS.map(function (a) {
          var v = run.analyzers && run.analyzers[a];
          var ok = v !== undefined && v !== "failed";
          return '<span class="' + (ok ? "ok" : "") + '" title="' + h(skillName(a)) + '">' +
            h(skillName(a)) + (ok ? " · " + h(v) : v === "failed" ? " · failed" : "") + "</span>";
        }).join("") + "</div>";
      }
      return '<li class="step ' + s.state + '"><div class="lbl"><span class="ic">' +
        (s.state === "done" ? icon("check") : "") + "</span>" + h(s.label) + "</div><p>" + h(s.sub) + "</p>" + extra + "</li>";
    }).join("");
    var el = $("#steps");
    if (el) el.innerHTML = html;
  }

  function consoleLine(l) {
    var cls = l.kind === "stage" ? "stage" : l.kind === "error" ? "error" : l.kind === "thought" ? "thought" : l.kind === "tool" ? "tool" : "";
    var body = l.kind === "tool"
      ? '<span class="tn ' + h(l.tool) + '">' + h(l.tool) + "</span>" + h(l.text)
      : h(l.text);
    return '<div class="ln ' + cls + '"><span class="ts">' + h(fmtElapsed(l.t || 0)) + "</span><span>" + body + "</span></div>";
  }

  function renderRunning() {
    var run = S.run;
    run._allLog = run.log || [];
    document.title = "Auditing " + (run.site || "") + " · Brand AI-Readiness Audit";
    var modeLine = run.mode === "agent"
      ? "Agent run · " + h(run.harness || "Claude Code") + " · model " + h(run.model)
      : "Engine run · scripted pipeline";
    $("#main").innerHTML =
      '<div class="run-head"><div><h1 style="font-size:22px;word-break:break-word">Auditing ' + h(run.site) + "</h1>" +
      '<div class="meta-line"><span>' + modeLine + "</span><span>" + h(run.url) + "</span></div></div>" +
      '<div style="display:flex;gap:12px;align-items:center"><div><div class="muted small">Elapsed</div><div class="elapsed" id="elapsed">0:00</div></div>' +
      '<button class="btn danger" id="cancel-btn">' + icon("stop") + "Cancel</button></div></div>" +
      '<ol class="steps" id="steps"></ol>' +
      '<div class="term"><div class="term-bar"><i></i><i></i><i></i><span>' +
      (run.mode === "agent" ? "agent activity · " + h(run.harness || "Claude Code") : "engine log · run_audit.py") +
      '</span><span class="live">live</span></div>' +
      '<div class="console" id="console" role="log" aria-live="polite">' + run._allLog.map(consoleLine).join("") + "</div></div>";
    renderSteps();
    var started = new Date(run.started_at).getTime();
    var tick = function () { var e = $("#elapsed"); if (e) e.textContent = fmtElapsed((Date.now() - started) / 1000); };
    tick();
    S.tickTimer = setInterval(tick, 1000);
    $("#cancel-btn").addEventListener("click", function () {
      if (!confirm("Cancel this audit?")) return;
      api("POST", "/api/runs/" + run.id + "/cancel").catch(function (e) { toast(e.message); });
    });
    var c = $("#console"); c.scrollTop = c.scrollHeight;
  }

  function poll() {
    var id = S.runId;
    S.pollTimer = setTimeout(function () {
      var since = (S.run && S.run._allLog) ? S.run._allLog.length : 0;
      api("GET", "/api/runs/" + id + "?since=" + since).then(function (run) {
        if (id !== S.runId) return;
        var all = (S.run._allLog || []).concat(run.log || []);
        var c = $("#console");
        if (c && run.log && run.log.length) {
          var stick = c.scrollHeight - c.scrollTop - c.clientHeight < 40;
          c.insertAdjacentHTML("beforeend", run.log.map(consoleLine).join(""));
          if (stick) c.scrollTop = c.scrollHeight;
        }
        run._allLog = all;
        S.run = run;
        renderSteps();
        if (run.status === "running") { poll(); return; }
        stopPolling();
        refreshHistory();
        if (run.status === "done") { toast("Audit complete: " + run.site); loadReport(); }
        else renderFailed();
      }).catch(function () { poll(); });
    }, 1200);
  }

  function renderFailed() {
    var run = S.run;
    document.title = run.site + " · " + run.status;
    $("#main").innerHTML =
      '<div class="run-head"><div><h1 style="font-size:22px">' + h(run.site) + "</h1>" +
      '<div class="meta-line"><span class="tag fail">' + h(run.status) + "</span><span>" + h(fmtDate(run.started_at)) + "</span><span>" + h(run.url) + "</span></div></div>" +
      '<div class="actions"><button class="btn" id="retry-btn">' + icon("retry") + 'Run again</button><button class="btn danger" id="del-btn">' + icon("trash") + "Delete</button></div></div>" +
      (run.error ? '<div class="banner">' + icon("info") + "<span>" + h(run.error) + "</span></div>" : "") +
      '<div class="term"><div class="term-bar"><i></i><i></i><i></i><span>log</span></div><div class="console">' +
      (run.log || []).map(consoleLine).join("") + "</div></div>";
    $("#retry-btn").addEventListener("click", function () { rerun(run); });
    $("#del-btn").addEventListener("click", function () { deleteRun(run); });
  }

  function rerun(run) {
    api("POST", "/api/runs", { url: run.url, mode: run.mode === "imported" ? "engine" : run.mode, max_pages: run.max_pages || 15, model: run.model })
      .then(function (r) { location.hash = "#/run/" + r.id; refreshHistory(); })
      .catch(function (e) { toast(e.message); });
  }
  function deleteRun(run) {
    if (!confirm("Delete this audit and its files?")) return;
    api("DELETE", "/api/runs/" + run.id).then(function () {
      location.hash = "#/";
      refreshHistory();
    }).catch(function (e) { toast(e.message); });
  }

  // --- report ---------------------------------------------------------------
  function findings() { return (S.report && S.report.findings) || []; }

  function renderReport() {
    var run = S.run, rep = S.report, sm = rep.summary || {};
    document.title = (run.site || rep.site) + " · Brand AI-Readiness Audit";
    var modeBadge = run.mode === "agent" ? '<span class="tag agent">agent-reviewed</span>'
      : run.mode === "imported" ? '<span class="tag">imported</span>' : '<span class="tag">engine only</span>';
    var scope = rep.audit_scope || {};
    var integrity = "";
    if (run.mode !== "imported" && run.engine_verified) {
      integrity = '<span title="Ran the frozen submission.zip, SHA-256 verified' +
        (run.mode === "agent" && run.engine_unchanged ? "; skills byte-identical after the agent run" : "") +
        '" style="display:inline-flex;gap:4px;align-items:center">' + icon("shield") + "engine verified" +
        (run.mode === "agent" && run.engine_unchanged ? " · unchanged" : "") + "</span>";
    }
    var files = run.files || [];
    var dl = function (name, label) {
      return files.indexOf(name) >= 0
        ? '<a class="btn sm" href="/api/runs/' + h(run.id) + "/download/" + name + '">' + icon("download") + h(label) + "</a>" : "";
    };
    var bannerHtml = "";
    if (run.mode === "engine") {
      bannerHtml = '<div class="banner">' + icon("info") + "<span><strong>Engine-only run.</strong> These are the scripted checks without the agent's judgement layer. " +
        "An agent run adds off-site corroboration, a reading of the homepage, and a review of every finding, which can raise or lower severities." +
        (S.meta.agent.available ? " Use <em>Agent</em> mode for that." : "") + "</span></div>";
    } else if (run.mode === "agent") {
      bannerHtml = '<div class="banner info">' + icon("info") + "<span><strong>Agent-reviewed run.</strong> " + h(run.harness || "Claude Code") +
        " driving the audit-orchestrator skill with model <span class=\"mono\">" + h(run.model) + "</span>. The agent's own summary is under Review.</span></div>";
    } else if (run.mode === "imported" && run.source_dir) {
      bannerHtml = '<div class="banner info">' + icon("info") + "<span><strong>Opened from a run's output folder.</strong> " +
        "These are the files that run wrote to <span class=\"mono\" title=\"" + h(run.source_dir) + "\">" + h(shortPath(run.source_dir)) + "</span>, shown unchanged.</span></div>";
    }

    var counts = { findings: findings().length, roadmap: ["now", "next", "later"].reduce(function (n, k) { return n + (((rep.roadmap || {})[k]) || []).length; }, 0) };
    $("#main").innerHTML =
      '<div class="report-head"><div><h1><a href="' + safeUrl(run.url || rep.site) + '" target="_blank" rel="noopener noreferrer">' + h(run.site || rep.site) + "</a></h1>" +
      '<div class="meta-line">' + modeBadge + "<span>" + h(fmtDate(rep.audited_at || run.started_at)) + "</span>" +
      (scope.pages_sampled ? "<span>" + plural(scope.pages_sampled, "page") + " sampled</span>" : "") +
      (scope.crawl_seconds ? "<span>crawl " + h(Math.round(scope.crawl_seconds)) + "s</span>" : "") + integrity + "</div></div>" +
      '<div class="actions">' + dl("audit_report.json", "JSON") + dl("audit_report.md", "Markdown") +
      (run.mode !== "imported" ? '<button class="btn sm" id="rerun-btn">' + icon("retry") + "Re-run</button>" : "") +
      '<button class="btn sm danger" id="del-btn" aria-label="Delete audit">' + icon("trash") + "</button></div></div>" +
      bannerHtml +
      '<nav class="tabs" role="tablist">' + TABS.map(function (t) {
        var c = counts[t.key] !== undefined ? '<span class="count">' + counts[t.key] + "</span>" : "";
        return '<button role="tab" data-tab="' + t.key + '" aria-selected="' + (S.tab === t.key) + '">' + h(t.label) + c + "</button>";
      }).join("") + "</nav>" +
      '<section id="tab-body"></section>';

    $$(".tabs button").forEach(function (b) {
      b.addEventListener("click", function () { setTab(b.getAttribute("data-tab")); });
    });
    var rr = $("#rerun-btn"); if (rr) rr.addEventListener("click", function () { rerun(run); });
    $("#del-btn").addEventListener("click", function () { deleteRun(run); });
    renderTab();
  }

  function setTab(key) {
    S.tab = key;
    history.replaceState(null, "", "#/run/" + S.runId + "/" + key);
    $$(".tabs button").forEach(function (b) { b.setAttribute("aria-selected", String(b.getAttribute("data-tab") === key)); });
    renderTab();
  }

  function renderTab() {
    var body = $("#tab-body");
    if (!body) return;
    body.classList.remove("fade-in");
    void body.offsetWidth;
    body.classList.add("fade-in");
    ({ overview: tabOverview, findings: tabFindings, roadmap: tabRoadmap, evidence: tabEvidence,
      review: tabReview, compare: tabCompare, markdown: tabMarkdown }[S.tab] || tabOverview)(body);
  }

  // --- overview -------------------------------------------------------------
  function pillarFindings(p) {
    return findings().filter(function (f) {
      var s = f.source_skill || "";
      return p.skills.some(function (k) { return s.indexOf(k) >= 0; });
    });
  }

  function tabOverview(body) {
    var rep = S.report, rd = rep.readiness || {}, sm = rep.summary || {};
    var scored = rd.overall !== null && rd.overall !== undefined;
    var hero = '<div class="gauge" role="img" aria-label="' + (scored ? "Readiness " + h(rd.overall) + " out of 100" : "Not scored") + '">' +
      ring(scored ? 0 : null, 184, 14) +
      '<div class="gauge-center">' + (scored
        ? '<span class="num" id="gauge-num">0</span><span class="of">out of 100</span>'
        : '<span class="num na">Not scored</span><span class="of">site could not be assessed</span>') + "</div></div>";
    var tiles = SEV.map(function (s) {
      var n = sm[s] || 0;
      return '<button class="sev-tile' + (n ? "" : " zero") + '" data-sev="' + s + '" title="Show ' + s + ' findings">' +
        sevBadge(s) + '<span class="n">' + n + "</span></button>";
    }).join("");
    var pillarRows = PILLARS.map(function (p) {
      var pd = (rd.pillars || {})[p.key] || {};
      var score = pd.score;
      var has = score !== null && score !== undefined;
      return '<button class="pillar-row" data-pillar="' + p.key + '">' +
        '<span class="pillar-name"><strong>' + h(pd.label || p.label) + "</strong><span>" + h(p.q) + "</span></span>" +
        '<span class="bar-track" aria-hidden="true"><span class="bar-fill" style="width:0%" data-w="' + (has ? Math.max(0, Math.min(100, score)) : 0) + '"></span></span>' +
        '<span class="pillar-score' + (has ? "" : " na") + '">' + (has ? h(score) : "n/a") + "</span></button>";
    }).join("");

    var now = ((rep.roadmap || {}).now || []).slice(0, 5);
    var fixFirst = now.length
      ? '<ul class="fix-list">' + now.map(function (r) {
        return "<li>" + sevBadge(r.severity) + '<div><div class="t">' + h(r.title) + '</div><div class="a">' + h(r.action) + "</div></div></li>";
      }).join("") + "</ul>"
      : '<p class="muted">Nothing in the do-now bucket.</p>';

    var scope = rep.audit_scope || {};
    var orient = scope.homepage_orientation;
    var offsite = scope.off_site_check;
    var scopeRows = [];
    if (scope.pages_sampled) scopeRows.push(["Pages sampled", plural(scope.pages_sampled, "page")]);
    if (scope.collected_at) scopeRows.push(["Collected", fmtDate(scope.collected_at)]);
    if (orient && orient.result) scopeRows.push(["Homepage orientation", orient.result]);
    if (offsite) scopeRows.push(["Off-site corroboration", offsite.ran ? (offsite.result || "ran") : "did not run"]);
    if (scope.crawler_reprobe) scopeRows.push(["Crawler re-probe", scope.crawler_reprobe]);
    if (scope.pages_note) scopeRows.push(["Note", scope.pages_note]);

    body.innerHTML =
      '<div class="overview-grid">' +
      '<div class="card hero"><div><div class="hero-label">AI readiness</div>' + hero + "</div>" +
      weakestHtml(rd) +
      '<p class="hero-note">' + h(rd.scale_note || "") + "</p></div>" +
      '<div class="stack"><div class="card"><div class="section-title"><h2>Findings by severity</h2><span class="muted small">' +
      plural(sm.total_findings || findings().length, "finding") + '</span></div><div class="sev-tiles">' + tiles + "</div></div>" +
      '<div class="card"><div class="section-title"><h2>Readiness by pillar</h2><span class="muted small">0 to 100, higher is better</span></div>' +
      '<div class="pillars" id="pillars">' + pillarRows + "</div></div></div></div>" +
      '<div class="two-col" style="margin-top:16px">' +
      '<div class="card"><div class="section-title"><h2>Fix these first</h2><button class="btn sm ghost" data-goto="roadmap">Full roadmap</button></div>' + fixFirst + "</div>" +
      '<div class="card"><div class="section-title"><h2>Audit scope</h2></div>' +
      (scopeRows.length ? '<dl class="kv">' + scopeRows.map(function (r) { return "<dt>" + h(r[0]) + "</dt><dd>" + h(r[1]) + "</dd>"; }).join("") + "</dl>"
        : '<p class="muted">No scope notes recorded.</p>') + "</div></div>";

    $$(".sev-tile", body).forEach(function (t) {
      t.addEventListener("click", function () {
        var s = t.getAttribute("data-sev");
        SEV.forEach(function (k) { S.filters.sev[k] = k === s; });
        S.filters.pillar = ""; S.filters.skill = ""; S.filters.q = "";
        setTab("findings");
      });
    });
    $$(".pillar-row", body).forEach(function (row) {
      var p = PILLARS.filter(function (x) { return x.key === row.getAttribute("data-pillar"); })[0];
      var fs = pillarFindings(p);
      var tipText = function () {
        if (!fs.length) return "<strong>" + h(p.label) + "</strong>No findings in this pillar.";
        var by = SEV.map(function (s) { var n = fs.filter(function (f) { return f.severity === s; }).length; return n ? n + " " + s : ""; }).filter(Boolean).join(", ");
        return "<strong>" + h(p.label) + "</strong>" + plural(fs.length, "finding") + ": " + h(by) + ". Click to view.";
      };
      attachTip(row, tipText);
      row.addEventListener("click", function () {
        SEV.forEach(function (k) { S.filters.sev[k] = true; });
        S.filters.pillar = p.key; S.filters.skill = ""; S.filters.q = "";
        setTab("findings");
      });
    });
    $$("[data-goto]", body).forEach(function (b) { b.addEventListener("click", function () { setTab(b.getAttribute("data-goto")); }); });

    // Animate in: gauge sweep, count-up, bars growing from zero.
    var val = $(".gauge .val", body);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        if (val && scored) {
          var full = parseFloat(val.getAttribute("data-full"));
          val.style.strokeDashoffset = (full * (1 - Math.max(0, Math.min(100, rd.overall)) / 100)).toFixed(2);
        }
        $$(".bar-fill[data-w]", body).forEach(function (b) { b.style.width = b.getAttribute("data-w") + "%"; });
      });
    });
    if (scored) countUp($("#gauge-num"), rd.overall);
  }

  function weakestHtml(rd) {
    var rows = PILLARS.map(function (p) {
      var pd = (rd.pillars || {})[p.key] || {};
      return { label: pd.label || p.label, score: pd.score };
    }).filter(function (r) { return typeof r.score === "number" && r.score < 100; })
      .sort(function (a, b) { return a.score - b.score; }).slice(0, 2);
    if (!rows.length) return "";
    return '<div><div class="hero-label" style="margin-bottom:8px">Weakest pillars</div><ul class="weakest">' + rows.map(function (r) {
      return "<li><span>" + h(r.label) + "</span><b>" + h(r.score) + '</b><span class="bar-track" aria-hidden="true"><span class="bar-fill" style="width:' + r.score + '%"></span></span></li>';
    }).join("") + "</ul></div>";
  }

  // --- tooltip ----------------------------------------------------------------
  var tipEl = null;
  function attachTip(el, htmlFn) {
    var show = function (x, y) {
      if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "tip"; tipEl.setAttribute("role", "tooltip"); document.body.appendChild(tipEl); }
      tipEl.innerHTML = htmlFn();
      tipEl.hidden = false;
      var r = tipEl.getBoundingClientRect();
      var left = Math.min(window.innerWidth - r.width - 12, x + 14);
      var top = y + 16 + r.height > window.innerHeight ? y - r.height - 12 : y + 16;
      tipEl.style.left = Math.max(8, left) + "px";
      tipEl.style.top = Math.max(8, top) + "px";
    };
    el.addEventListener("mousemove", function (e) { show(e.clientX, e.clientY); });
    el.addEventListener("mouseleave", function () { if (tipEl) tipEl.hidden = true; });
    el.addEventListener("focus", function () { var r = el.getBoundingClientRect(); show(r.left + r.width / 2, r.bottom); });
    el.addEventListener("blur", function () { if (tipEl) tipEl.hidden = true; });
  }

  // --- findings ---------------------------------------------------------------
  function filtered() {
    var F = S.filters, q = F.q.toLowerCase();
    var pillar = PILLARS.filter(function (p) { return p.key === F.pillar; })[0];
    var out = findings().filter(function (f) {
      if (!F.sev[f.severity] && SEV.indexOf(f.severity) >= 0) return false;
      if (F.skill && f.source_skill !== F.skill) return false;
      if (pillar && !pillar.skills.some(function (k) { return (f.source_skill || "").indexOf(k) >= 0; })) return false;
      if (q) {
        var hay = [f.title, f.evidence, f.mechanism, f.code, f.source_skill,
          f.suggested_action && f.suggested_action.summary].join(" ").toLowerCase();
        if (hay.indexOf(q) < 0) return false;
      }
      return true;
    });
    var bySev = function (a, b) { return (SEV_RANK[a.severity] || 9) - (SEV_RANK[b.severity] || 9); };
    out.sort(function (a, b) {
      if (F.sort === "confidence") return (b.confidence || 0) - (a.confidence || 0) || bySev(a, b);
      if (F.sort === "effort") return (EFFORT_RANK[a.effort] || 9) - (EFFORT_RANK[b.effort] || 9) || bySev(a, b);
      return bySev(a, b) || (b.confidence || 0) - (a.confidence || 0);
    });
    return out;
  }

  function findingCard(f) {
    var sa = f.suggested_action || {};
    var saText = typeof sa === "string" ? sa : sa.summary;
    var conf = typeof f.confidence === "number"
      ? '<span class="conf" title="Confidence the audit has that this is a real defect"><span class="track"><span class="fill" style="width:' +
      Math.round(f.confidence * 100) + '%"></span></span>' + Math.round(f.confidence * 100) + "%</span>" : "";
    var urls = f.affected_urls || [];
    var metaItems = [
      ["Code", f.code], ["Skill", skillName(f.source_skill)], ["Evidence tier", f.evidence_tier],
      ["Signal tier", f.signal_tier ? "Tier " + f.signal_tier : null], ["Effort", f.effort],
      ["Category", f.category], ["Corroborated by", f.corroborated_by ? [].concat(f.corroborated_by).join(", ") : null]
    ].filter(function (x) { return x[1]; });
    var sevCls = SEV.indexOf(f.severity) >= 0 ? f.severity : "low";
    return '<details class="finding sev-' + sevCls + '" id="f-' + h(f.id || f.code) + '">' +
      "<summary>" + sevBadge(f.severity) +
      '<div><div class="ftitle">' + h(f.title) + '</div><div class="fsub">' +
      (f.code ? '<span class="tag mono">' + h(f.code) + "</span>" : "") +
      '<span class="tag">' + h(skillName(f.source_skill)) + "</span>" +
      (f.effort ? '<span class="tag">' + h(f.effort) + " fix</span>" : "") +
      (f.severity_adjusted_from ? '<span class="adjusted">critic: ' + h(f.severity_adjusted_from) + " &rarr; " + h(f.severity) + "</span>" : "") +
      "</div></div>" +
      '<div class="fright">' + conf + '<span class="chev">' + icon("chev") + "</span></div></summary>" +
      '<div class="fbody">' +
      '<div class="stack"><div><h4>Evidence</h4><p>' + h(f.evidence) + "</p></div>" +
      (f.mechanism ? "<div><h4>Why it matters</h4><p>" + h(f.mechanism) + "</p></div>" : "") + "</div>" +
      '<div class="stack"><div><h4>Suggested fix</h4><div class="fix-box"><p>' + h(saText) + "</p>" + (sa.how ? "<p>" + h(sa.how) + "</p>" : "") + "</div></div>" +
      (urls.length ? "<div><h4>Affected URLs</h4><ul class=\"url-list\">" + urls.slice(0, 12).map(function (u) {
        return '<li><a href="' + safeUrl(u) + '" target="_blank" rel="noopener noreferrer">' + h(u) + "</a></li>";
      }).join("") + (urls.length > 12 ? "<li class=\"muted\">and " + (urls.length - 12) + " more</li>" : "") + "</ul></div>" : "") + "</div>" +
      '<div class="meta-grid full">' + metaItems.map(function (m) { return "<div><span>" + h(m[0]) + "</span><strong>" + h(m[1]) + "</strong></div>"; }).join("") + "</div>" +
      "</div></details>";
  }

  function tabFindings(body) {
    var F = S.filters, all = findings();
    var skills = all.map(function (f) { return f.source_skill; }).filter(function (s, i, a) { return s && a.indexOf(s) === i; }).sort();
    var sevCount = function (s) { return all.filter(function (f) { return f.severity === s; }).length; };
    body.innerHTML =
      '<div class="toolbar">' +
      '<label class="search">' + icon("search") + '<input id="f-search" type="search" placeholder="Search findings  ( / )" value="' + h(F.q) + '" aria-label="Search findings"></label>' +
      SEV.map(function (s) {
        return '<button class="chip-toggle" data-sev="' + s + '" aria-pressed="' + !!F.sev[s] + '">' + sevBadge(s) + '<span class="c">' + sevCount(s) + "</span></button>";
      }).join("") +
      '<select id="f-pillar" aria-label="Pillar"><option value="">All pillars</option>' + PILLARS.map(function (p) {
        return '<option value="' + p.key + '"' + (F.pillar === p.key ? " selected" : "") + ">" + h(p.label) + "</option>";
      }).join("") + "</select>" +
      '<select id="f-skill" aria-label="Skill"><option value="">All skills</option>' + skills.map(function (s) {
        return '<option value="' + h(s) + '"' + (F.skill === s ? " selected" : "") + ">" + h(skillName(s)) + "</option>";
      }).join("") + "</select>" +
      '<select id="f-sort" aria-label="Sort"><option value="severity">Sort: severity</option><option value="confidence">Sort: confidence</option><option value="effort">Sort: effort</option></select>' +
      "</div>" +
      '<p class="result-count" id="f-count"></p><div id="f-list"></div>';
    $("#f-sort").value = F.sort;

    var draw = function () {
      var list = filtered();
      $("#f-count").textContent = list.length === all.length ? plural(all.length, "finding") : list.length + " of " + all.length + " findings";
      $("#f-list").innerHTML = list.length ? list.map(findingCard).join("")
        : '<div class="banner">' + icon("info") + "<span>No findings match these filters.</span></div>";
    };
    draw();

    $("#f-search").addEventListener("input", function () { F.q = this.value; draw(); });
    $$(".chip-toggle", body).forEach(function (b) {
      b.addEventListener("click", function () {
        var s = b.getAttribute("data-sev");
        F.sev[s] = !F.sev[s];
        b.setAttribute("aria-pressed", String(F.sev[s]));
        draw();
      });
    });
    $("#f-pillar").addEventListener("change", function () { F.pillar = this.value; draw(); });
    $("#f-skill").addEventListener("change", function () { F.skill = this.value; draw(); });
    $("#f-sort").addEventListener("change", function () { F.sort = this.value; draw(); });
    if (S._openFinding) {
      var el = document.getElementById("f-" + S._openFinding);
      S._openFinding = null;
      if (el) { el.open = true; el.scrollIntoView({ block: "center" }); }
    }
  }

  // --- roadmap ----------------------------------------------------------------
  function tabRoadmap(body) {
    var rm = S.report.roadmap || {};
    var lanes = [
      { key: "now", title: "Do now", sub: "Serious, or quick to fix" },
      { key: "next", title: "Next", sub: "Worth scheduling" },
      { key: "later", title: "Later", sub: "Lower impact or larger projects" }
    ];
    body.innerHTML =
      (rm.note ? '<div class="banner">' + icon("info") + "<span>" + h(rm.note) + "</span></div>" : "") +
      '<div class="roadmap">' + lanes.map(function (l, i) {
        var items = rm[l.key] || [];
        return '<div class="lane lane-' + l.key + '"><div class="lane-head"><span class="lane-num">' + (i + 1) + "</span><div><h3>" + h(l.title) + "</h3><p>" + h(l.sub) + "</p></div>" +
          '<span class="tag">' + items.length + "</span></div>" +
          (items.length ? items.map(function (r) {
            return '<button class="lane-card" data-fid="' + h(r.id) + '"><div class="top">' + sevBadge(r.severity) +
              (r.effort ? '<span class="tag">' + h(r.effort) + "</span>" : "") + '</div><div class="t">' + h(r.title) +
              '</div><div class="a">' + h(r.action) + "</div></button>";
          }).join("") : '<div class="lane-empty">Nothing here.</div>') + "</div>";
      }).join("") + "</div>";
    $$(".lane-card", body).forEach(function (c) {
      c.addEventListener("click", function () {
        SEV.forEach(function (k) { S.filters.sev[k] = true; });
        S.filters.pillar = ""; S.filters.skill = ""; S.filters.q = "";
        S._openFinding = c.getAttribute("data-fid");
        setTab("findings");
      });
    });
  }

  // --- evidence ---------------------------------------------------------------
  function statusCell(code) {
    if (code === null || code === undefined) return '<span class="status none"><i></i>n/a</span>';
    var cls = code >= 200 && code < 300 ? "ok" : code === 404 ? "warn" : code >= 400 ? "bad" : "warn";
    return '<span class="status ' + cls + '"><i></i>' + h(code) + "</span>";
  }

  function tabEvidence(body) {
    if (!S.evidenceLoaded) {
      body.innerHTML = '<p class="muted">Loading evidence&hellip;</p>';
      api("GET", "/api/runs/" + S.runId + "/evidence").then(function (ev) { S.evidence = ev; })
        .catch(function () { S.evidence = null; })
        .then(function () { S.evidenceLoaded = true; if (S.tab === "evidence") renderTab(); });
      return;
    }
    var e = S.evidence;
    if (!e) {
      body.innerHTML = '<div class="banner">' + icon("info") + "<span>No evidence bundle for this audit. Import its <code>evidence.json</code> alongside the report to see it here.</span></div>";
      return;
    }
    var robots = e.robots || {}, agents = robots.agents || {}, probes = ((e.ua_probe || {}).probes) || {};
    var agentRows = Object.keys(agents).map(function (name) {
      var a = agents[name], imp = IMPACT[a.citation_impact] || { text: a.citation_impact || "", cls: "" };
      var probe = probes[name];
      var blocked = a.allowed_root === false || (probe && (probe.status === 401 || probe.status === 403));
      var impCls = imp.cls + (blocked ? "-blocked" : "");
      return "<tr" + (blocked ? ' class="row-blocked"' : "") + "><td><strong>" + h(name) + "</strong></td><td>" + h(a.operator) + "</td><td>" + h(a.category) + "</td>" +
        '<td><span class="impact ' + h(impCls) + '">' + h(imp.text) + "</span></td>" +
        "<td>" + (a.allowed_root === false ? '<span class="status bad"><i></i>disallowed</span>' : '<span class="status ok"><i></i>allowed</span>') + "</td>" +
        "<td>" + (probe ? statusCell(probe.status) : '<span class="muted">not probed</span>') + "</td></tr>";
    });
    if (probes.browser) {
      agentRows.unshift('<tr><td><strong>Browser</strong></td><td class="muted">baseline</td><td class="muted">reference</td><td class="muted">&ndash;</td><td class="muted">&ndash;</td><td>' + statusCell(probes.browser.status) + "</td></tr>");
    }
    var sm = e.sitemap || {}, wk = e.wellknown || {}, st = e.stats || {};
    var fileRows = [
      ["robots.txt", robots.status, robots.present ? (robots.bytes + " bytes" + ((robots.declared_sitemaps || []).length ? ", declares " + plural(robots.declared_sitemaps.length, "sitemap") : ", no Sitemap line")) : "not found"],
      ["sitemap", (sm.checked && sm.checked[0] && sm.checked[0].status), (sm.total_urls_found ? plural(sm.total_urls_found, "URL") + " found" : "no URLs found") + (sm.checked ? " · checked " + sm.checked.map(function (c) { return c.url; }).join(", ") : "")],
      ["llms.txt", (wk.llms_txt || {}).status, (wk.llms_txt || {}).present ? "present" : "absent (optional; no measured effect)"],
      ["security.txt", (wk.security_txt || {}).status, (wk.security_txt || {}).present ? "present" : "absent"]
    ];
    var pages = e.pages || [];
    var pageRows = pages.map(function (p) {
      var h1 = (p.headings || []).filter(function (x) { return x[0] === 1; }).length;
      var sd = (p.structured_data || {}).verdict || ((p.jsonld_types || []).length ? p.jsonld_types.join(", ") : "none");
      return '<tr><td class="url"><a href="' + safeUrl(p.url) + '" target="_blank" rel="noopener noreferrer">' + h(p.url) + "</a>" +
        (p.title ? '<div class="muted small">' + h(p.title.slice(0, 90)) + "</div>" : "") + "</td>" +
        "<td>" + statusCell(p.status) + '</td><td class="num">' + h(p.word_count || 0) + '</td><td class="num">' + h(h1) + "</td>" +
        "<td>" + h(String(sd).replace(/_/g, " ").toLowerCase()) + "</td><td>" + (p.lang ? h(p.lang) : '<span class="muted">none</span>') + "</td>" +
        "<td>" + (p.meta_description ? "yes" : '<span class="muted">no</span>') + "</td></tr>";
    });
    body.innerHTML =
      '<div class="stack">' +
      '<div><div class="section-title"><h2>AI crawler access</h2><span class="muted small">robots.txt rules plus a live request with each user agent</span></div>' +
      '<div class="table-wrap"><table><thead><tr><th>Agent</th><th>Operator</th><th>Type</th><th>Cost of blocking</th><th>robots.txt</th><th>Live probe</th></tr></thead><tbody>' +
      agentRows.join("") + "</tbody></table></div>" +
      '<p class="muted small" style="margin-top:8px">Blocking a training crawler does not remove a site from AI answers. Blocking a search-index crawler does. The live probe only confirms a block on HTTP 401 or 403.</p></div>' +
      '<div class="two-col"><div><div class="section-title"><h2>Site files</h2></div><div class="table-wrap"><table><thead><tr><th>File</th><th>HTTP</th><th>Result</th></tr></thead><tbody>' +
      fileRows.map(function (r) { return "<tr><td><strong>" + h(r[0]) + "</strong></td><td>" + statusCell(r[1]) + "</td><td>" + h(r[2]) + "</td></tr>"; }).join("") +
      "</tbody></table></div></div>" +
      '<div><div class="section-title"><h2>Crawl</h2></div><div class="card"><dl class="kv">' +
      "<dt>Pages fetched</dt><dd>" + h(st.pages_fetched) + "</dd><dt>Failed</dt><dd>" + h(st.pages_failed || 0) + "</dd>" +
      "<dt>Elapsed</dt><dd>" + h(st.elapsed_seconds) + " s</dd><dt>Budget exhausted</dt><dd>" + (st.budget_exhausted ? "yes" : "no") + "</dd>" +
      "<dt>Skipped by robots.txt</dt><dd>" + h((st.robots_skipped || []).length) + "</dd>" +
      "<dt>Limits</dt><dd>" + h(((e.limits || {}).max_pages || "?") + " pages, depth " + ((e.limits || {}).max_depth || "?") + ", " + ((e.limits || {}).budget_seconds || "?") + " s") + "</dd>" +
      "<dt>Collected</dt><dd>" + h(fmtDate(e.collected_at)) + "</dd></dl></div></div></div>" +
      '<div><div class="section-title"><h2>Pages sampled</h2><span class="muted small">' + plural(pages.length, "page") + '</span></div>' +
      '<div class="table-wrap"><table><thead><tr><th>URL</th><th>HTTP</th><th>Words</th><th>H1</th><th>Structured data</th><th>lang</th><th>Meta desc.</th></tr></thead><tbody>' +
      pageRows.join("") + "</tbody></table></div></div></div>";
  }

  // --- review -----------------------------------------------------------------
  function tabReview(body) {
    var rep = S.report, cs = rep.critic_summary || {}, na = rep.not_assessed || [];
    var sup = cs.suppressed || [], adj = cs.severity_adjustments || [];
    var parts = [];
    if (S.run.agent_summary) {
      parts.push('<div class="card"><div class="section-title"><h2>Agent summary</h2><span class="muted small">' + h(S.run.harness || "") + " · " + h(S.run.model || "") +
        '</span></div><div class="md-view" style="max-height:none;border:0;padding:0;background:none">' + h(S.run.agent_summary) + "</div></div>");
    }
    parts.push('<div class="card"><div class="section-title"><h2>Evidence critic</h2></div><dl class="kv">' +
      "<dt>Findings considered</dt><dd>" + h(cs.findings_considered !== undefined ? cs.findings_considered : "n/a") + "</dd>" +
      "<dt>Findings reported</dt><dd>" + h(cs.findings_reported !== undefined ? cs.findings_reported : findings().length) + "</dd>" +
      "<dt>Suppressed</dt><dd>" + sup.length + "</dd><dt>Severity changes</dt><dd>" + adj.length + "</dd></dl></div>");
    if (sup.length) {
      parts.push('<div><div class="section-title"><h2>Suppressed findings</h2><span class="muted small">Removed before the report, with the reason</span></div>' +
        '<div class="table-wrap"><table><thead><tr><th>Finding</th><th>Reason</th></tr></thead><tbody>' +
        sup.map(function (s) { return "<tr><td><strong>" + h(s.title) + "</strong>" + (s.severity ? "<div>" + sevBadge(s.severity) + "</div>" : "") + "</td><td>" + h(s.reason) + "</td></tr>"; }).join("") +
        "</tbody></table></div></div>");
    }
    if (adj.length) {
      parts.push('<div class="card"><div class="section-title"><h2>Severity changes</h2></div><ul class="url-list">' +
        adj.map(function (a) { return "<li>" + h(typeof a === "string" ? a : JSON.stringify(a)) + "</li>"; }).join("") + "</ul></div>");
    }
    parts.push('<div><div class="section-title"><h2>Not assessed</h2><span class="muted small">Not a defect: not applicable, or could not be observed</span></div>' +
      (na.length ? '<div class="table-wrap"><table><thead><tr><th>Item</th><th>Status</th><th>Evidence</th></tr></thead><tbody>' +
        na.map(function (n) { return "<tr><td><strong>" + h(n.title) + "</strong></td><td>" + h(String(n.status || "").replace(/_/g, " ")) + "</td><td>" + h(n.evidence) + "</td></tr>"; }).join("") +
        "</tbody></table></div>" : '<p class="muted">Every area was assessed.</p>') + "</div>");
    body.innerHTML = '<div class="stack">' + parts.join("") + "</div>";
  }

  // --- compare ----------------------------------------------------------------
  function tabCompare(body) {
    var others = S.runs.filter(function (r) { return r.id !== S.runId && r.status === "done"; });
    var site = S.run.site;
    others.sort(function (a, b) { return (b.site === site) - (a.site === site) || (b.started_at || "").localeCompare(a.started_at || ""); });
    if (!others.length) {
      body.innerHTML = '<div class="banner">' + icon("info") + "<span>Run another audit to compare against. Findings are matched by their stable code, so you can see what a fix actually changed.</span></div>";
      return;
    }
    body.innerHTML =
      '<div class="toolbar"><label class="field" style="flex:1 1 320px;max-width:520px"><span>Compare this audit against</span>' +
      '<select id="cmp-select"><option value="">Choose an audit&hellip;</option>' + others.map(function (r) {
        return '<option value="' + h(r.id) + '"' + (S.compareWith === r.id ? " selected" : "") + ">" + h(r.site) + " · " + h(r.mode) + " · " + h(fmtDate(r.started_at)) +
          (r.summary && r.summary.score !== null && r.summary.score !== undefined ? " · " + h(r.summary.score) : "") + "</option>";
      }).join("") + "</select></label></div><div id=\"cmp-body\"></div>";
    $("#cmp-select").addEventListener("change", function () {
      S.compareWith = this.value; S.compareReport = null;
      drawCompare();
    });
    drawCompare();
  }

  function drawCompare() {
    var out = $("#cmp-body");
    if (!out) return;
    if (!S.compareWith) { out.innerHTML = '<p class="muted">Pick an earlier audit, ideally of the same site.</p>'; return; }
    if (!S.compareReport) {
      out.innerHTML = '<p class="muted">Loading&hellip;</p>';
      var id = S.compareWith;
      api("GET", "/api/runs/" + id + "/report").then(function (r) {
        if (S.compareWith !== id) return;
        S.compareReport = r; drawCompare();
      }).catch(function (e) { out.innerHTML = '<div class="banner">' + h(e.message) + "</div>"; });
      return;
    }
    var key = function (f) { return f.code || f.title; };
    var base = {}, cur = {};
    (S.compareReport.findings || []).forEach(function (f) { base[key(f)] = f; });
    findings().forEach(function (f) { cur[key(f)] = f; });
    var fixed = Object.keys(base).filter(function (k) { return !cur[k]; }).map(function (k) { return base[k]; });
    var added = Object.keys(cur).filter(function (k) { return !base[k]; }).map(function (k) { return cur[k]; });
    var kept = Object.keys(cur).filter(function (k) { return base[k]; }).map(function (k) { return { now: cur[k], was: base[k] }; });
    var bySev = function (a, b) { return (SEV_RANK[a.severity] || 9) - (SEV_RANK[b.severity] || 9); };
    fixed.sort(bySev); added.sort(bySev);
    kept.sort(function (a, b) { return bySev(a.now, b.now); });
    var s0 = (S.compareReport.readiness || {}).overall, s1 = (S.report.readiness || {}).overall;
    var delta = (typeof s0 === "number" && typeof s1 === "number") ? s1 - s0 : null;
    var li = function (f) { return "<li>" + sevBadge(f.severity) + "<div>" + h(f.title) + "</div><code>" + h(f.code || "") + "</code></li>"; };
    // "Resolved" and "New" only make sense when the baseline is the earlier audit.
    var baseRun = S.runs.filter(function (r) { return r.id === S.compareWith; })[0] || {};
    var earlier = (S.compareReport.audited_at || "") < (S.report.audited_at || "");
    var L = earlier ? ["Resolved", "New", "Still present"] : ["Only in the other audit", "Only in this audit", "In both"];
    var note = "";
    if (baseRun.mode && baseRun.mode !== S.run.mode) {
      note = '<div class="banner">' + icon("info") + "<span>These audits ran in different modes (" + h(S.run.mode) + " and " + h(baseRun.mode) +
        "). Differences may come from the agent's review rather than from changes to the site, and an agent can name the same issue with a different code.</span></div>";
    }
    out.innerHTML = note +
      '<div class="card" style="margin-bottom:14px"><dl class="kv"><dt>Readiness</dt><dd>' +
      (delta === null ? "n/a" : h(s0) + " &rarr; " + h(s1) + ' <span class="delta ' + (earlier ? (delta > 0 ? "up" : delta < 0 ? "down" : "") : "") + '">(' + (delta > 0 ? "+" : "") + delta + ")</span>") +
      "</dd><dt>Baseline</dt><dd>" + h(S.compareReport.site || "") + " · " + h(fmtDate(S.compareReport.audited_at)) + "</dd>" +
      "<dt>Matched by</dt><dd>stable finding code</dd></dl></div>" +
      '<div class="diff-cols">' +
      '<div class="diff-col"><h3><span class="delta' + (earlier ? " up" : "") + '">' + fixed.length + "</span> " + L[0] + "</h3><ul>" + (fixed.map(li).join("") || '<li class="muted">None</li>') + "</ul></div>" +
      '<div class="diff-col"><h3><span class="delta' + (earlier ? " down" : "") + '">' + added.length + "</span> " + L[1] + "</h3><ul>" + (added.map(li).join("") || '<li class="muted">None</li>') + "</ul></div>" +
      '<div class="diff-col"><h3><span class="delta">' + kept.length + "</span> " + L[2] + "</h3><ul>" + (kept.map(function (p) {
        var ch = p.now.severity !== p.was.severity ? ' <span class="adjusted">was ' + h(p.was.severity) + "</span>" : "";
        return "<li>" + sevBadge(p.now.severity) + ch + "<div>" + h(p.now.title) + "</div><code>" + h(p.now.code || "") + "</code></li>";
      }).join("") || '<li class="muted">None</li>') + "</ul></div></div>";
  }

  // --- markdown -----------------------------------------------------------------
  function tabMarkdown(body) {
    if ((S.run.files || []).indexOf("audit_report.md") < 0) {
      body.innerHTML = '<div class="banner">' + icon("info") + "<span>No Markdown rendering for this audit.</span></div>";
      return;
    }
    if (S.markdown === null) {
      body.innerHTML = '<p class="muted">Loading&hellip;</p>';
      fetch("/api/runs/" + S.runId + "/download/audit_report.md").then(function (r) { return r.text(); })
        .then(function (t) { S.markdown = t; if (S.tab === "markdown") renderTab(); });
      return;
    }
    body.innerHTML = '<div class="md-view">' + h(S.markdown) + "</div>";
  }

  // --- import -------------------------------------------------------------------
  function importFiles(files) {
    files = Array.prototype.slice.call(files || []);
    if (!files.length) return;
    var read = files.map(function (f) {
      return f.text().then(function (t) { return { name: f.name, text: t }; });
    });
    Promise.all(read).then(function (items) {
      var body = {};
      items.forEach(function (it) {
        if (/\.md$/i.test(it.name)) { body.markdown = it.text; return; }
        var obj;
        try { obj = JSON.parse(it.text); } catch (e) { return; }
        if (obj && obj.findings && obj.summary) { body.report = obj; body.name = it.name; }
        else if (obj && obj.pages && obj.robots) body.evidence = obj;
      });
      if (!body.report) throw new Error("None of those files is an audit_report.json.");
      return api("POST", "/api/import", body);
    }).then(function (r) {
      toast("Report imported.");
      location.hash = "#/run/" + r.id;
      refreshHistory();
    }).catch(function (e) { toast(e.message); });
  }
  $("#import-input").addEventListener("change", function () { importFiles(this.files); this.value = ""; });
  document.addEventListener("dragover", function (e) { e.preventDefault(); $("#main").classList.add("drop-hint"); });
  document.addEventListener("dragleave", function (e) { if (!e.relatedTarget) $("#main").classList.remove("drop-hint"); });
  document.addEventListener("drop", function (e) {
    e.preventDefault();
    $("#main").classList.remove("drop-hint");
    importFiles(e.dataTransfer.files);
  });

  // --- keyboard -----------------------------------------------------------------
  document.addEventListener("keydown", function (e) {
    if (e.key === "/" && !/INPUT|TEXTAREA|SELECT/.test((document.activeElement || {}).tagName || "")) {
      var s = $("#f-search");
      if (s) { e.preventDefault(); s.focus(); }
      else if (S.report) { e.preventDefault(); setTab("findings"); setTimeout(function () { var x = $("#f-search"); if (x) x.focus(); }, 0); }
    }
  });

  // --- boot ---------------------------------------------------------------------
  api("GET", "/api/meta").then(function (m) {
    S.meta = m;
    renderEngineBadge();
    setupForm();
    return refreshHistory();
  }).then(route).catch(function (e) {
    $("#main").innerHTML = '<div class="banner">' + icon("info") + "<span>Cannot reach the audit server: " + h(e.message) + "</span></div>";
  });
})();
