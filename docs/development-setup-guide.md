# Development Environment Setup Guide
# AI Part Designer

**Version:** 1.0  
**Date:** 2026-01-24  

---

## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Initial Setup](#2-initial-setup)
3. [Backend Setup](#3-backend-setup)
4. [Frontend Setup](#4-frontend-setup)
5. [Worker Setup](#5-worker-setup)
6. [Database Setup](#6-database-setup)
7. [Running the Application](#7-running-the-application)
8. [IDE Configuration](#8-ide-configuration)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Git | 2.40+ | Version control |
| Docker | 24+ | Containerization |
| Docker Compose | 2.20+ | Multi-container orchestration |
| Node.js | 20 LTS | Frontend runtime |
| pnpm | 8+ | Frontend package manager |
| Python | 3.11+ | Backend runtime |
| Poetry | 1.7+ | Python dependency management |

### Installation Commands

#### macOS (Homebrew)
```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install prerequisites
brew install git docker node@20 python@3.11 poetry
brew install --cask docker

# Install pnpm
npm install -g pnpm

# Start Docker Desktop
open -a Docker
```

#### Ubuntu/Debian
```bash
# Update package lists
sudo apt update && sudo apt upgrade -y

# Install Git
sudo apt install git -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y

# Install pnpm
npm install -g pnpm

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -
```

#### Windows (WSL2 recommended)
```powershell
# Install WSL2 first
wsl --install

# Then follow Ubuntu instructions inside WSL2
```

### Verify Installations
```bash
git --version          # >= 2.40
docker --version       # >= 24.0
docker compose version # >= 2.20
node --version         # >= 20.0
pnpm --version         # >= 8.0
python3 --version      # >= 3.11
poetry --version       # >= 1.7
```

---

## 2. Initial Setup

### Clone Repository
```bash
# Clone the repository
git clone https://github.com/your-org/ai-part-designer.git
cd ai-part-designer

# Create your feature branch
git checkout -b feature/your-feature
```

### Environment Files

#### Create Local Environment Files
```bash
# Copy example environment files
cp backend/.env.example backend/.env
cp worker/.env.example worker/.env
cp frontend/.env.example frontend/.env
```

#### Backend `.env` Configuration
```bash
# backend/.env

# Application
APP_NAME=ai-part-designer
APP_ENV=development
DEBUG=true
SECRET_KEY=your-super-secret-key-change-in-production

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_part_designer
DATABASE_POOL_SIZE=5

# Redis
REDIS_URL=redis://localhost:6379/0

# Storage (MinIO - S3-compatible, cloud-agnostic)
STORAGE_BACKEND=minio
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET=ai-part-designer-dev
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_REGION=us-east-1

# OpenAI
OPENAI_API_KEY=sk-your-development-key

# JWT
JWT_SECRET_KEY=jwt-secret-key-for-development
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

#### Frontend `.env` Configuration
```bash
# frontend/.env

VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws
VITE_ENVIRONMENT=development
```

---

## 3. Backend Setup

### Install Dependencies
```bash
cd backend

# Install Python dependencies with Poetry
poetry install

# Activate virtual environment
poetry shell
```

### Verify Installation
```bash
# Check FastAPI is installed
python -c "import fastapi; print(fastapi.__version__)"

# Run linting
poetry run ruff check .

# Run type checking
poetry run mypy .
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
poetry run pre-commit install
```

---

## 4. Frontend Setup

### Install Dependencies
```bash
cd frontend

# Install Node.js dependencies
pnpm install
```

### Generate API Types
```bash
# Generate TypeScript types from OpenAPI spec
pnpm run generate-api-types
```

### Verify Installation
```bash
# Run type checking
pnpm run typecheck

# Run linting
pnpm run lint
```

---

## 5. Worker Setup

### Install Dependencies
```bash
cd worker

# Install Python dependencies
poetry install

# Activate virtual environment
poetry shell
```

### CadQuery Dependencies (macOS)
```bash
# CadQuery requires additional system dependencies
brew install opencascade

# If using conda (alternative approach)
conda install -c conda-forge cadquery
```

### CadQuery Dependencies (Ubuntu)
```bash
# Install OpenCASCADE dependencies
sudo apt install -y libocct-modeling-algorithms-dev libocct-visualization-dev

# Install CadQuery via pip
pip install cadquery
```

---

## 6. Database Setup

### Start Infrastructure Services
```bash
# From project root
docker compose up -d postgres redis minio
```

### Verify Services
```bash
# Check containers are running
docker compose ps

# Expected output:
# NAME                     STATUS
# ai-part-designer-postgres   running (healthy)
# ai-part-designer-redis      running
# ai-part-designer-minio        running (healthy)
```

### Initialize Database
```bash
cd backend

# Run database migrations
poetry run alembic upgrade head

# Seed development data (optional)
poetry run python scripts/seed_templates.py
poetry run python scripts/create_admin.py
```

### Connect to Database (for debugging)
```bash
# Using psql
docker compose exec postgres psql -U postgres -d ai_part_designer

# Or use a GUI like pgAdmin, TablePlus, or DBeaver
# Connection string: postgresql://postgres:postgres@localhost:5432/ai_part_designer
```

### MinIO Object Storage

MinIO provides S3-compatible storage for local development (cloud-agnostic).

```bash
# Bucket is auto-created by minio-init container
# Access MinIO Console at http://localhost:9001
# Credentials: minioadmin / minioadmin

# Or use AWS CLI with MinIO endpoint:
aws --endpoint-url=http://localhost:9000 s3 ls s3://ai-part-designer-dev/
```

---

## 7. Running the Application

### Option A: Docker Compose (Recommended for Full Stack)
```bash
# Start all services
docker compose up

# Or start in detached mode
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

### Option B: Run Services Individually (For Development)

#### Terminal 1: Database, Redis & MinIO
```bash
docker compose up postgres redis minio
```

#### Terminal 2: Backend API
```bash
cd backend
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Terminal 3: Celery Worker
```bash
cd worker
poetry run celery -A app.celery worker --loglevel=info --concurrency=2
```

#### Terminal 4: Celery Beat (Scheduled Tasks)
```bash
cd worker
poetry run celery -A app.celery beat --loglevel=info
```

#### Terminal 5: Frontend
```bash
cd frontend
pnpm run dev
```

### Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5173 | React application |
| Backend API | http://localhost:8000 | FastAPI REST API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| ReDoc | http://localhost:8000/redoc | ReDoc documentation |
| Flower | http://localhost:5555 | Celery task monitor |
| MinIO Console | http://localhost:9001 | Object storage admin |
| MinIO API | http://localhost:9000 | S3-compatible API |

---

## 8. IDE Configuration

### VS Code

#### Recommended Extensions
Create/update `.vscode/extensions.json`:
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "bradlc.vscode-tailwindcss",
    "Prisma.prisma",
    "ms-azuretools.vscode-docker",
    "redhat.vscode-yaml",
    "yoavbls.pretty-ts-errors",
    "formulahendry.auto-rename-tag"
  ]
}
```

#### Workspace Settings
Create/update `.vscode/settings.json`:
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": "explicit",
    "source.organizeImports": "explicit"
  },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/bin/python",
  "python.analysis.typeCheckingMode": "basic",
  "typescript.preferences.importModuleSpecifier": "non-relative",
  "tailwindCSS.includeLanguages": {
    "typescript": "javascript",
    "typescriptreact": "javascript"
  },
  "files.associations": {
    "*.css": "tailwindcss"
  }
}
```

#### Launch Configuration
Create/update `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Backend: FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--port", "8000"],
      "cwd": "${workspaceFolder}/backend",
      "envFile": "${workspaceFolder}/backend/.env",
      "jinja": true
    },
    {
      "name": "Worker: Celery",
      "type": "debugpy",
      "request": "launch",
      "module": "celery",
      "args": ["-A", "app.celery", "worker", "--loglevel=info"],
      "cwd": "${workspaceFolder}/worker",
      "envFile": "${workspaceFolder}/worker/.env"
    },
    {
      "name": "Frontend: Vite",
      "type": "node",
      "request": "launch",
      "runtimeExecutable": "pnpm",
      "runtimeArgs": ["run", "dev"],
      "cwd": "${workspaceFolder}/frontend"
    },
    {
      "name": "Backend: Debug Tests",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["-xvs"],
      "cwd": "${workspaceFolder}/backend",
      "envFile": "${workspaceFolder}/backend/.env"
    }
  ],
  "compounds": [
    {
      "name": "Full Stack",
      "configurations": ["Backend: FastAPI", "Worker: Celery", "Frontend: Vite"]
    }
  ]
}
```

### PyCharm / IntelliJ IDEA

1. **Open Project**: Open the root `ai-part-designer` folder
2. **Configure Python Interpreter**:
   - Go to Settings → Project → Python Interpreter
   - Add interpreter → Poetry Environment → Existing
   - Select `backend/.venv/bin/python`
3. **Configure Node.js**:
   - Go to Settings → Languages & Frameworks → Node.js
   - Set Node interpreter path
4. **Enable ESLint**: Settings → Languages & Frameworks → JavaScript → Code Quality Tools → ESLint → Automatic configuration
5. **Enable Prettier**: Settings → Languages & Frameworks → JavaScript → Prettier → On code reformat

---

## 9. Troubleshooting

### Common Issues

#### Docker Issues

**Issue: Docker daemon not running**
```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker
```

**Issue: Port already in use**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or change port in docker-compose.yml
```

**Issue: Container keeps restarting**
```bash
# Check container logs
docker compose logs <service-name>

# Check if dependencies are healthy
docker compose ps
```

#### Database Issues

**Issue: Connection refused**
```bash
# Ensure PostgreSQL container is running
docker compose up -d postgres

# Check container health
docker compose ps postgres

# Verify connection
docker compose exec postgres pg_isready -U postgres
```

**Issue: Migration failed**
```bash
# Reset database (WARNING: deletes all data)
docker compose down -v
docker compose up -d postgres
cd backend && poetry run alembic upgrade head
```

#### Python Issues

**Issue: Poetry not using correct Python version**
```bash
# Tell Poetry which Python to use
poetry env use python3.11

# Recreate virtual environment
poetry install
```

**Issue: CadQuery import error**
```bash
# Verify OCC is installed
python -c "from OCP.TopoDS import TopoDS_Shape; print('OK')"

# If fails, reinstall cadquery
pip install --force-reinstall cadquery
```

#### Frontend Issues

**Issue: Node modules issues**
```bash
# Clear cache and reinstall
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

**Issue: TypeScript errors after API changes**
```bash
# Regenerate API types
pnpm run generate-api-types

# Restart TypeScript server in VS Code
Cmd+Shift+P → TypeScript: Restart TS Server
```

#### Redis Issues

**Issue: Redis connection refused**
```bash
# Check Redis is running
docker compose up -d redis

# Test connection
docker compose exec redis redis-cli ping
# Should return: PONG
```

### Getting Help

1. **Check logs**: `docker compose logs -f <service>`
2. **Search existing issues**: GitHub Issues
3. **Slack channel**: #ai-part-designer-dev
4. **Office hours**: Tuesdays 2-3pm

---

## Quick Reference

### Makefile Commands
```bash
make dev          # Start development environment
make test         # Run all tests
make lint         # Run linters
make format       # Format code
make db-migrate   # Run migrations
make clean        # Clean up containers and caches
```

### Useful Docker Commands
```bash
docker compose up -d          # Start services
docker compose down           # Stop services
docker compose down -v        # Stop and remove volumes
docker compose logs -f api    # Follow API logs
docker compose exec api bash  # Shell into container
docker compose restart api    # Restart single service
```

---

*End of Document*
