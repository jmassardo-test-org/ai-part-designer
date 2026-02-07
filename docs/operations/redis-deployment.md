# Redis Deployment and Operations Guide

## Overview

Redis is deployed via the Bitnami Redis Helm chart with Sentinel mode for high availability. Redis serves two critical purposes in the AI Part Designer platform:

1. **Caching** - Session data, API response caching
2. **Message Broker** - Celery task queue for background jobs

## Architecture

### Production Configuration
- **Architecture**: Redis Sentinel (replication mode)
- **Master Nodes**: 1 master pod
- **Replica Nodes**: 2 replica pods
- **Sentinel Nodes**: 3 Sentinel pods (co-located with Redis pods)
- **Quorum**: 2 (minimum Sentinels needed to agree on failover)
- **Persistence**: RDB + AOF (Append-Only File) for maximum durability

### Staging Configuration
- **Architecture**: Redis Sentinel (replication mode)
- **Master Nodes**: 1 master pod
- **Replica Nodes**: 1 replica pod
- **Sentinel Nodes**: 2 Sentinel pods
- **Persistence**: RDB + AOF

### Development Configuration
- **Architecture**: Standalone (single instance)
- **Nodes**: 1 pod (no replication)
- **Persistence**: RDB only

## Deployment

### Prerequisites

1. Kubernetes cluster with dynamic volume provisioning
2. Helm 3.x installed
3. Appropriate StorageClass configured

### Deploy Redis

```bash
# Add Bitnami repository (if not already added)
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install/upgrade the full application stack (includes Redis)
helm upgrade --install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer \
  --create-namespace \
  --values helm/ai-part-designer/values-production.yaml \
  --set redis.auth.password=<secure-password>
```

### Configuration Parameters

Key Redis configuration values in `values.yaml`:

```yaml
redis:
  architecture: replication  # or standalone for dev
  auth:
    enabled: true
    password: "CHANGEME"
    sentinel: true
  sentinel:
    enabled: true
    quorum: 2
    downAfterMilliseconds: 5000
    failoverTimeout: 10000
    parallelSyncs: 1
  master:
    count: 1
    persistence:
      enabled: true
      size: 10Gi
      storageClass: "fast-ssd"
    resources:
      requests:
        memory: "512Mi"
        cpu: "250m"
      limits:
        memory: "2Gi"
        cpu: "1000m"
  replica:
    replicaCount: 2
    persistence:
      enabled: true
      size: 10Gi
      storageClass: "fast-ssd"
  metrics:
    enabled: true
    serviceMonitor:
      enabled: true
      interval: 30s
```

## Service Names

When Redis is deployed, the following services are created:

- **Master Service**: `ai-part-designer-redis-master` (port 6379)
- **Headless Service**: `ai-part-designer-redis-headless` (port 6379)
- **Sentinel Service**: `ai-part-designer-redis` (port 26379)
- **Metrics Service**: `ai-part-designer-redis-metrics` (port 9121)

## Connecting to Redis

### From Application Pods

The backend and Celery workers automatically connect using these environment variables:

```bash
REDIS_HOST=ai-part-designer-redis-master
REDIS_PORT=6379
REDIS_PASSWORD=<from-secret>
REDIS_DB=0
```

### Using redis-cli

```bash
# Connect to master
kubectl exec -it -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master -o name | head -1) \
  -- redis-cli -a <password>

# Connect to Sentinel
kubectl exec -it -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis -o name | head -1) \
  -- redis-cli -p 26379

# Sentinel commands
SENTINEL masters
SENTINEL replicas mymaster
SENTINEL get-master-addr-by-name mymaster
```

## High Availability Testing

### Verify Sentinel Configuration

```bash
# Check Sentinel status
kubectl exec -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis -o name | head -1) \
  -- redis-cli -p 26379 SENTINEL masters

# Check replication status
kubectl exec -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master -o name) \
  -- redis-cli -a <password> INFO replication
```

### Test Automatic Failover

1. **Identify current master**:
```bash
kubectl exec -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis -o name | head -1) \
  -- redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster
```

2. **Delete master pod to trigger failover**:
```bash
kubectl delete pod -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master -o name)
```

3. **Monitor failover process** (should complete within ~10 seconds):
```bash
kubectl logs -n ai-part-designer -l app.kubernetes.io/name=redis -f
```

4. **Verify new master**:
```bash
kubectl exec -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis -o name | head -1) \
  -- redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster
```

5. **Check application connectivity**:
```bash
# Backend should automatically reconnect
kubectl logs -n ai-part-designer -l app.kubernetes.io/name=backend --tail=50

# Celery workers should reconnect
kubectl logs -n ai-part-designer -l app.kubernetes.io/name=celery-worker --tail=50
```

## Data Persistence

### Persistence Configuration

Redis uses two persistence mechanisms:

1. **RDB (Redis Database Backup)**: Point-in-time snapshots
   - `save 900 1` - Save if 1 key changed in 15 minutes
   - `save 300 10` - Save if 10 keys changed in 5 minutes
   - `save 60 10000` - Save if 10,000 keys changed in 1 minute

2. **AOF (Append-Only File)**: Transaction log
   - `appendonly yes` - Enable AOF
   - `appendfsync everysec` - Sync every second (good balance)

### Backup Procedures

```bash
# Trigger manual snapshot
kubectl exec -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master -o name) \
  -- redis-cli -a <password> BGSAVE

# Check last save time
kubectl exec -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master -o name) \
  -- redis-cli -a <password> LASTSAVE

# Copy RDB file from PVC
kubectl cp ai-part-designer/$(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master -o jsonpath='{.items[0].metadata.name}'):/data/dump.rdb ./redis-backup-$(date +%Y%m%d).rdb
```

### Restore Procedures

```bash
# Scale down to prevent writes
kubectl scale deployment -n ai-part-designer backend --replicas=0
kubectl scale deployment -n ai-part-designer celery-worker --replicas=0
kubectl scale deployment -n ai-part-designer celery-beat --replicas=0

# Copy backup to master pod
kubectl cp ./redis-backup-<date>.rdb ai-part-designer/$(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master -o jsonpath='{.items[0].metadata.name}'):/data/dump.rdb

# Restart Redis to load backup
kubectl delete pod -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master

# Wait for Redis to be ready
kubectl wait --for=condition=ready pod -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master --timeout=300s

# Scale applications back up
kubectl scale deployment -n ai-part-designer backend --replicas=3
kubectl scale deployment -n ai-part-designer celery-worker --replicas=3
kubectl scale deployment -n ai-part-designer celery-beat --replicas=1
```

## Monitoring and Metrics

### Prometheus Metrics

Redis exports metrics on port 9121. A ServiceMonitor is automatically created when:
- `redis.metrics.enabled=true`
- `redis.metrics.serviceMonitor.enabled=true`

Key metrics to monitor:

- `redis_up` - Redis instance availability
- `redis_connected_clients` - Number of connected clients
- `redis_memory_used_bytes` - Memory usage
- `redis_commands_processed_total` - Total commands processed
- `redis_keyspace_hits_total` / `redis_keyspace_misses_total` - Cache hit ratio
- `redis_replication_connected_slaves` - Number of connected replicas

### Grafana Dashboards

Import the official Redis dashboard:
- Dashboard ID: 11835 (Redis Dashboard for Prometheus)

### Alerting Rules

Example Prometheus alerting rules:

```yaml
- alert: RedisDown
  expr: redis_up == 0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Redis instance down"
    description: "Redis {{ $labels.instance }} is down"

- alert: RedisHighMemoryUsage
  expr: (redis_memory_used_bytes / redis_memory_max_bytes) > 0.9
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Redis high memory usage"
    description: "Redis {{ $labels.instance }} is using {{ $value }}% of available memory"

- alert: RedisReplicationBroken
  expr: redis_connected_slaves < 2
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Redis replication broken"
    description: "Redis master has {{ $value }} replicas (expected 2)"
```

## Performance Tuning

### Memory Management

```bash
# Check current memory usage
kubectl exec -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master -o name) \
  -- redis-cli -a <password> INFO memory

# Set memory eviction policy (if needed)
kubectl exec -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master -o name) \
  -- redis-cli -a <password> CONFIG SET maxmemory-policy allkeys-lru
```

### Connection Pooling

The backend uses Redis connection pooling:
- Default pool size: 10 connections
- Max connections: 50
- Retry on timeout: Yes

### Slow Log Analysis

```bash
# Get slow queries (>10ms)
kubectl exec -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master -o name) \
  -- redis-cli -a <password> SLOWLOG GET 10
```

## Security

### Network Policies

Network policies restrict Redis access to:
- Backend pods (port 6379)
- Celery worker pods (port 6379)
- Celery beat pods (port 6379)
- Redis pods (replication and Sentinel: ports 6379, 26379)
- Prometheus (metrics: port 9121)

### Authentication

Redis requires password authentication:
- Password stored in Kubernetes Secret: `ai-part-designer-redis`
- Secret key: `redis-password`
- Injected into pods via environment variable: `REDIS_PASSWORD`

### Rotating Passwords

```bash
# Generate new password
NEW_PASSWORD=$(openssl rand -base64 32)

# Update secret
kubectl create secret generic ai-part-designer-redis \
  --from-literal=redis-password=$NEW_PASSWORD \
  --namespace=ai-part-designer \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart all Redis pods
kubectl rollout restart statefulset -n ai-part-designer ai-part-designer-redis-master
kubectl rollout restart statefulset -n ai-part-designer ai-part-designer-redis-replicas

# Restart application pods
kubectl rollout restart deployment -n ai-part-designer backend
kubectl rollout restart deployment -n ai-part-designer celery-worker
kubectl rollout restart deployment -n ai-part-designer celery-beat
```

## Troubleshooting

### Common Issues

#### Redis Pods Not Starting

```bash
# Check pod events
kubectl describe pod -n ai-part-designer -l app.kubernetes.io/name=redis

# Check logs
kubectl logs -n ai-part-designer -l app.kubernetes.io/name=redis

# Common causes:
# - PVC binding issues (check StorageClass)
# - Resource limits (check node capacity)
# - Image pull issues (check image availability)
```

#### Application Cannot Connect

```bash
# Verify Redis service
kubectl get svc -n ai-part-designer | grep redis

# Test connection from backend pod
kubectl exec -it -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=backend -o name | head -1) \
  -- sh -c 'apt update && apt install -y redis-tools && redis-cli -h ai-part-designer-redis-master -a $REDIS_PASSWORD ping'

# Check backend logs for Redis errors
kubectl logs -n ai-part-designer -l app.kubernetes.io/name=backend | grep -i redis
```

#### Sentinel Failover Not Working

```bash
# Check Sentinel logs
kubectl logs -n ai-part-designer -l app.kubernetes.io/name=redis -c sentinel

# Verify quorum configuration
kubectl exec -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis -o name | head -1) \
  -- redis-cli -p 26379 SENTINEL masters

# Check network connectivity between Sentinel pods
kubectl exec -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis -o name | head -1) \
  -- redis-cli -p 26379 SENTINEL ckquorum mymaster
```

#### High Memory Usage

```bash
# Check memory stats
kubectl exec -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master -o name) \
  -- redis-cli -a <password> INFO memory

# Check keyspace
kubectl exec -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master -o name) \
  -- redis-cli -a <password> INFO keyspace

# Find large keys
kubectl exec -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master -o name) \
  -- redis-cli -a <password> --bigkeys

# If needed, increase memory limits or enable eviction policy
```

## Maintenance

### Upgrading Redis

```bash
# Update Chart.yaml with new Redis chart version
# Update helm dependencies
helm dependency update ./helm/ai-part-designer

# Test upgrade in staging first
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-staging \
  --values helm/ai-part-designer/values-staging.yaml \
  --dry-run --debug

# Apply upgrade
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-staging \
  --values helm/ai-part-designer/values-staging.yaml

# Monitor rollout
kubectl rollout status statefulset -n ai-part-designer-staging ai-part-designer-redis-master
kubectl rollout status statefulset -n ai-part-designer-staging ai-part-designer-redis-replicas
```

### Scaling

```bash
# Scale replicas (production only, requires Sentinel)
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer \
  --values helm/ai-part-designer/values-production.yaml \
  --set redis.replica.replicaCount=3 \
  --reuse-values

# Verify replication
kubectl exec -n ai-part-designer \
  $(kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=redis,app.kubernetes.io/component=master -o name) \
  -- redis-cli -a <password> INFO replication
```

## Best Practices

1. **Always use Sentinel in production** for automatic failover
2. **Enable both RDB and AOF persistence** for maximum durability
3. **Monitor memory usage** and set appropriate limits
4. **Test failover scenarios** regularly
5. **Backup RDB files** before major upgrades
6. **Use strong passwords** and rotate them periodically
7. **Enable network policies** to restrict access
8. **Monitor cache hit rates** to optimize application caching
9. **Set up alerting** for Redis availability and performance
10. **Document runbooks** for common operational tasks

## References

- [Bitnami Redis Helm Chart](https://github.com/bitnami/charts/tree/main/bitnami/redis)
- [Redis Sentinel Documentation](https://redis.io/docs/management/sentinel/)
- [Redis Persistence](https://redis.io/docs/management/persistence/)
- [Redis Security](https://redis.io/docs/management/security/)
