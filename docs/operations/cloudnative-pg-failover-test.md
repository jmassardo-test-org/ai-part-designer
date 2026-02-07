# CloudNativePG Failover Testing Procedure

This document provides step-by-step instructions for testing PostgreSQL failover in the CloudNativePG cluster.

## Purpose

Validate that the PostgreSQL cluster can automatically recover from primary node failures with minimal downtime and zero data loss.

## Prerequisites

- Access to Kubernetes cluster with `kubectl` configured
- Ability to monitor application metrics
- Notification to stakeholders about planned test

## Pre-Test Checklist

- [ ] All cluster pods are healthy (`kubectl get pods -n ai-part-designer -l postgresql=postgres-cluster`)
- [ ] Replication lag is minimal (< 1 second)
- [ ] Recent backup exists (`kubectl get backup -n ai-part-designer`)
- [ ] Monitoring dashboards are accessible
- [ ] Stakeholders are notified of test window

## Test Procedure

### Step 1: Record Baseline Metrics

```bash
# Set namespace variable for convenience
NAMESPACE=ai-part-designer
CLUSTER_NAME=postgres-cluster

# Identify current primary
PRIMARY=$(kubectl get cluster -n $NAMESPACE $CLUSTER_NAME -o jsonpath='{.status.currentPrimary}')
echo "Current primary: $PRIMARY"

# Record replication status
kubectl exec -it -n $NAMESPACE $PRIMARY -- psql -U postgres -c "
  SELECT 
    client_addr, 
    state, 
    sync_state,
    pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes,
    replay_lag 
  FROM pg_stat_replication;
"

# Record transaction counts
kubectl exec -it -n $NAMESPACE $PRIMARY -- psql -U postgres -d assemblematic_ai -c "
  SELECT 
    xact_commit, 
    xact_rollback 
  FROM pg_stat_database 
  WHERE datname = 'assemblematic_ai';
"

# Save current time
echo "Test started at: $(date -Iseconds)"
```

### Step 2: Simulate Primary Failure

```bash
# Delete primary pod to simulate failure
echo "Deleting primary pod: $PRIMARY"
kubectl delete pod -n $NAMESPACE $PRIMARY

# Record deletion time
echo "Primary deleted at: $(date -Iseconds)"
```

### Step 3: Monitor Failover

```bash
# Watch cluster status (Ctrl+C to exit)
watch -n 1 "kubectl get cluster -n $NAMESPACE $CLUSTER_NAME"

# In another terminal, watch pod status
watch -n 1 "kubectl get pods -n $NAMESPACE -l postgresql=$CLUSTER_NAME -L role"
```

**Expected Behavior:**
- Cluster status changes to "Promoting replica" within 30 seconds
- New primary is elected within 60 seconds
- Old primary rejoins as replica when it comes back

### Step 4: Verify New Primary

```bash
# Get new primary
NEW_PRIMARY=$(kubectl get cluster -n $NAMESPACE $CLUSTER_NAME -o jsonpath='{.status.currentPrimary}')
echo "New primary: $NEW_PRIMARY"

# Verify it's different from original
if [ "$NEW_PRIMARY" != "$PRIMARY" ]; then
  echo "✓ Failover successful - new primary is different"
else
  echo "✗ Failover failed - primary unchanged"
  exit 1
fi

# Check replication status on new primary
kubectl exec -it -n $NAMESPACE $NEW_PRIMARY -- psql -U postgres -c "
  SELECT 
    client_addr, 
    state, 
    sync_state,
    replay_lag 
  FROM pg_stat_replication;
"
```

### Step 5: Verify Application Connectivity

```bash
# Check backend logs for database errors
kubectl logs -n $NAMESPACE -l app.kubernetes.io/name=backend --tail=50 --since=5m | grep -i "database\|postgres\|connection"

# Test connection from backend pod
BACKEND_POD=$(kubectl get pod -n $NAMESPACE -l app.kubernetes.io/name=backend -o name | head -1)
kubectl exec -it -n $NAMESPACE $BACKEND_POD -- python -c "
import asyncpg
import asyncio

async def test():
    conn = await asyncpg.connect(
        host='postgres-pooler-service',
        port=5432,
        user='app',
        password='PASSWORD',
        database='assemblematic_ai'
    )
    result = await conn.fetchval('SELECT COUNT(*) FROM users')
    await conn.close()
    print(f'✓ Connected successfully. User count: {result}')

asyncio.run(test())
"
```

### Step 6: Verify Data Consistency

```bash
# Check transaction counts match baseline
kubectl exec -it -n $NAMESPACE $NEW_PRIMARY -- psql -U postgres -d assemblematic_ai -c "
  SELECT 
    xact_commit, 
    xact_rollback 
  FROM pg_stat_database 
  WHERE datname = 'assemblematic_ai';
"

# Query sample data
kubectl exec -it -n $NAMESPACE $NEW_PRIMARY -- psql -U postgres -d assemblematic_ai -c "
  SELECT COUNT(*) as user_count FROM users;
  SELECT COUNT(*) as design_count FROM designs;
"
```

### Step 7: Verify Old Primary Rejoins

```bash
# Wait for old primary pod to restart (usually 2-3 minutes)
kubectl wait --for=condition=ready pod/$PRIMARY -n $NAMESPACE --timeout=5m

# Check its role (should be 'replica')
kubectl get pod -n $NAMESPACE $PRIMARY -L role

# Verify it's replicating
kubectl exec -it -n $NAMESPACE $NEW_PRIMARY -- psql -U postgres -c "
  SELECT client_addr, state, sync_state 
  FROM pg_stat_replication 
  WHERE application_name LIKE '%$PRIMARY%';
"
```

## Metrics to Record

| Metric | Expected | Actual |
|--------|----------|--------|
| Time to detect failure | < 30 seconds | |
| Time to elect new primary | < 60 seconds | |
| Total downtime | < 60 seconds | |
| Application connection errors | Brief spike during switchover | |
| Data loss | 0 rows | |
| Replication lag after failover | < 1 second | |
| Old primary rejoin time | < 5 minutes | |

## Success Criteria

✅ **Pass** if all criteria are met:
- [ ] New primary elected within 60 seconds
- [ ] Zero data loss (transaction counts match)
- [ ] Application can connect to new primary
- [ ] Old primary rejoins as replica
- [ ] Replication resumes normally
- [ ] No persistent errors in logs

❌ **Fail** if any criteria fails - investigate before production use

## Post-Test Actions

```bash
# Verify cluster health
kubectl get cluster -n $NAMESPACE $CLUSTER_NAME

# Check all pods are healthy
kubectl get pods -n $NAMESPACE -l postgresql=$CLUSTER_NAME

# Verify replication is working
kubectl exec -it -n $NAMESPACE $NEW_PRIMARY -- psql -U postgres -c "
  SELECT * FROM pg_stat_replication;
"

# Check backup status (ensure backups still work)
kubectl get backup -n $NAMESPACE --sort-by=.metadata.creationTimestamp

# Document results
echo "Test completed at: $(date -Iseconds)"
```

## Rollback (If Test Fails)

If failover fails or causes issues:

```bash
# Option 1: Force specific pod as primary
kubectl cnpg promote -n $NAMESPACE $CLUSTER_NAME postgres-cluster-2

# Option 2: Restart entire cluster
kubectl delete pod -n $NAMESPACE -l postgresql=$CLUSTER_NAME

# Option 3: Restore from backup (last resort)
# See operations guide for restore procedure
```

## Troubleshooting

### Failover Takes Too Long

**Possible Causes:**
- Network issues
- Insufficient resources
- Consensus problems

**Actions:**
```bash
# Check operator logs
kubectl logs -n cnpg-system -l app.kubernetes.io/name=cloudnative-pg --tail=100

# Check cluster events
kubectl describe cluster -n $NAMESPACE $CLUSTER_NAME

# Check pod events
kubectl describe pod -n $NAMESPACE $PRIMARY
```

### Application Connection Errors Persist

**Possible Causes:**
- Connection pooler not updated
- DNS cache issues
- Application connection pool not refreshed

**Actions:**
```bash
# Restart pooler
kubectl rollout restart deployment -n $NAMESPACE -l cnpg.io/poolerName=postgres-pooler

# Restart application pods
kubectl rollout restart deployment -n $NAMESPACE backend
kubectl rollout restart deployment -n $NAMESPACE celery-worker
```

### Old Primary Won't Rejoin

**Possible Causes:**
- Data corruption
- Disk issues
- Configuration mismatch

**Actions:**
```bash
# Check pod logs
kubectl logs -n $NAMESPACE $PRIMARY

# Check events
kubectl describe pod -n $NAMESPACE $PRIMARY

# Force recreation if needed
kubectl delete pod -n $NAMESPACE $PRIMARY --force
```

## Frequency

- **Development**: Monthly
- **Staging**: Monthly
- **Production**: Quarterly (during maintenance window)

## Documentation

After each test, document:
1. Test date and time
2. Metrics observed
3. Any issues encountered
4. Actions taken
5. Recommendations for improvement

Save test reports in: `docs/operations/failover-test-reports/`

## References

- [CloudNativePG Failover Documentation](https://cloudnative-pg.io/documentation/current/failover/)
- [Operations Guide](cloudnative-pg-operations.md)
- [PostgreSQL High Availability](https://www.postgresql.org/docs/current/high-availability.html)

---

**Version**: 1.0  
**Last Updated**: 2024-03-20  
**Owner**: Platform Operations Team
