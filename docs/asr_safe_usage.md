# Attack Surface Recon — Safe Usage & Ethics

The Attack Surface Recon (ASR) features in DarkReconX are powerful and must be used responsibly.

## Permission and Ethics

- Only scan targets you own or for which you have explicit, written permission.
- Do NOT scan third-party or unauthorised hosts.
- Keep records of consent and scope for each engagement.

## Safe Defaults

DarkReconX ASR defaults to conservative, non-destructive checks:

- Safe mode: HEAD-only for web path checks (disabled by default in CLI when --no-safe-mode is used)
- Low timeouts and low concurrency
- No payload injection, no authentication attempts

## Running ASR (example)

Create a `targets.txt` containing allowed targets (one per line) and ensure you have permission.

Activate your venv and run:

```bash
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python cli/main.py asr --targets targets.txt --max-workers 20 --safe-mode --output results/asr_summary.json
```

## Documentation & Record Keeping

For each ASR run, maintain a record of:
- Who authorised the scan
- Allowed IPs/domains
- Date/time and duration
- Results and remediation actions taken

## Remediation Guidance

The tool provides defensive remediation suggestions for each flagged issue. These are recommendations only; review with your security team and apply best practices.

If you need to perform more aggressive scanning (nmap/naabu), ensure explicit permission and enable those tools deliberately and separately.
