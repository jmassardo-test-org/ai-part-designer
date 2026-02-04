# CI/CD Pipeline Configuration
# AI Part Designer

**Version:** 1.0  
**Date:** 2026-01-24  

---

## Overview

This document describes the CI/CD pipeline architecture using GitHub Actions for automated testing, building, and deployment.

---

## Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CI/CD PIPELINE OVERVIEW                            │
└─────────────────────────────────────────────────────────────────────────────┘

Pull Request:
  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
  │  Lint   │───>│  Type   │───>│  Unit   │───>│  Build  │───>│ Preview │
  │  Check  │    │  Check  │    │  Tests  │    │  Check  │    │  (opt)  │
  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘

Merge to main:
  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
  │  Build  │───>│ Integ.  │───>│ Docker  │───>│ Deploy  │───>│ Smoke   │
  │  & Test │    │  Tests  │    │  Build  │    │ Staging │    │  Tests  │
  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘

Release tag (v*.*.*):
  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
  │  Build  │───>│   E2E   │───>│  Build  │───>│ Deploy  │───>│ Monitor │
  │  & Test │    │  Tests  │    │  Images │    │  Prod   │    │ & Alert │
  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
```

---

## GitHub Actions Workflows

### 1. Pull Request CI (`.github/workflows/ci.yml`)

```yaml
name: CI

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '20'
  PNPM_VERSION: '8'

jobs:
  # ============================================================================
  # Frontend Checks
  # ============================================================================
  frontend-lint:
    name: Frontend Lint & Type Check
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup pnpm
        uses: pnpm/action-setup@v2
        with:
          version: ${{ env.PNPM_VERSION }}
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'pnpm'
          cache-dependency-path: frontend/pnpm-lock.yaml
      
      - name: Install dependencies
        run: pnpm install --frozen-lockfile
      
      - name: Run ESLint
        run: pnpm run lint
      
      - name: Run TypeScript check
        run: pnpm run typecheck
      
      - name: Run Prettier check
        run: pnpm run format:check

  frontend-test:
    name: Frontend Tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup pnpm
        uses: pnpm/action-setup@v2
        with:
          version: ${{ env.PNPM_VERSION }}
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'pnpm'
          cache-dependency-path: frontend/pnpm-lock.yaml
      
      - name: Install dependencies
        run: pnpm install --frozen-lockfile
      
      - name: Run tests with coverage
        run: pnpm run test:coverage
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: frontend/coverage/lcov.info
          flags: frontend
          fail_ci_if_error: true

  frontend-build:
    name: Frontend Build
    runs-on: ubuntu-latest
    needs: [frontend-lint, frontend-test]
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup pnpm
        uses: pnpm/action-setup@v2
        with:
          version: ${{ env.PNPM_VERSION }}
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'pnpm'
          cache-dependency-path: frontend/pnpm-lock.yaml
      
      - name: Install dependencies
        run: pnpm install --frozen-lockfile
      
      - name: Build
        run: pnpm run build
      
      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: frontend-build
          path: frontend/dist
          retention-days: 7

  # ============================================================================
  # Backend Checks
  # ============================================================================
  backend-lint:
    name: Backend Lint & Type Check
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: '1.7.1'
          virtualenvs-create: true
          virtualenvs-in-project: true
      
      - name: Load cached venv
        uses: actions/cache@v4
        with:
          path: backend/.venv
          key: venv-${{ runner.os }}-${{ hashFiles('backend/poetry.lock') }}
      
      - name: Install dependencies
        run: poetry install --no-interaction
      
      - name: Run Ruff linter
        run: poetry run ruff check .
      
      - name: Run Ruff formatter check
        run: poetry run ruff format --check .
      
      - name: Run mypy
        run: poetry run mypy .

  backend-test:
    name: Backend Tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: '1.7.1'
          virtualenvs-create: true
          virtualenvs-in-project: true
      
      - name: Load cached venv
        uses: actions/cache@v4
        with:
          path: backend/.venv
          key: venv-${{ runner.os }}-${{ hashFiles('backend/poetry.lock') }}
      
      - name: Install dependencies
        run: poetry install --no-interaction
      
      - name: Run tests with coverage
        run: |
          poetry run pytest \
            --cov=app \
            --cov-report=xml \
            --cov-report=term \
            -v
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: test-secret-key
          JWT_SECRET_KEY: test-jwt-secret
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: backend/coverage.xml
          flags: backend
          fail_ci_if_error: true

  # ============================================================================
  # Worker Checks
  # ============================================================================
  worker-lint:
    name: Worker Lint & Type Check
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: worker
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: '1.7.1'
          virtualenvs-create: true
          virtualenvs-in-project: true
      
      - name: Load cached venv
        uses: actions/cache@v4
        with:
          path: worker/.venv
          key: venv-worker-${{ runner.os }}-${{ hashFiles('worker/poetry.lock') }}
      
      - name: Install dependencies
        run: poetry install --no-interaction
      
      - name: Run Ruff linter
        run: poetry run ruff check .
      
      - name: Run mypy
        run: poetry run mypy .

  worker-test:
    name: Worker Tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: worker
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y libgl1-mesa-glx
      
      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: '1.7.1'
          virtualenvs-create: true
          virtualenvs-in-project: true
      
      - name: Load cached venv
        uses: actions/cache@v4
        with:
          path: worker/.venv
          key: venv-worker-${{ runner.os }}-${{ hashFiles('worker/poetry.lock') }}
      
      - name: Install dependencies
        run: poetry install --no-interaction
      
      - name: Run tests
        run: poetry run pytest -v --cov=app --cov-report=xml
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: worker/coverage.xml
          flags: worker
          fail_ci_if_error: true

  # ============================================================================
  # Security Scanning
  # ============================================================================
  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
      
      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

  # ============================================================================
  # Integration Tests (on push to main only)
  # ============================================================================
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: [frontend-build, backend-test, worker-test]
    steps:
      - uses: actions/checkout@v4
      
      - name: Start services
        run: docker compose -f docker-compose.test.yml up -d
      
      - name: Wait for services
        run: |
          timeout 60 bash -c 'until curl -s http://localhost:8000/health; do sleep 2; done'
      
      - name: Run integration tests
        run: |
          docker compose -f docker-compose.test.yml exec -T api \
            poetry run pytest tests/integration -v
      
      - name: Stop services
        if: always()
        run: docker compose -f docker-compose.test.yml down -v
```

### 2. Deploy to Staging (`.github/workflows/deploy-staging.yml`)

```yaml
name: Deploy to Staging

on:
  push:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_REGISTRY: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com
  ECS_CLUSTER: ai-part-designer-staging

jobs:
  build-and-deploy:
    name: Build and Deploy to Staging
    runs-on: ubuntu-latest
    environment: staging
    permissions:
      id-token: write
      contents: read
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      # Build Frontend
      - name: Build frontend image
        run: |
          docker build \
            -t ${{ env.ECR_REGISTRY }}/ai-part-designer-frontend:${{ github.sha }} \
            -t ${{ env.ECR_REGISTRY }}/ai-part-designer-frontend:staging \
            -f frontend/Dockerfile \
            --build-arg VITE_API_URL=${{ secrets.STAGING_API_URL }} \
            frontend
      
      # Build Backend
      - name: Build backend image
        run: |
          docker build \
            -t ${{ env.ECR_REGISTRY }}/ai-part-designer-api:${{ github.sha }} \
            -t ${{ env.ECR_REGISTRY }}/ai-part-designer-api:staging \
            -f backend/Dockerfile \
            backend
      
      # Build Worker
      - name: Build worker image
        run: |
          docker build \
            -t ${{ env.ECR_REGISTRY }}/ai-part-designer-worker:${{ github.sha }} \
            -t ${{ env.ECR_REGISTRY }}/ai-part-designer-worker:staging \
            -f worker/Dockerfile \
            worker
      
      # Push all images
      - name: Push images to ECR
        run: |
          docker push ${{ env.ECR_REGISTRY }}/ai-part-designer-frontend:${{ github.sha }}
          docker push ${{ env.ECR_REGISTRY }}/ai-part-designer-frontend:staging
          docker push ${{ env.ECR_REGISTRY }}/ai-part-designer-api:${{ github.sha }}
          docker push ${{ env.ECR_REGISTRY }}/ai-part-designer-api:staging
          docker push ${{ env.ECR_REGISTRY }}/ai-part-designer-worker:${{ github.sha }}
          docker push ${{ env.ECR_REGISTRY }}/ai-part-designer-worker:staging
      
      # Run database migrations
      - name: Run migrations
        run: |
          aws ecs run-task \
            --cluster ${{ env.ECS_CLUSTER }} \
            --task-definition ai-part-designer-migrate-staging \
            --network-configuration "awsvpcConfiguration={subnets=[${{ secrets.STAGING_PRIVATE_SUBNETS }}],securityGroups=[${{ secrets.STAGING_SG }}]}" \
            --launch-type FARGATE
          
          # Wait for migration to complete
          sleep 30
      
      # Deploy services
      - name: Deploy API service
        run: |
          aws ecs update-service \
            --cluster ${{ env.ECS_CLUSTER }} \
            --service api \
            --force-new-deployment
      
      - name: Deploy Worker service
        run: |
          aws ecs update-service \
            --cluster ${{ env.ECS_CLUSTER }} \
            --service worker \
            --force-new-deployment
      
      - name: Wait for deployment
        run: |
          aws ecs wait services-stable \
            --cluster ${{ env.ECS_CLUSTER }} \
            --services api worker
      
      # Smoke tests
      - name: Run smoke tests
        run: |
          # Health check
          curl -f ${{ secrets.STAGING_API_URL }}/health
          
          # Basic API test
          curl -f ${{ secrets.STAGING_API_URL }}/api/v1/templates
      
      - name: Notify on success
        if: success()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "✅ Staging deployment successful",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Staging Deployment Successful*\n\nCommit: `${{ github.sha }}`\nBy: ${{ github.actor }}"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
      
      - name: Notify on failure
        if: failure()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "❌ Staging deployment failed",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Staging Deployment Failed*\n\nCommit: `${{ github.sha }}`\nBy: ${{ github.actor }}\n<${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View Logs>"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### 3. Deploy to Production (`.github/workflows/deploy-production.yml`)

```yaml
name: Deploy to Production

on:
  release:
    types: [published]

env:
  AWS_REGION: us-east-1
  ECR_REGISTRY: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com
  ECS_CLUSTER: ai-part-designer-production

jobs:
  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest
    environment: production
    permissions:
      id-token: write
      contents: read
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Tag images for production
        run: |
          # Pull staging images
          docker pull ${{ env.ECR_REGISTRY }}/ai-part-designer-frontend:staging
          docker pull ${{ env.ECR_REGISTRY }}/ai-part-designer-api:staging
          docker pull ${{ env.ECR_REGISTRY }}/ai-part-designer-worker:staging
          
          # Tag for production
          docker tag ${{ env.ECR_REGISTRY }}/ai-part-designer-frontend:staging \
            ${{ env.ECR_REGISTRY }}/ai-part-designer-frontend:${{ github.event.release.tag_name }}
          docker tag ${{ env.ECR_REGISTRY }}/ai-part-designer-frontend:staging \
            ${{ env.ECR_REGISTRY }}/ai-part-designer-frontend:production
          
          docker tag ${{ env.ECR_REGISTRY }}/ai-part-designer-api:staging \
            ${{ env.ECR_REGISTRY }}/ai-part-designer-api:${{ github.event.release.tag_name }}
          docker tag ${{ env.ECR_REGISTRY }}/ai-part-designer-api:staging \
            ${{ env.ECR_REGISTRY }}/ai-part-designer-api:production
          
          docker tag ${{ env.ECR_REGISTRY }}/ai-part-designer-worker:staging \
            ${{ env.ECR_REGISTRY }}/ai-part-designer-worker:${{ github.event.release.tag_name }}
          docker tag ${{ env.ECR_REGISTRY }}/ai-part-designer-worker:staging \
            ${{ env.ECR_REGISTRY }}/ai-part-designer-worker:production
          
          # Push
          docker push ${{ env.ECR_REGISTRY }}/ai-part-designer-frontend:${{ github.event.release.tag_name }}
          docker push ${{ env.ECR_REGISTRY }}/ai-part-designer-frontend:production
          docker push ${{ env.ECR_REGISTRY }}/ai-part-designer-api:${{ github.event.release.tag_name }}
          docker push ${{ env.ECR_REGISTRY }}/ai-part-designer-api:production
          docker push ${{ env.ECR_REGISTRY }}/ai-part-designer-worker:${{ github.event.release.tag_name }}
          docker push ${{ env.ECR_REGISTRY }}/ai-part-designer-worker:production
      
      - name: Create deployment record
        run: |
          echo "Recording deployment..."
          # Create deployment marker in monitoring system
      
      - name: Deploy with rolling update
        run: |
          aws ecs update-service \
            --cluster ${{ env.ECS_CLUSTER }} \
            --service api \
            --force-new-deployment \
            --deployment-configuration "minimumHealthyPercent=100,maximumPercent=200"
          
          aws ecs update-service \
            --cluster ${{ env.ECS_CLUSTER }} \
            --service worker \
            --force-new-deployment
      
      - name: Wait for stable deployment
        run: |
          aws ecs wait services-stable \
            --cluster ${{ env.ECS_CLUSTER }} \
            --services api worker
        timeout-minutes: 15
      
      - name: Verify deployment
        run: |
          # Health checks
          for i in {1..5}; do
            curl -f ${{ secrets.PRODUCTION_API_URL }}/health && break
            sleep 10
          done
      
      - name: Notify team
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "🚀 Production deployment: ${{ github.event.release.tag_name }}",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Production Deployment Complete*\n\nVersion: `${{ github.event.release.tag_name }}`\n\n${{ github.event.release.body }}"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## Required Secrets

| Secret | Description | Where Used |
|--------|-------------|------------|
| `AWS_ACCOUNT_ID` | AWS account number | ECR registry URL |
| `AWS_DEPLOY_ROLE_ARN` | IAM role for deployments | OIDC auth |
| `STAGING_API_URL` | Staging API endpoint | Smoke tests |
| `STAGING_PRIVATE_SUBNETS` | VPC subnet IDs | ECS tasks |
| `STAGING_SG` | Security group ID | ECS tasks |
| `PRODUCTION_API_URL` | Production API endpoint | Health checks |
| `SLACK_WEBHOOK_URL` | Slack notifications | Alerts |
| `CODECOV_TOKEN` | Codecov upload token | Coverage |

---

## Environments

Configure GitHub Environments for:
- `staging` - Auto-deploy on main merge
- `production` - Requires approval, deploy on release

---

*End of Document*
