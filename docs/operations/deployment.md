# Production Deployment Guide

This guide covers deploying AI Part Designer to a production environment.

## Deployment Methods

We support two deployment approaches:

1. **GitOps with ArgoCD (Recommended)** - Automated continuous deployment with Git as source of truth
2. **Manual Kubernetes/Docker** - Traditional deployment for environments without GitOps

For GitOps deployments, see [ArgoCD Operations Guide](./argocd-operations.md).

## Table of Contents

1. [GitOps Deployment (ArgoCD)](#gitops-deployment-argocd)
2. [Prerequisites](#prerequisites)
3. [Secrets Management](#secrets-management)
4. [Environment Configuration](#environment-configuration)
5. [Docker Deployment](#docker-deployment)
6. [Kubernetes Deployment](#kubernetes-deployment)
7. [Database Setup](#database-setup)
8. [SSL/TLS Configuration](#ssltls-configuration)
9. [Monitoring & Logging](#monitoring--logging)
10. [Backup & Recovery](#backup--recovery)
11. [Scaling](#scaling)
12. [Security Checklist](#security-checklist)

---

## GitOps Deployment (ArgoCD)

**⭐ RECOMMENDED**: For production environments, we recommend using ArgoCD for GitOps-based deployments.

### Benefits

- **Automated Deployments**: Changes to main branch automatically deploy to staging
- **Manual Production Control**: Production requires explicit approval
- **Easy Rollbacks**: Roll back to any previous Git commit via UI or CLI
- **Drift Detection**: Automatically detect and correct configuration drift
- **Audit Trail**: Complete history of all deployments in Git
- **Visual Dashboard**: Monitor deployment status in real-time

### Quick Start

1. **Install ArgoCD**:
   ```bash
   # See k8s/argocd/README.md for detailed instructions
   kubectl create namespace argocd
   kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.10.0/manifests/install.yaml
   kubectl apply -f k8s/argocd/
   ```

2. **Deploy Applications**:
   ```bash
   # Deploy staging (auto-sync)
   kubectl apply -f k8s/argocd/application-staging.yaml

   # Deploy production (manual sync)
   kubectl apply -f k8s/argocd/application-production.yaml
   ```

3. **Access ArgoCD UI**:
   ```bash
   # Get admin password
   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

   # Access UI (after configuring ingress or port-forward)
   # https://argocd.yourdomain.com
   ```

### Deployment Workflow

```
PR Merged → CI Build → Push Images → Update Git → ArgoCD Sync → Deployed
```

**Staging**: Auto-syncs on every main branch change
**Production**: Requires manual approval via ArgoCD UI/CLI

### Documentation

- **Setup Guide**: [k8s/argocd/README.md](../../k8s/argocd/README.md)
- **Operations**: [argocd-operations.md](./argocd-operations.md)
- **Rollbacks**: [rollback-runbook.md](./rollback-runbook.md)

For non-GitOps deployments, continue with the sections below.

---

## Prerequisites

- Docker Engine 24.0+
- Docker Compose 2.20+
- Domain name with DNS configured
- SSL certificate (or use Let's Encrypt)
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (for caching and rate limiting)
- Minimum 4GB RAM, 2 CPU cores

---

## Secrets Management

**⚠️ IMPORTANT**: For production Kubernetes deployments, use OpenBao (Vault fork) for secure secrets management instead of environment variables or `.env` files.

### Quick Start

```bash
# Deploy OpenBao with External Secrets Operator
cd k8s/base/openbao
./deploy-openbao.sh

# This will:
# 1. Deploy OpenBao in HA mode (3 replicas)
# 2. Initialize and unseal OpenBao
# 3. Configure Kubernetes authentication
# 4. Deploy External Secrets Operator
# 5. Bootstrap initial secrets
```

### Key Features

- **Encrypted at Rest**: All secrets encrypted in OpenBao storage
- **Audit Logging**: Complete audit trail of all secret access
- **Dynamic Secrets**: Time-limited database credentials
- **Secret Rotation**: Automated rotation without downtime
- **Kubernetes Integration**: Secrets sync automatically via External Secrets Operator

### Documentation

See [Secrets Management Operations Guide](./secrets-management.md) for:
- Detailed deployment instructions
- Secret rotation procedures
- Troubleshooting guide
- Emergency access procedures
- Audit and compliance

---

## Environment Configuration

### Required Environment Variables

Create a `.env.production` file:

```bash
# Application
APP_ENV=production
DEBUG=false
SECRET_KEY=<generate-with-openssl-rand-hex-32>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/aipartdesigner
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://redis:6379/0
CACHE_TTL=3600

# Authentication
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-64>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (SMTP)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=<sendgrid-api-key>
EMAIL_FROM=noreply@yourdomain.com

# File Storage
STORAGE_BACKEND=s3  # or 'local'
AWS_ACCESS_KEY_ID=<aws-key>
AWS_SECRET_ACCESS_KEY=<aws-secret>
AWS_S3_BUCKET=aipartdesigner-files
AWS_S3_REGION=us-east-1

# AI/ML Services
OPENAI_API_KEY=<openai-key>
MODEL_INFERENCE_URL=http://inference:8080

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/xxx
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE=redis

# CORS
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Generate Secrets

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate JWT_SECRET_KEY
openssl rand -hex 64
```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.24+)
- `kubectl` configured with cluster access
- `helm` 3.x installed
- Cluster-admin permissions (for initial setup)

### Step 1: Deploy OpenBao for Secrets Management

```bash
# Clone repository
git clone https://github.com/jmassardo/ai-part-designer.git
cd ai-part-designer

# Deploy OpenBao
cd k8s/base/openbao
./deploy-openbao.sh

# Backup unseal keys (CRITICAL!)
kubectl get secret openbao-unseal-keys -n openbao -o yaml \
  > ~/secure-backup/openbao-keys-$(date +%Y%m%d).yaml
```

### Step 2: Configure Application Secrets

```bash
# Port-forward to OpenBao
kubectl port-forward -n openbao svc/openbao 8200:8200 &

# Set environment variables
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=$(kubectl get secret openbao-unseal-keys \
  -n openbao -o jsonpath='{.data.root-token}' | base64 -d)

# Add AI service API keys
openbao kv put secret/ai-part-designer/ai-services/openai \
  api_key="sk-proj-YOUR_KEY" \
  org_id="org-YOUR_ORG" \
  model="gpt-4o"

openbao kv put secret/ai-part-designer/ai-services/anthropic \
  api_key="sk-ant-YOUR_KEY" \
  model="claude-sonnet-4-20250514"

# Add storage credentials (S3/MinIO)
openbao kv put secret/ai-part-designer/storage/s3-credentials \
  access_key_id="YOUR_ACCESS_KEY" \
  secret_access_key="YOUR_SECRET_KEY" \
  bucket_name="ai-part-designer-files" \
  region="us-east-1"

# Add email credentials
openbao kv put secret/ai-part-designer/email/smtp-config \
  host="smtp.sendgrid.net" \
  port="587" \
  username="apikey" \
  password="YOUR_SENDGRID_KEY" \
  from_email="noreply@yourdomain.com"

# Add payment processing keys (if using Stripe)
openbao kv put secret/ai-part-designer/payments/stripe-keys \
  publishable_key="pk_live_..." \
  secret_key="sk_live_..." \
  webhook_secret="whsec_..."
```

### Step 3: Deploy Application Services

```bash
# Create namespace
kubectl create namespace ai-part-designer

# Deploy PostgreSQL (or use managed service)
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install postgres bitnami/postgresql \
  --namespace ai-part-designer \
  --set auth.database=ai_part_designer \
  --set primary.persistence.size=50Gi

# Deploy Redis
helm install redis bitnami/redis \
  --namespace ai-part-designer \
  --set auth.enabled=true \
  --set master.persistence.size=10Gi

# Create ExternalSecrets to sync from OpenBao
kubectl apply -f k8s/overlays/production/external-secrets/

# Deploy application workloads
kubectl apply -f k8s/overlays/production/

# Verify deployment
kubectl get pods -n ai-part-designer
kubectl get externalsecret -n ai-part-designer
```

### Step 4: Configure Ingress

```bash
# Install ingress-nginx controller (if not already installed)
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace

# Apply ingress configuration
kubectl apply -f k8s/overlays/production/ingress.yaml

# Configure DNS
# Point your domain to the ingress controller's external IP
kubectl get svc -n ingress-nginx ingress-nginx-controller
```

### Step 5: Enable SSL/TLS with cert-manager

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
kubectl apply -f k8s/base/cert-manager/letsencrypt-issuer.yaml

# Update ingress to use TLS
kubectl annotate ingress ai-part-designer \
  -n ai-part-designer \
  cert-manager.io/cluster-issuer=letsencrypt-prod
```

### Kubernetes Architecture

```
┌─────────────────────────────────────────────────────┐
│  Ingress (nginx-ingress)                            │
│  - TLS termination (cert-manager)                   │
│  - Rate limiting                                    │
│  - Path routing                                     │
└─────────────────┬───────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌──────────┐
│ API    │  │ Worker   │  │ Frontend │
│ Service│  │ Service  │  │ Static   │
│        │  │          │  │ Files    │
│ HPA    │  │ KEDA     │  │          │
│ 2-20   │  │ 2-20     │  │          │
└───┬────┘  └────┬─────┘  └──────────┘
    │            │
    │     ┌──────┴───────┐
    │     │              │
    ▼     ▼              ▼
┌─────────────┐  ┌─────────────┐
│ PostgreSQL  │  │ Redis       │
│ (Primary)   │  │ (Cache)     │
│             │  │             │
│ PVC: 50Gi   │  │ PVC: 10Gi   │
└─────────────┘  └─────────────┘
         ▲                ▲
         │                │
         └────────┬───────┘
                  │
         Secrets from OpenBao
         (via External Secrets Operator)
```

### Monitoring & Observability

```bash
# Install Prometheus & Grafana
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Default credentials
# Username: admin
# Password: prom-operator
```

### Scaling Configuration

```yaml
# API service - HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: ai-part-designer
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80

---
# Worker service - KEDA (queue-based scaling)
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: worker-scaler
  namespace: ai-part-designer
spec:
  scaleTargetRef:
    name: worker
  minReplicaCount: 2
  maxReplicaCount: 20
  triggers:
  - type: redis
    metadata:
      address: redis:6379
      listName: celery
      listLength: "5"
```

---

## Docker Deployment

### docker-compose.production.yml

```yaml
version: '3.8'

services:
  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - backend
    restart: always
    networks:
      - frontend

  # Backend API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.production
    env_file:
      - .env.production
    expose:
      - "8000"
    depends_on:
      - db
      - redis
    restart: always
    networks:
      - frontend
      - backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Celery Worker (for background jobs)
  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.production
    command: celery -A app.tasks worker --loglevel=info
    env_file:
      - .env.production
    depends_on:
      - db
      - redis
    restart: always
    networks:
      - backend

  # PostgreSQL Database
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: aipartdesigner
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: always
    networks:
      - backend
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: always
    networks:
      - backend
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:

networks:
  frontend:
  backend:
```

### Build and Deploy

```bash
# Build frontend
cd frontend
npm ci
npm run build

# Build and start services
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d

# View logs
docker-compose -f docker-compose.production.yml logs -f

# Scale workers
docker-compose -f docker-compose.production.yml up -d --scale worker=3
```

---

## Database Setup

### Initial Migration

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Create admin user
docker-compose exec backend python -c "
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.user import User

db = SessionLocal()
admin = User(
    email='admin@yourdomain.com',
    hashed_password=get_password_hash('SecureAdminPassword123!'),
    display_name='Admin',
    is_admin=True,
    is_verified=True
)
db.add(admin)
db.commit()
print('Admin user created')
"
```

### Migration Commands

```bash
# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec backend alembic upgrade head

# Rollback one version
docker-compose exec backend alembic downgrade -1

# View migration history
docker-compose exec backend alembic history
```

---

## SSL/TLS Configuration

### Option 1: Let's Encrypt (Certbot)

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Get certificate
certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Auto-renewal cron
0 0 1 * * certbot renew --quiet
```

### Option 2: Custom Certificate

```bash
# Create ssl directory
mkdir -p nginx/ssl

# Copy certificates
cp /path/to/fullchain.pem nginx/ssl/
cp /path/to/privkey.pem nginx/ssl/
```

### Nginx SSL Configuration

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=static:10m rate=100r/s;

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS Server
    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;

        # Frontend static files
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
            limit_req zone=static burst=50 nodelay;
            
            # Cache static assets
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
                expires 1y;
                add_header Cache-Control "public, immutable";
            }
        }

        # API proxy
        location /api {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://backend:8000;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Health check
        location /health {
            proxy_pass http://backend:8000/api/v1/health;
            access_log off;
        }
    }
}
```

---

## Monitoring & Logging

### Sentry Integration

```python
# backend/app/core/monitoring.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

def init_sentry(dsn: str):
    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment="production",
    )
```

### Structured Logging

```python
# backend/app/core/logging.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler]
    )
```

### Health Check Endpoint

```python
# backend/app/api/v1/health.py
from fastapi import APIRouter, Depends
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

@router.get("/health")
async def health_check(db = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "version": "1.0.0",
    }
```

---

## Backup & Recovery

### Automated Backups

```bash
#!/bin/bash
# scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# Database backup
docker-compose exec -T db pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete

# Upload to S3 (optional)
aws s3 cp $BACKUP_DIR/db_$DATE.sql.gz s3://your-backup-bucket/db/
```

### Restore from Backup

```bash
# Stop the application
docker-compose down

# Restore database
gunzip -c backups/db_YYYYMMDD_HHMMSS.sql.gz | docker-compose exec -T db psql -U $DB_USER $DB_NAME

# Start the application
docker-compose up -d
```

### Backup Cron Job

```bash
# Add to crontab
0 2 * * * /path/to/scripts/backup.sh >> /var/log/backup.log 2>&1
```

---

## Scaling

### Horizontal Scaling

```bash
# Scale API servers
docker-compose up -d --scale backend=3

# Scale workers
docker-compose up -d --scale worker=5
```

### Load Balancer Configuration

Nginx automatically load balances between backend containers using round-robin.

### Database Connection Pooling

```python
# backend/app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)
```

---

## Security Checklist

### Pre-Deployment

- [ ] All secrets are unique and securely generated
- [ ] DEBUG mode is disabled
- [ ] Database credentials are not in version control
- [ ] SSL/TLS is configured and certificates are valid
- [ ] CORS is configured for production domains only
- [ ] Rate limiting is enabled
- [ ] Input validation is comprehensive
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)
- [ ] CSRF protection enabled
- [ ] Security headers configured in Nginx

### Post-Deployment

- [ ] Verify HTTPS redirect works
- [ ] Test rate limiting with multiple requests
- [ ] Verify error pages don't leak information
- [ ] Check that stack traces are not exposed
- [ ] Verify authentication and authorization
- [ ] Test password reset flow
- [ ] Review access logs for anomalies
- [ ] Set up security monitoring alerts

### Regular Maintenance

- [ ] Update dependencies weekly
- [ ] Review and rotate secrets quarterly
- [ ] Audit user access permissions
- [ ] Review and clean up old data
- [ ] Test backup restoration process
- [ ] Run security vulnerability scans
- [ ] Update SSL certificates before expiry

---

## Troubleshooting

### Common Issues

**Container won't start:**
```bash
docker-compose logs backend
docker-compose exec backend python -c "import app.main"
```

**Database connection issues:**
```bash
docker-compose exec backend python -c "
from app.db.session import engine
import asyncio
asyncio.run(engine.connect())
print('Connected!')
"
```

**Check service health:**
```bash
curl -s http://localhost/api/v1/health | jq
```

**Reset everything:**
```bash
docker-compose down -v
docker-compose up -d --build
docker-compose exec backend alembic upgrade head
```

---

## Support

For issues, check:
1. Container logs: `docker-compose logs -f`
2. Application logs: `docker-compose exec backend tail -f /var/log/app.log`
3. Sentry dashboard for error tracking
4. GitHub issues for known problems
