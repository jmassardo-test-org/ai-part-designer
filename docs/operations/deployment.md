# Production Deployment Guide

This guide covers deploying AI Part Designer to a production environment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Docker Deployment](#docker-deployment)
4. [Database Setup](#database-setup)
5. [SSL/TLS Configuration](#ssltls-configuration)
6. [Monitoring & Logging](#monitoring--logging)
7. [Backup & Recovery](#backup--recovery)
8. [Scaling](#scaling)
9. [Security Checklist](#security-checklist)

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
