# Release Guide for DarkReconX v0.1.0

This guide walks through the steps to officially release DarkReconX v0.1.0 on GitHub.

## Prerequisites

- Git and GitHub CLI (`gh`) installed and authenticated
- Tag not yet created (or force-push if needed)

## Steps

### 1. Create Git Tag

```bash
git tag -a v0.1.0 -m "DarkReconX v0.1.0 - initial public release"
```

### 2. Push Tag to GitHub

```bash
git push origin v0.1.0
```

### 3. Create GitHub Release

```bash
gh release create v0.1.0 --title "v0.1.0 - DarkReconX" --notes-file CHANGELOG.md
```

### 4. (Optional) Build and Push Docker Image

If you have Docker Hub credentials:

```bash
docker build -t geoaziz/darkreconx:0.1.0 -f docker/Dockerfile .
docker tag geoaziz/darkreconx:0.1.0 geoaziz/darkreconx:latest
docker push geoaziz/darkreconx:0.1.0
docker push geoaziz/darkreconx:latest
```

### 5. (Optional) Publish to PyPI

If you have PyPI credentials:

```bash
python -m build
twine upload dist/*
```

## Verification

After release, verify:

- GitHub Releases page shows v0.1.0
- Tag `v0.1.0` exists in the repo
- CI workflow runs (if enabled)
- Example script works: `./examples/example_run.sh`

## Next Steps

- Monitor issues and PRs
- Update GitHub Project board with feedback
- Plan Day 15+ enhancements
