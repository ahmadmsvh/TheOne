# CI/CD Pipeline Tutorial - Using TheOne Project as Example

## Table of Contents
1. [What is CI/CD?](#what-is-cicd)
2. [Key Concepts](#key-concepts)
3. [Understanding Your Workflow File](#understanding-your-workflow-file)
4. [Step-by-Step Breakdown](#step-by-step-breakdown)
5. [Common CI/CD Patterns](#common-cicd-patterns)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## What is CI/CD?

### CI (Continuous Integration)
**Definition:** Automatically testing and building your code every time someone pushes changes.

**Why it matters:** 
- Catches bugs early before they reach production
- Ensures code quality
- Prevents "it works on my machine" problems

**Real-world analogy:** Like a quality control checkpoint in a factory. Every product (code change) is automatically tested before it can proceed.

### CD (Continuous Deployment/Delivery)
**Definition:** Automatically deploying your code to production after it passes all tests.

**Why it matters:**
- Faster delivery of features
- Consistent deployments
- Less manual work

**Real-world analogy:** Like an automated delivery system that ships products (code) to customers (production) after quality checks pass.

---

## Key Concepts

### 1. **Workflow/Pipeline**
A workflow is a series of automated steps that run when triggered.

**In your project:** The file `.github/workflows/ci-cd.yml` defines your workflow.

### 2. **Trigger**
An event that starts the workflow (like pushing code).

**In your project:**
```yaml
on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
```
This means: "Run the workflow when code is pushed to main branch OR when someone creates a pull request to main."

### 3. **Job**
A job is a set of steps that run on the same machine. Jobs can run in parallel or sequentially.

**In your project, you have 4 jobs:**
- `test` - Runs your tests
- `build` - Builds Docker images
- `build-notification-worker` - Builds the worker image
- `lint` - Checks code quality

### 4. **Step**
A step is a single action within a job (like installing dependencies or running a command).

**Example from your project:**
```yaml
- name: Install auth-service dependencies
  working-directory: ./auth-service
  run: |
    pip install -r requirements.txt
```

### 5. **Runner**
The machine (virtual or physical) where your jobs run. GitHub provides free runners (Ubuntu, Windows, macOS).

**In your project:**
```yaml
runs-on: ubuntu-latest
```
This means: "Run this job on a fresh Ubuntu Linux machine."

---

## Understanding Your Workflow File

Let's break down your actual workflow file line by line:

### Header Section
```yaml
name: CI/CD Pipeline
```
**What it does:** Gives your workflow a name (shows up in GitHub Actions UI)

```yaml
env:
  PYTHON_VERSION: '3.11'
  DOCKER_BUILDKIT: 1
```
**What it does:** Sets environment variables that all jobs can use. Like global settings.

### Trigger Section
```yaml
on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
```
**What it does:** 
- Triggers on push to `main` branch
- Also triggers on pull requests to `main` (so you can test before merging)

**Why both?** 
- Push to main = "This code is ready, deploy it!"
- Pull request = "Check if this code is good before merging"

---

## Step-by-Step Breakdown

### Job 1: `test` - Running Tests

```yaml
test:
  name: Run Tests
  runs-on: ubuntu-latest
```

**What happens:**
1. GitHub spins up a fresh Ubuntu Linux machine
2. This machine is completely clean (no previous code or dependencies)

#### Services (Database Containers)
```yaml
services:
  postgres:
    image: postgres:15-alpine
    env:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
```
**What it does:** Starts a PostgreSQL database in a container, just like your local setup.

**Why?** Your tests need a database to run. Instead of installing PostgreSQL on the runner, we use a container (faster and cleaner).

#### Steps Breakdown

**Step 1: Checkout Code**
```yaml
- name: Checkout code
  uses: actions/checkout@v4
```
**What it does:** Downloads your code from GitHub to the runner.

**Why?** The runner starts empty. This step gets your code.

**Step 2: Set up Python**
```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: ${{ env.PYTHON_VERSION }}
```
**What it does:** Installs Python 3.11 on the runner.

**The `${{ }}` syntax:** This is GitHub Actions templating. It substitutes the value of `PYTHON_VERSION` (which is '3.11').

**Step 3: Install Shared Package**
```yaml
- name: Install shared package
  working-directory: ./shared
  run: |
    pip install --upgrade pip
    pip install -e .
```
**What it does:** 
- Goes to the `shared` directory
- Upgrades pip
- Installs your shared package in "editable" mode (`-e`)

**Why editable?** Changes to shared code are immediately available without reinstalling.

**Step 4: Install Dependencies**
```yaml
- name: Install auth-service dependencies
  working-directory: ./auth-service
  run: |
    pip install -r requirements.txt
```
**What it does:** Installs all Python packages your auth-service needs (FastAPI, SQLAlchemy, etc.)

**Step 5: Install PostgreSQL Client**
```yaml
- name: Install PostgreSQL client
  run: |
    sudo apt-get update
    sudo apt-get install -y postgresql-client
```
**What it does:** Installs the `psql` command-line tool so we can create databases.

**Step 6: Run Tests**
```yaml
- name: Run auth-service tests
  working-directory: ./auth-service
  env:
    DATABASE_URL: postgresql://postgres:postgres@localhost:5432/theone_auth_db
    REDIS_URL: redis://localhost:6379
    SECRET_KEY: test-secret-key-for-ci
  run: |
    PGPASSWORD=postgres psql -h localhost -U postgres -c "CREATE DATABASE theone_auth_db;" || true
    alembic upgrade head || true
    pytest
```

**Breaking this down:**
- `env:` - Sets environment variables (like setting them in your terminal)
- `DATABASE_URL` - Tells your app where the database is
- `|| true` - Means "if this command fails, don't stop" (useful if database already exists)
- `alembic upgrade head` - Runs database migrations (creates tables)
- `pytest` - Runs your actual tests

**What happens if tests fail?** The entire workflow stops, and you get a notification.

---

### Job 2: `build` - Building Docker Images

```yaml
build:
  name: Build Docker Images
  runs-on: ubuntu-latest
  needs: test
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

**Key concepts:**
- `needs: test` - **Job dependency**. This job only runs AFTER the `test` job succeeds.
- `if:` - **Conditional execution**. Only runs on pushes to main (not on pull requests).

**Why not build on PRs?** 
- Saves resources (no need to build if tests fail)
- PRs are for review, not deployment

#### Matrix Strategy
```yaml
strategy:
  matrix:
    service:
      - auth-service
      - notification-service
      - order-service
      - product-service
```

**What it does:** Creates 4 parallel jobs, one for each service.

**Why?** Instead of building services one by one (slow), build them all at once (fast).

**Visual representation:**
```
Without matrix:  auth → notification → order → product  (4 minutes)
With matrix:     auth ┐
                 notification ┤
                 order        ├── All at once (1 minute)
                 product ┘
```

#### Build Steps
```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3
```
**What it does:** Sets up advanced Docker building features (like caching).

```yaml
- name: Build Docker image for ${{ matrix.service }}
  uses: docker/build-push-action@v5
  with:
    context: .
    file: ./${{ matrix.service }/Dockerfile
    push: false
    tags: theone-${{ matrix.service }}:latest
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

**Breaking this down:**
- `context: .` - Build context (where Docker looks for files)
- `file:` - Which Dockerfile to use
- `push: false` - Build but don't push to registry (yet)
- `tags:` - What to name the image
- `cache-from/cache-to: type=gha` - **Caching!** Saves build layers between runs (much faster)

**What is caching?** 
- First build: Takes 5 minutes (builds everything)
- Second build: Takes 1 minute (reuses unchanged layers)

---

### Job 3: `build-notification-worker` - Special Worker Build

```yaml
build-notification-worker:
  name: Build Notification Worker Image
  needs: test
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

**Why separate?** The notification worker uses a different Dockerfile (`Dockerfile.worker`), so it needs its own build job.

**Same pattern as `build` job, just for one specific service.**

---

### Job 4: `lint` - Code Quality Checks

```yaml
lint:
  name: Code Quality Checks
  runs-on: ubuntu-latest
```

**What is linting?** Checking code style and quality (like a spell-checker for code).

**Why run separately?** 
- Can run in parallel with tests (faster)
- Different tools, different purpose

#### Linting Steps

**Black (Code Formatter)**
```yaml
- name: Check code formatting with black
  run: |
    black --check --diff auth-service/ ... || true
```
**What it does:** Checks if your code follows formatting rules (spaces, line length, etc.)

**`--check`** - Don't fix, just check
**`--diff`** - Show what would change
**`|| true`** - Don't fail the pipeline (currently just warnings)

**isort (Import Sorter)**
```yaml
- name: Check import sorting with isort
  run: |
    isort --check-only --diff ...
```
**What it does:** Checks if your Python imports are sorted correctly.

**flake8 (Linter)**
```yaml
- name: Lint with flake8
  run: |
    flake8 ... --count --select=E9,F63,F7,F82 ...
```
**What it does:** Finds code issues (unused variables, syntax errors, etc.)

**The `--select=E9,F63,F7,F82`** - Only check for critical errors (not style warnings)

---

## Common CI/CD Patterns

### Pattern 1: Job Dependencies
```yaml
build:
  needs: test
```
**Meaning:** "Don't build if tests fail"

**Your workflow flow:**
```
test ──┐
       ├──> build (only if test passes)
lint ──┘
```

### Pattern 2: Conditional Execution
```yaml
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```
**Meaning:** "Only run on pushes to main, not on pull requests"

**Use cases:**
- Builds: Only on main (saves resources)
- Deployments: Only on main (don't deploy PR code)
- Tests: Run on both (catch issues early)

### Pattern 3: Matrix Strategy
```yaml
strategy:
  matrix:
    service: [auth-service, notification-service, ...]
```
**Meaning:** "Run the same job multiple times with different values"

**Benefits:**
- Parallel execution (faster)
- Less code duplication
- Easy to add new services

### Pattern 4: Environment Variables
```yaml
env:
  DATABASE_URL: postgresql://...
```
**Meaning:** "Set these variables for this step/job"

**Why?** Your code reads from environment variables. CI needs to provide them.

### Pattern 5: Service Containers
```yaml
services:
  postgres:
    image: postgres:15-alpine
```
**Meaning:** "Start this container before the job runs"

**Why?** Your app needs databases, Redis, etc. Services provide them automatically.

---

## Best Practices

### 1. **Fail Fast**
Run quick checks first (linting, unit tests) before slow operations (builds, integration tests).

**Your workflow does this:** `lint` and `test` run in parallel, both must pass before `build`.

### 2. **Cache Everything**
Use caching for:
- Dependencies (pip packages)
- Docker layers
- Build artifacts

**Your workflow:** Uses Docker layer caching (`cache-from: type=gha`)

### 3. **Parallel Execution**
Run independent jobs in parallel.

**Your workflow:**
- `test` and `lint` run in parallel (they don't depend on each other)
- `build` matrix runs services in parallel

### 4. **Clear Job Names**
```yaml
name: Run Tests  # Good - clear what it does
name: Job 1      # Bad - unclear
```

### 5. **Use Secrets for Sensitive Data**
Never hardcode passwords or API keys. Use GitHub Secrets.

**Example:**
```yaml
env:
  DATABASE_PASSWORD: ${{ secrets.DATABASE_PASSWORD }}
```

### 6. **Test Before Deploy**
Always run tests before building/deploying.

**Your workflow:** `build` has `needs: test`

---

## Troubleshooting

### Problem: "Tests fail but I don't know why"

**Solution:** Check the workflow logs in GitHub:
1. Go to your repository
2. Click "Actions" tab
3. Click on the failed workflow run
4. Click on the failed job
5. Expand the failed step to see error messages

### Problem: "Build is slow"

**Solutions:**
1. Enable caching (you already have this!)
2. Use matrix strategy for parallel builds (you have this!)
3. Only build what changed (advanced: use path filters)

### Problem: "Tests pass locally but fail in CI"

**Common causes:**
1. **Different environment** - CI uses fresh Ubuntu, you might have different packages
2. **Missing environment variables** - Check the `env:` section
3. **Database not ready** - Check service health checks
4. **Timing issues** - Add waits or retries

**Debugging tip:** Add debug output:
```yaml
- name: Debug info
  run: |
    echo "Python version: $(python --version)"
    echo "Database URL: $DATABASE_URL"
    pip list
```

### Problem: "I want to skip CI for a commit"

**Solution:** Add `[skip ci]` or `[ci skip]` to your commit message:
```bash
git commit -m "Update README [skip ci]"
```

### Problem: "How do I test the workflow before pushing?"

**Solution:** Create a pull request! The workflow runs on PRs too (for the `test` and `lint` jobs).

---

## Understanding the Flow

Here's what happens when you push to main:

```
1. You push code to main branch
   ↓
2. GitHub detects the push
   ↓
3. Workflow starts
   ↓
4. Three jobs start in parallel:
   ├── test (runs tests)
   ├── lint (checks code quality)
   └── (build waits - needs test)
   ↓
5. If test passes:
   ├── build job starts (builds all services in parallel)
   └── build-notification-worker starts
   ↓
6. If everything passes:
   └── ✅ Green checkmark in GitHub
   ↓
7. (Future) Deploy job would run here
```

**If anything fails:**
- ❌ Red X in GitHub
- You get an email notification
- You can see exactly what failed in the logs

---

## Next Steps

### 1. **Enable Container Registry Push**
Uncomment the registry push sections in your workflow to publish Docker images.

### 2. **Add More Tests**
Add test jobs for other services (order-service, product-service) when you add tests.

### 3. **Configure Deployment**
Uncomment and configure the `deploy` job when ready to deploy.

### 4. **Add Notifications**
Configure Slack/Discord/email notifications for workflow results.

### 5. **Add Security Scanning**
Add jobs to scan for vulnerabilities in dependencies and Docker images.

---

## Key Takeaways

1. **CI/CD automates repetitive tasks** - No more manual testing and deployment
2. **Fail fast** - Catch problems early before they reach production
3. **Everything is code** - Your workflow file is version-controlled
4. **Parallel is faster** - Run independent jobs simultaneously
5. **Cache everything** - Speed up builds with caching
6. **Test before deploy** - Always verify code works before deploying

---

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Docker Buildx](https://docs.docker.com/build/buildx/)
- [Pytest Documentation](https://docs.pytest.org/)

---

**Remember:** CI/CD is about automation and confidence. Every time you push code, you know it's been tested and is ready to deploy!
