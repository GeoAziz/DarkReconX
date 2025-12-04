# DarkReconX v1.0 Deployment & Release Guide

Comprehensive guide for deploying DarkReconX v1.0 to production environments.

## 📋 Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Installation Methods](#installation-methods)
3. [Configuration for Production](#configuration-for-production)
4. [Running the Service](#running-the-service)
5. [Monitoring & Logging](#monitoring--logging)
6. [Docker Deployment](#docker-deployment)
7. [Team Deployment](#team-deployment)
8. [Troubleshooting](#troubleshooting)
9. [Rollback Procedures](#rollback-procedures)

---

## ✅ Pre-Deployment Checklist

Before deploying DarkReconX to production, ensure:

### Code Quality
- [ ] Flake8 clean: `flake8 . --count`
- [ ] Type checks pass: `mypy core/ modules/ cli/`
- [ ] All tests pass: `pytest tests/ -v`
- [ ] No hardcoded secrets: `grep -r "api_key\|password" . --include="*.py" | grep -v "os.environ\|.env"`

### Dependencies
- [ ] All dependencies pinned: `pip freeze | grep -E "requests==|httpx==|rich=="`
- [ ] No vulnerable packages: `safety check`
- [ ] Virtual environment active: `which python | grep venv`

### Configuration
- [ ] `.env.example` exists with all keys documented
- [ ] API keys obtained for required providers
- [ ] Cache directory writable: `mkdir -p ~/.darkreconx_cache && touch ~/.darkreconx_cache/test.txt`
- [ ] Log directory writable: `mkdir -p logs && touch logs/test.log`

### Documentation
- [ ] README.md up-to-date
- [ ] ONBOARDING.md complete
- [ ] CHANGELOG.md updated for this version
- [ ] All commands documented

### Testing
- [ ] Manual test scan completed: `darkreconx pipeline --targets example.com`
- [ ] Cache working: Run same command twice, verify fast execution
- [ ] Export formats working: Test `--format json`, `--format csv`, `--format html`
- [ ] Error handling tested: Run with invalid API keys, verify graceful degradation

---

## 📦 Installation Methods

### Option 1: Development Installation (Recommended for Team)

```bash
# Clone repository
git clone https://github.com/GeoAziz/DarkReconX.git
cd DarkReconX

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or: venv\Scripts\Activate on Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Verify installation
pytest tests/ -v  # Should see 51 passed
darkreconx --help  # Should show command list
```

### Option 2: Production Installation (Package)

```bash
# Create virtual environment
python3 -m venv /opt/darkreconx/venv
source /opt/darkreconx/venv/bin/activate

# Install from PyPI (when released)
pip install darkreconx

# Or install from local wheel
pip install dist/darkreconx-1.0.0-py3-none-any.whl

# Verify
darkreconx --help
```

### Option 3: Docker Installation

```bash
# Build image
docker build -t darkreconx:1.0 .

# Run container
docker run -it \
  -e VT_API_KEY="your_key" \
  -e SHODAN_API_KEY="your_key" \
  -v $(pwd)/results:/app/results \
  darkreconx:1.0

# Or with docker-compose
docker-compose up -d darkreconx
```

---

## ⚙️ Configuration for Production

### Create Production .env File

```bash
# Copy template
cp .env.example .env

# Edit with your API keys
nano .env
```

### .env Template (Production)

```bash
# ===== API KEYS (Required) =====
VT_API_KEY=your_virustotal_api_key
SHODAN_API_KEY=your_shodan_api_key
DNSDB_API_KEY=your_dnsdb_api_key
CENSYS_API_ID=your_censys_id
CENSYS_API_SECRET=your_censys_secret
IPINFO_API_TOKEN=your_ipinfo_token
WHOISXML_API_KEY=your_whoisxml_key

# ===== CACHE (Optional) =====
DARKRECONX_CACHE_TTL=86400      # 24 hours
DARKRECONX_NO_CACHE=0
DARKRECONX_REFRESH_CACHE=0

# ===== PERFORMANCE (Optional) =====
DARKRECONX_MAX_WORKERS=50       # Concurrent workers
DARKRECONX_TIMEOUT=30           # Request timeout (seconds)
DARKRECONX_RETRY_ATTEMPTS=3     # Failed request retries

# ===== TOR (Optional) =====
TOR_ENABLED=false
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051
TOR_PASSWORD=

# ===== LOGGING (Optional) =====
DARKRECONX_LOG_LEVEL=INFO       # DEBUG, INFO, WARNING, ERROR
DARKRECONX_LOG_FILE=logs/darkreconx.log
```

### Security Considerations

1. **Never commit `.env` to git**
   ```bash
   # Verify .env is in .gitignore
   grep ".env" .gitignore
   ```

2. **Restrict file permissions**
   ```bash
   chmod 600 .env
   chmod 700 ~/.darkreconx_cache/
   chmod 700 logs/
   ```

3. **Use environment variables in CI/CD**
   ```bash
   # Instead of .env file, use secrets in GitHub Actions
   export VT_API_KEY="${VT_API_KEY}"
   export SHODAN_API_KEY="${SHODAN_API_KEY}"
   ```

---

## 🚀 Running the Service

### Command-Line Usage

```bash
# Basic pipeline scan
darkreconx pipeline --targets example.com --outdir results/prod_scan

# With custom workers and timeout
darkreconx pipeline \
  --targets targets.txt \
  --max-workers 20 \
  --outdir results/prod_scan \
  --format json

# Enrich single target
darkreconx enrich 8.8.8.8 --type ip --providers virustotal,shodan

# View cache statistics
darkreconx cache --stats

# Test provider connectivity
darkreconx test-providers
```

### Batch Processing

```bash
# Create targets file
cat > targets.txt << 'EOF'
example.com
google.com
github.com
EOF

# Run pipeline
darkreconx pipeline --targets targets.txt --outdir results/batch_2025_12_04

# Monitor progress (watch results directory)
watch 'ls -lah results/batch_2025_12_04/'
```

### Scheduling with Cron

```bash
# Add to crontab
crontab -e

# Daily reconnaissance at 2 AM
0 2 * * * /opt/darkreconx/venv/bin/darkreconx pipeline --targets /etc/darkreconx/targets.txt --outdir /var/darkreconx/results --format json >> /var/log/darkreconx_cron.log 2>&1

# Weekly cache cleanup
0 3 * * 0 /opt/darkreconx/venv/bin/darkreconx cache --clear
```

### Systemd Service (Optional)

```bash
# Create service file
sudo tee /etc/systemd/system/darkreconx.service << 'EOF'
[Unit]
Description=DarkReconX OSINT Service
After=network.target

[Service]
Type=simple
User=darkreconx
WorkingDirectory=/opt/darkreconx
EnvironmentFile=/opt/darkreconx/.env
ExecStart=/opt/darkreconx/venv/bin/darkreconx pipeline --targets /etc/darkreconx/targets.txt
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable darkreconx
sudo systemctl start darkreconx
```

---

## 📊 Monitoring & Logging

### Enable File Logging

```bash
# Set log file
export DARKRECONX_LOG_FILE=logs/darkreconx.log
export DARKRECONX_LOG_LEVEL=INFO

# Run with logging
darkreconx pipeline --targets example.com --verbose
```

### View Logs

```bash
# Real-time log monitoring
tail -f logs/darkreconx.log

# View recent errors
grep ERROR logs/darkreconx.log | tail -20

# Log statistics
wc -l logs/darkreconx.log
du -h logs/darkreconx.log
```

### Log Rotation

```bash
# Create logrotate configuration
sudo tee /etc/logrotate.d/darkreconx << 'EOF'
/var/log/darkreconx.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 darkreconx darkreconx
    sharedscripts
    postrotate
        systemctl reload darkreconx > /dev/null 2>&1 || true
    endscript
}
EOF
```

### Monitoring Performance

```bash
# Monitor memory and CPU
ps aux | grep darkreconx

# Check cache disk usage
du -sh ~/.darkreconx_cache/

# Performance metrics
darkreconx cache --stats

# Rate limit status
darkreconx rate-limit --show
```

---

## 🐳 Docker Deployment

### Build Docker Image

```bash
# Build image
docker build -t darkreconx:1.0 -f docker/Dockerfile .

# Build with build args
docker build \
  --build-arg PYTHON_VERSION=3.11 \
  -t darkreconx:1.0 .

# Tag for registry
docker tag darkreconx:1.0 myregistry.azurecr.io/darkreconx:1.0
```

### Run Container

```bash
# Interactive mode
docker run -it \
  -e VT_API_KEY="your_key" \
  -e SHODAN_API_KEY="your_key" \
  -v $(pwd)/.env:/app/.env:ro \
  -v $(pwd)/results:/app/results \
  darkreconx:1.0 \
  darkreconx pipeline --targets example.com

# Detached mode (background)
docker run -d \
  --name darkreconx_prod \
  -e VT_API_KEY="your_key" \
  -e SHODAN_API_KEY="your_key" \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/logs:/app/logs \
  darkreconx:1.0

# Access container shell
docker exec -it darkreconx_prod /bin/bash
```

### Docker Compose

```bash
# Use docker-compose.yml
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down

# Restart service
docker-compose restart
```

### Docker Swarm / Kubernetes

```bash
# Docker Stack
docker stack deploy -c docker-compose.yml darkreconx

# Kubernetes Deployment
kubectl apply -f k8s/darkreconx-deployment.yaml
```

---

## 👥 Team Deployment

### Initial Team Setup

```bash
# 1. Each team member clones repo
git clone https://github.com/GeoAziz/DarkReconX.git
cd DarkReconX

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dev dependencies
pip install -e ".[dev]"

# 4. Run tests to verify
pytest tests/ -v

# 5. Copy .env template
cp .env.example .env

# 6. Add personal API keys
nano .env

# 7. Run first scan
darkreconx pipeline --targets example.com
```

### Team Collaboration

```bash
# Create feature branch
git checkout -b feature/my-enhancement

# Make changes
vim core/module.py

# Run tests
pytest tests/ -v

# Check code quality
black . && isort . && flake8 .

# Commit changes
git add .
git commit -m "Feature: Add X, fix Y"

# Push to origin
git push origin feature/my-enhancement

# Create Pull Request on GitHub
# (wait for code review)

# Merge when approved
```

---

## 🆘 Troubleshooting

### Issue: "Command not found: darkreconx"

**Solution**:
```bash
# Check if virtual environment is active
which python | grep venv

# If not, activate it
source venv/bin/activate

# Reinstall in editable mode
pip install -e .

# Verify
darkreconx --help
```

### Issue: "API key not found"

**Solution**:
```bash
# Check .env file
cat .env | grep VT_API_KEY

# Or check environment
echo $VT_API_KEY

# If empty, set it
export VT_API_KEY="your_key"

# Test
darkreconx test-providers
```

### Issue: "No space left on device"

**Solution**:
```bash
# Check disk space
df -h

# Clear cache to free space
darkreconx cache --clear

# Check cache size
du -sh ~/.darkreconx_cache/

# If still full, clean old results
rm -rf results/old_scans_*
```

### Issue: "Port 9050 already in use" (Tor)

**Solution**:
```bash
# Disable Tor
export TOR_ENABLED=false

# Or change Tor port
export TOR_SOCKS_PORT=9051

# Or kill existing Tor
pkill tor
systemctl restart tor
```

---

## ⬅️ Rollback Procedures

### If v1.0 Has Critical Issues

```bash
# 1. Identify issue
darkreconx pipeline --targets example.com --verbose

# 2. Check version
pip show darkreconx | grep Version

# 3. Rollback to previous version (if needed)
pip install darkreconx==0.1.0

# 4. Or reinstall from git tag
git checkout v1.0.0  # or previous tag
pip install -e .

# 5. Verify rollback
darkreconx --help
pytest tests/ -v
```

### Emergency Hotfix

```bash
# 1. Create hotfix branch
git checkout -b hotfix/v1.0.1

# 2. Fix issue
vim core/module.py

# 3. Run tests
pytest tests/ -v

# 4. Update version
# Edit pyproject.toml and setup.py: version = "1.0.1"

# 5. Test thoroughly
pytest tests/ -v

# 6. Commit and tag
git add .
git commit -m "Hotfix: Fix critical issue"
git tag v1.0.1
git push origin hotfix/v1.0.1 --tags

# 7. Reinstall
pip install -e .

# 8. Verify
darkreconx --help
```

---

## 📝 Post-Deployment Checklist

After successful deployment:

- [ ] Verify all providers are working: `darkreconx test-providers`
- [ ] Run test scan: `darkreconx pipeline --targets example.com`
- [ ] Check cache: `darkreconx cache --stats`
- [ ] Monitor logs: `tail -f logs/darkreconx.log`
- [ ] Document configuration: `cat .env | grep -v "^#"`
- [ ] Update team: Notify of successful v1.0 deployment
- [ ] Collect feedback: Ask team for issues/improvements
- [ ] Monitor for 24 hours: Watch for any anomalies

---

## 📞 Support & Rollback

**If Issues Arise**:
1. Check logs: `tail -f logs/darkreconx.log`
2. Review troubleshooting: See section above
3. Rollback if needed: See rollback procedures
4. Contact team lead: GeoAziz@darkreconx
5. Open GitHub issue: github.com/GeoAziz/DarkReconX/issues

---

**Deployment v1.0 Complete** ✅

DarkReconX is now ready for production use!

