# DarkReconX Demo Script

Purpose: show a 3–5 minute demo of the basic features and safe defaults.

Steps:

1. Introduce the problem: attack surface discovery for an authorised target.
2. Show the repo structure and ethics note.
3. Run the example script: `./examples/example_run.sh`.
4. Open `examples/results/sample.example.com.json` and `examples/report_sample.md` to show outputs.
5. Show the API endpoints: `POST /generate_report` and `GET /reports/{target}` (local demo using `http`ie or curl).

Safety note: this demo runs against a controlled demo target and uses the `--fast` flag.
