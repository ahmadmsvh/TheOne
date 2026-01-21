# CI/CD Quick Reference Guide

## Workflow File Location
```
.github/workflows/ci-cd.yml
```

## What Triggers the Workflow?
- ✅ Push to `main` branch
- ✅ Pull request to `main` branch

## Jobs Overview

| Job | What It Does | When It Runs | Depends On |
|-----|--------------|--------------|------------|
| `test` | Runs auth-service tests | Every push/PR | None |
| `lint` | Checks code quality | Every push/PR | None |
| `build` | Builds Docker images | Only on push to main | `test` must pass |
| `build-notification-worker` | Builds worker image | Only on push to main | `test` must pass |

## Common Commands

### View Workflow Status
1. Go to your GitHub repository
2. Click "Actions" tab
3. See all workflow runs

### View Logs
1. Click on a workflow run
2. Click on a job
3. Expand steps to see output

### Re-run Failed Workflow
1. Go to failed workflow run
2. Click "Re-run jobs" button

## Environment Variables in Workflow

| Variable | Value | Used By |
|----------|-------|---------|
| `PYTHON_VERSION` | `3.11` | All Python jobs |
| `DOCKER_BUILDKIT` | `1` | Docker builds |
| `DATABASE_URL` | `postgresql://...` | Test job |
| `REDIS_URL` | `redis://localhost:6379` | Test job |
| `SECRET_KEY` | `test-secret-key-for-ci` | Test job |

## Workflow Flow Diagram

```
Push to main
    │
    ├─► test ──────────┐
    │                   │
    └─► lint ───────────┤
                        │
                        ▼
                   build (if test passes)
                        │
                        ├─► auth-service
                        ├─► notification-service
                        ├─► order-service
                        └─► product-service
                        │
                        ▼
              build-notification-worker
```

## Key Concepts Cheat Sheet

### `on:` - When to run
```yaml
on:
  push:
    branches: [main]      # Run on push to main
  pull_request:           # Run on PRs
```

### `jobs:` - What to do
```yaml
jobs:
  my-job:
    runs-on: ubuntu-latest  # Where to run
    steps:                  # What steps to execute
      - name: Step 1
        run: echo "Hello"
```

### `needs:` - Job dependencies
```yaml
build:
  needs: test  # Only run if test passes
```

### `if:` - Conditional execution
```yaml
if: github.ref == 'refs/heads/main'  # Only on main branch
```

### `strategy.matrix:` - Parallel execution
```yaml
strategy:
  matrix:
    service: [service1, service2]  # Run for each value
```

### `env:` - Environment variables
```yaml
env:
  MY_VAR: value  # Available in all steps
```

### `services:` - Container services
```yaml
services:
  postgres:
    image: postgres:15-alpine  # Start this container
```

## Common Patterns

### Pattern: Install Dependencies
```yaml
- name: Install dependencies
  run: pip install -r requirements.txt
```

### Pattern: Run Tests
```yaml
- name: Run tests
  run: pytest
```

### Pattern: Build Docker Image
```yaml
- name: Build image
  uses: docker/build-push-action@v5
  with:
    context: .
    file: ./Dockerfile
```

### Pattern: Conditional Step
```yaml
- name: Deploy
  if: github.ref == 'refs/heads/main'
  run: ./deploy.sh
```

## Debugging Tips

### Add Debug Output
```yaml
- name: Debug
  run: |
    echo "Python: $(python --version)"
    echo "PWD: $(pwd)"
    ls -la
```

### Check Service Health
```yaml
- name: Check database
  run: |
    psql -h localhost -U postgres -c "SELECT 1;"
```

### See Environment Variables
```yaml
- name: Show env vars
  run: env | grep DATABASE
```

## Status Icons

- ✅ Green checkmark = All jobs passed
- ❌ Red X = One or more jobs failed
- 🟡 Yellow circle = Job is running
- ⏸️ Gray square = Job was cancelled

## Skip CI

Add to commit message to skip workflow:
```
[skip ci]
[ci skip]
```

## GitHub Actions Syntax

### Variables
```yaml
${{ env.PYTHON_VERSION }}     # Environment variable
${{ github.ref }}              # Git reference
${{ github.sha }}              # Commit SHA
${{ github.actor }}            # Username who triggered
${{ matrix.service }}          # Matrix variable
```

### Secrets
```yaml
${{ secrets.MY_SECRET }}       # Secret from GitHub settings
```

## File Structure

```
.github/
  workflows/
    ci-cd.yml          # Your workflow file
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Tests fail in CI but pass locally | Check environment variables, database setup |
| Build is slow | Enable caching (already done!) |
| Can't find file | Check `working-directory` and paths |
| Service not ready | Add health checks or wait steps |
| Permission denied | Check file permissions, use `sudo` if needed |

## Next Steps

1. ✅ Workflow is created and ready
2. ⏳ Push to main to trigger first run
3. ⏳ Monitor results in GitHub Actions tab
4. ⏳ Configure deployment when ready
5. ⏳ Add more test jobs for other services

---

**Pro Tip:** Always check the Actions tab after pushing to see if your workflow runs successfully!
