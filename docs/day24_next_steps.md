## Day 24 — Next steps and recommendations

This document captures recommended follow-ups after the Day 24 baseline work (profiles, fusion, correlation, report, graph). These tasks are prioritized, include acceptance criteria, test guidance, and notes about risk/effort. We'll implement these incrementally in small PR-like changes.

---

### 1) Priority — Improve collection extraction & persistence (pipeline)

What
- Expand the heuristics in `engine/pipeline.py` (or provider-specific normalizers) to extract and persist richer collections into `profiles/<target>/*`:
  - domains (with optional metadata: resolved IPs, ASN, first_seen)
  - ips (with ASN, country, owner)
  - emails (with context: source/provider, first_seen)
  - social handles / URLs

Why
- Enables richer reports/graphs and improves fusion/correlation quality.

Acceptance criteria
- `profiles/<target>/domains.json`, `ips.json`, `emails.json` populated after pipeline runs for test fixtures.
- Unit test asserting that running the pipeline for a mocked target persists at least one collection file.

Files to touch
- `engine/pipeline.py` (collection extraction)
- `core/profiles.py` (may add richer merge logic)

Estimate
- Small change (2–4 hours dev + tests).

---

### 2) Priority — Add integration tests for profile persistence

What
- Add a couple of focused integration tests that run `run_pipeline_for_targets` against mocked/stubbed providers and assert metadata and collection files are saved in `profiles/`.

Why
- Prevent regressions and ensure pipeline+fusion persistence works end-to-end.

Acceptance criteria
- New tests in `tests/` pass in CI and locally.

Files to add
- `tests/test_pipeline_profiles.py` — uses monkeypatch to stub provider outputs and asserts `profiles/<target>/metadata.json` contains `confidence`.

Estimate
- Small (1–2 hours).

---

### 3) Priority — Improve fusion scoring

What
- Iteratively refine `core/fusion.py` to:
  - apply per-provider weights (e.g., VirusTotal high weight for reputation, DNS low weight for presence)
  - detect conflicts (e.g., contradictory registrar info) and penalize confidence
  - normalize scores across different provider result shapes

Why
- More meaningful confidence values improve triage and reporting.

Acceptance criteria
- Unit tests for scoring scenarios (weights and conflicts) pass.

Files to touch
- `core/fusion.py`, `tests/test_fusion_module.py` (extend)

Estimate
- Medium (3–6 hours) depending on complexity.

---

### 4) Priority — Improve graph visuals and export options

What
- Enhance DOT generation further:
  - Edge weights and labels for confidence and relation type
  - Cluster by ASN, provider, or entity type
  - Offer exports to SVG, PNG, and interactive HTML (via `viz.js` embedding)

Why
- Visual clarity is critical for analysts and for embedding in reports.

Acceptance criteria
- Graph CLI produces a DOT file with clusters and edge labels; with Graphviz installed it produces a PNG/SVG that contains cluster boxes and readable labels.

Files to touch
- `cli/main.py` (graph command), possibly a new `core/graph.py` helper, tests for DOT creation

Estimate
- Medium (4–8 hours + optional visualization polishing).

---

### 5) Priority — Migrate more modules to structured output

What
- Continue converting modules to expose `run_structured()` or return structured dicts that include `target`, `type`, and provider `data`.

Why
- Consistent shapes simplify renderer, fusion, and pipeline logic.

Acceptance criteria
- At least the next 3 modules (e.g., DNS provider, GitHub OSINT, Pastebin) have structured outputs and CLI handlers use `_format_output`.

Files to touch
- `modules/*/scanner.py`, `cli/main.py` (subcommands)

Estimate
- Per-module: small (1–3 hours each). Prioritize high-value providers.

---

### 6) Priority — CI and test hygiene

What
- Update CI to run new unit/integration tests and add an optional matrix job that installs `graphviz` when testing graph rendering.
- Add minimal snapshot tests for DOT content (string assertions) to catch regressions.

Why
- Keeps features stable and catches regressions early.

Estimate
- Small (1–2 hours).

---

### 7) Optional advanced features — pick one to prototype

Option A — ML Classifier
- Build a small feature extractor and prototype a basic classifier (sklearn logistic/regression or decision tree) to label domains as clean/suspicious/malicious.
- Add a `core/ml.py` scaffold and tests with synthetic data.

Option B — Playwright scraping over Tor
- Prototype a `modules/browserless` module that uses Playwright + Tor (requires Playwright + system browsers + Tor). Provide config flags and safe defaults.

Option C — Breach checks (HIBP-like)
- Implement an optional `core/breaches.py` that queries public breach APIs (or supports local breach DBs) and returns exposure info for emails.

Recommendation
- Start with Option C (Breach checks) because it has high analyst ROI and is easy to prototype with a mock/stub for tests. ML is valuable but requires labeled data and iteration; Playwright adds runtime complexity.

Estimate
- Option C: small (2–4 hours). Option A/B: medium-to-large (1–3 days depending on scope).

---

### 8) Security, privacy, and operational notes

- Respect API rate limits and secret management. Add keys and tokens to `core/keys.py` and document how to configure them.
- When enabling Playwright or other browser-based scraping, warn users about legal concerns and add opt-in flags.
- Consider encrypting `profiles/` or adding access controls for sensitive investigations.

---

### Helpful commands

Run tests locally (fast):
```bash
pytest tests/test_fusion_module.py -q
pytest tests/test_profiles_module.py -q
pytest -q
```

Generate a graph (writes DOT or PNG if graphviz installed):
```bash
python -m cli.main graph example.com --output reports/example.png
```

Try a pipeline run for a single target (dev):
```bash
python -m cli.main pipeline --targets example.com --outdir results/pipeline/test
```

---

If you'd like, I can: 
- implement item (1) collection extraction now and add the integration test (recommended next immediate step), or
- prototype breach checks (Option C) next (fast ROI).

Pick which I should implement next and I'll update the plan and start coding.
