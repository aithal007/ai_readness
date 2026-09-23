# Adobe University Hackathon 2026 — brand-ai-readiness-audit

An Agent Skill Marketplace that audits any website for **AI discoverability**
(why assistants miss, misquote or won't cite a brand) and **on-site engagement**
(why visitors who arrive don't stay). It emits one prioritized, evidence-backed
report of findings and fixes. Recommend-only: read-only GET traffic, robots.txt
honoured, nothing on the target site is ever changed.

## The engine is frozen

`submission.zip` is the exact Round 3 package. Round 4 requires the live demo to
run that package unchanged, so nothing in it has been edited since submission.

```
submission.zip  SHA-256  1d5e0f3e4dd12a8c12e205b4723124b4d441cdbf3f76605a2befde9114ec33b1
```

`brand-ai-readiness-audit/` is the same package unpacked, so the code can be read
on GitHub. It is byte-identical to the archive.

## Layout

| Path | What it is |
|---|---|
| `submission.zip` | The frozen Round 3 marketplace. The only engine. |
| `brand-ai-readiness-audit/` | That archive unpacked, for reading. Start with its [README](./brand-ai-readiness-audit/README.md) and [ARCHITECTURE](./brand-ai-readiness-audit/ARCHITECTURE.md). |
| `round4/REPLAY_TEAMNAME.txt` | Round 4 reproduction manifest: harness, model, exact commands, expected output. |
| `round4/NARRATION_SCRIPT.md` | Word-for-word video narration. Every claim cites a file and line in the package. |
| `round4/VIDEO_RUNBOOK.md` | Recording checklist, integrity gates, and the frozen engine's known limits. |
| `round4/setup_demo.py` | Installs the package's skills where Claude Code finds them, and proves byte identity. |

## Check it yourself

Both commands run offline with the Python standard library only.

```bash
python3 -m zipfile -e submission.zip r3
cd r3/brand-ai-readiness-audit
python3 tests/validate_spec.py    # -> ALL CHECKS PASSED
python3 tests/run_tests.py        # -> 119/119 passed
```

To replay the live agent demo, follow `round4/REPLAY_TEAMNAME.txt`.
