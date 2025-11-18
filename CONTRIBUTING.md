# Contributing to DarkReconX

Thanks for your interest in contributing! We welcome bug reports, feature
requests, and pull requests — especially modular tools that fit the
`modules/` structure.

Getting started

1. Fork the repository and create a new branch for your change.
2. Run tests locally and make sure they pass.
3. Add clear documentation and unit tests for new behavior.

Module guidelines

- Each module must live under `modules/<module_name>/` and expose a
  `scanner.py` with either a class (e.g., `MyModule`) that implements a
  `run()`-like method, or a top-level `run()` function.
- Prefer dependency-free code or add dependencies to `requirements.txt` with
  justification in your PR.
- Be respectful of local laws — do not include code meant to facilitate
  illegal activity.

Style

- Use 4-space indentation and clear docstrings.
- Keep modules small and focused.

Pull requests

- Target the `main` branch.
- Include a short description of changes and testing steps in your PR.
- Ensure CI passes.

Security

If you find a security issue, please open a private issue and avoid
publishing exploit details publicly.
