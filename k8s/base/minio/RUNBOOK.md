# MinIO Operational Runbook

## Quick Reference

| Operation | Command |
|-----------|---------|
| Check Status | `kubectl get statefulset minio -n ai-part-designer` |
| View Logs | `kubectl logs -f minio-0 -n ai-part-designer` |
| Access Console | `kubectl port-forward -n ai-part-designer svc/minio 9001:9001` |
| List Buckets | `mc ls k8s-minio/` |
| Check Disk Usage | `kubectl exec minio-0 -n ai-part-designer -- df -h /data` |
| Restart Pod | `kubectl delete pod minio-0 -n ai-part-designer` |

## Standard Operating Procedures

### SOP-1: Daily Health Check

**Frequency:** Daily  
**Duration:** 5 minutes  
**Responsibility:** DevOps/SRE

**Steps:**

1. Check pod status:
   ```bash
   kubectl get pod minio-0 -n ai-part-designer
   # Expected: Running, Ready 1/1
   ```

2. Verify metrics endpoint:
   ```bash
   kubectl exec minio-0 -n ai-part-designer -- wget -q -O- http://localhost:9000/minio/health/live
   # Expected: HTTP 200 OK
   ```

3. Check disk usage:
   ```bash
   kubectl exec minio-0 -n ai-part-designer -- df -h /data
   # Alert if > 80% used
   ```

4. Review recent errors in logs:
   ```bash
   kubectl logs --tail=100 minio-0 -n ai-part-designer | grep -i error
   # Expected: No critical errors
   ```

5. Verify Prometheus metrics collection:
   ```bash
   # Check in Grafana dashboard
   # Verify last scrape timestamp is < 5 minutes ago
   ```

**Escalation:**
- If pod not running: Follow SOP-6 (Pod Restart)
- If disk > 90%: Follow SOP-4 (Storage Expansion)
- If errors detected: Follow troubleshooting section

### SOP-2: Weekly Backup

**Frequency:** Weekly (Sunday 02:00 UTC)  
**Duration:** 30-60 minutes  
**Responsibility:** DevOps/SRE

**Steps:**

1. Port-forward to MinIO:
   ```bash
   kubectl port-forward -n ai-part-designer svc/minio 9000:9000 &
   PF_PID=$!
   ```

2. Configure mc client:
   ```bash
   ROOT_USER=$(kubectl get secret minio-credentials -n ai-part-designer -o jsonpath='{.data.root-user}' | base64 -d)
   ROOT_PASSWORD=$(kubectl get secret minio-credentials -n ai-part-designer -o jsonpath='{.data.root-password}' | base64 -d)
   mc alias set k8s-minio http://localhost:9000 $ROOT_USER $ROOT_PASSWORD
   ```

3. Create backup directory:
   ```bash
   BACKUP_DIR="/backups/minio/$(date +%Y%m%d-%H%M%S)"
   mkdir -p "$BACKUP_DIR"
   ```

4. Mirror critical buckets:
   ```bash
   mc mirror --preserve k8s-minio/user-uploads "$BACKUP_DIR/user-uploads"
   mc mirror --preserve k8s-minio/cad-exports "$BACKUP_DIR/cad-exports"
   mc mirror --preserve k8s-minio/design-thumbnails "$BACKUP_DIR/design-thumbnails"
   mc mirror --preserve k8s-minio/db-backups "$BACKUP_DIR/db-backups"
   
   # Environment-specific buckets
   for env in development staging production; do
     mc mirror --preserve k8s-minio/ai-part-designer-${env}-designs "$BACKUP_DIR/${env}-designs"
     mc mirror --preserve k8s-minio/ai-part-designer-${env}-exports "$BACKUP_DIR/${env}-exports"
   done
   ```

5. Create backup manifest:
   ```bash
   cat > "$BACKUP_DIR/manifest.json" <<EOF
   {
     "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
     "source_cluster": "$(kubectl config current-context)",
     "namespace": "ai-part-designer",
     "pod": "$(kubectl get pod minio-0 -n ai-part-designer -o jsonpath='{.metadata.name}')",
     "buckets": [
       $(mc ls k8s-minio/ | awk '{print "\"" $5 "\""}' | paste -sd,)
     ],
     "total_size": "$(du -sh $BACKUP_DIR | cut -f1)"
   }
   EOF
   ```

6. Compress backup (optional):
   ```bash
   tar -czf "$BACKUP_DIR.tar.gz" -C $(dirname $BACKUP_DIR) $(basename $BACKUP_DIR)
   ```

7. Upload to off-site storage:
   ```bash
   # AWS S3 example
   aws s3 cp "$BACKUP_DIR.tar.gz" s3://backups-bucket/minio/
   
   # Or Google Cloud Storage
   gsutil cp "$BACKUP_DIR.tar.gz" gs://backups-bucket/minio/
   ```

8. Clean up:
   ```bash
   kill $PF_PID
   # Keep last 4 weekly backups, delete older
   find /backups/minio -name "*.tar.gz" -mtime +28 -delete
   ```

9. Verify backup integrity:
   ```bash
   tar -tzf "$BACKUP_DIR.tar.gz" > /dev/null
   echo $?  # Expected: 0
   ```

10. Document backup:
    ```bash
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Backup completed: $BACKUP_DIR.tar.gz" >> /var/log/minio-backups.log
    ```

**Escalation:**
- If backup fails: Retry once, then escalate to senior engineer
- If backup too large (>500GB): Review retention policies

### SOP-3: Restore from Backup

**Frequency:** As needed (disaster recovery)  
**Duration:** 1-2 hours  
**Responsibility:** Senior DevOps/SRE

**⚠️ WARNING:** This procedure will overwrite existing data. Ensure you have confirmation before proceeding.

**Prerequisites:**
- Backup archive available
- Cluster access configured
- MinIO deployed and running

**Steps:**

1. Verify backup archive:
   ```bash
   tar -tzf /path/to/backup.tar.gz | head -20
   cat /path/to/backup/manifest.json
   ```

2. Extract backup:
   ```bash
   RESTORE_DIR="/tmp/minio-restore-$(date +%s)"
   mkdir -p "$RESTORE_DIR"
   tar -xzf /path/to/backup.tar.gz -C "$RESTORE_DIR"
   ```

3. Port-forward to MinIO:
   ```bash
   kubectl port-forward -n ai-part-designer svc/minio 9000:9000 &
   PF_PID=$!
   ```

4. Configure mc client:
   ```bash
   ROOT_USER=$(kubectl get secret minio-credentials -n ai-part-designer -o jsonpath='{.data.root-user}' | base64 -d)
   ROOT_PASSWORD=$(kubectl get secret minio-credentials -n ai-part-designer -o jsonpath='{.data.root-password}' | base64 -d)
   mc alias set k8s-minio http://localhost:9000 $ROOT_USER $ROOT_PASSWORD
   ```

5. Stop application pods (to prevent conflicts):
   ```bash
   kubectl scale deployment backend -n ai-part-designer --replicas=0
   kubectl scale deployment celery-worker -n ai-part-designer --replicas=0
   ```

6. Restore buckets:
   ```bash
   # Restore each bucket
   for bucket_dir in "$RESTORE_DIR"/*/; do
     bucket_name=$(basename "$bucket_dir")
     echo "Restoring bucket: $bucket_name"
     mc mirror --overwrite --preserve "$bucket_dir" "k8s-minio/$bucket_name"
   done
   ```

7. Verify restoration:
   ```bash
   # Check object counts
   mc ls --recursive k8s-minio/user-uploads | wc -l
   
   # Compare with backup manifest
   cat "$RESTORE_DIR/manifest.json"
   ```

8. Restart application pods:
   ```bash
   kubectl scale deployment backend -n ai-part-designer --replicas=3
   kubectl scale deployment celery-worker -n ai-part-designer --replicas=2
   ```

9. Test application:
   ```bash
   # Test file download
   kubectl exec -it deployment/backend -n ai-part-designer -- \
     python -c "from app.core.storage import storage_client, StorageBucket; import asyncio; asyncio.run(storage_client.list_files(StorageBucket.DESIGNS))"
   ```

10. Clean up:
    ```bash
    kill $PF_PID
    rm -rf "$RESTORE_DIR"
    ```

11. Document restoration:
    ```bash
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Restore completed from: $(basename /path/to/backup.tar.gz)" >> /var/log/minio-restores.log
    ```

### SOP-4: Storage Expansion

**Frequency:** As needed (when disk usage > 80%)  
**Duration:** 15-30 minutes  
**Responsibility:** DevOps/SRE

**Prerequisites:**
- StorageClass supports volume expansion
- Maintenance window scheduled

**Steps:**

1. Check current usage:
   ```bash
   kubectl exec minio-0 -n ai-part-designer -- df -h /data
   kubectl get pvc data-minio-0 -n ai-part-designer
   ```

2. Calculate new size:
   ```bash
   # Rule: Add 50% capacity or minimum 50Gi
   CURRENT_SIZE=$(kubectl get pvc data-minio-0 -n ai-part-designer -o jsonpath='{.spec.resources.requests.storage}')
   echo "Current size: $CURRENT_SIZE"
   # Decide new size (e.g., 100Gi)
   ```

3. Edit PVC:
   ```bash
   kubectl edit pvc data-minio-0 -n ai-part-designer
   # Change spec.resources.requests.storage to new size
   ```

4. Monitor expansion:
   ```bash
   kubectl get pvc data-minio-0 -n ai-part-designer -w
   # Wait for status to show new size
   ```

5. Delete pod to apply changes:
   ```bash
   kubectl delete pod minio-0 -n ai-part-designer
   # StatefulSet will recreate it
   ```

6. Verify expansion:
   ```bash
   kubectl wait --for=condition=ready pod/minio-0 -n ai-part-designer --timeout=5m
   kubectl exec minio-0 -n ai-part-designer -- df -h /data
   ```

7. Test application:
   ```bash
   # Upload test file
   kubectl exec -it deployment/backend -n ai-part-designer -- \
     python -c "from app.core.storage import storage_client, StorageBucket; import asyncio; asyncio.run(storage_client.upload_file(StorageBucket.TEMP, 'test.txt', b'test'))"
   ```

8. Update documentation:
   ```bash
   # Update k8s/base/minio/statefulset.yaml with new default size
   ```

### SOP-5: Credential Rotation

**Frequency:** Quarterly  
**Duration:** 30 minutes  
**Responsibility:** Security/DevOps

**Steps:**

1. Generate new credentials:
   ```bash
   NEW_ROOT_PASSWORD=$(openssl rand -base64 32)
   NEW_APP_ACCESS_KEY=$(openssl rand -hex 20)
   NEW_APP_SECRET_KEY=$(openssl rand -base64 40)
   ```

2. Update OpenBao:
   ```bash
   kubectl port-forward -n openbao svc/openbao 8200:8200 &
   export VAULT_ADDR=http://localhost:8200
   export VAULT_TOKEN=$(kubectl get secret openbao-unseal-keys -n openbao -o jsonpath='{.data.root-token}' | base64 -d)
   
   # Update root password
   openbao kv patch secret/ai-part-designer/storage/minio-credentials \
     root_password="$NEW_ROOT_PASSWORD"
   
   # Update app credentials
   openbao kv patch secret/ai-part-designer/storage/minio-app-credentials \
     access_key_id="$NEW_APP_ACCESS_KEY" \
     secret_access_key="$NEW_APP_SECRET_KEY"
   ```

3. Wait for External Secrets sync (or force refresh):
   ```bash
   kubectl annotate externalsecret minio-credentials -n ai-part-designer force-sync="$(date +%s)"
   kubectl annotate externalsecret minio-app-credentials -n ai-part-designer force-sync="$(date +%s)"
   
   # Wait 1-2 minutes
   ```

4. Restart MinIO pod:
   ```bash
   kubectl delete pod minio-0 -n ai-part-designer
   kubectl wait --for=condition=ready pod/minio-0 -n ai-part-designer --timeout=5m
   ```

5. Update MinIO user credentials:
   ```bash
   kubectl port-forward -n ai-part-designer svc/minio 9000:9000 &
   
   ROOT_USER=$(kubectl get secret minio-credentials -n ai-part-designer -o jsonpath='{.data.root-user}' | base64 -d)
   mc alias set k8s-minio http://localhost:9000 $ROOT_USER $NEW_ROOT_PASSWORD
   
   # Update app user in MinIO
   mc admin user remove k8s-minio $NEW_APP_ACCESS_KEY 2>/dev/null || true
   mc admin user add k8s-minio $NEW_APP_ACCESS_KEY $NEW_APP_SECRET_KEY
   mc admin policy attach k8s-minio app-storage-access --user=$NEW_APP_ACCESS_KEY
   ```

6. Restart application pods:
   ```bash
   kubectl rollout restart deployment/backend -n ai-part-designer
   kubectl rollout restart deployment/celery-worker -n ai-part-designer
   kubectl rollout restart deployment/celery-beat -n ai-part-designer
   ```

7. Verify connectivity:
   ```bash
   kubectl exec -it deployment/backend -n ai-part-designer -- \
     python -c "from app.core.storage import storage_client, StorageBucket; import asyncio; print(asyncio.run(storage_client.list_files(StorageBucket.TEMP)))"
   ```

8. Document rotation:
   ```bash
   echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Credentials rotated" >> /var/log/minio-credential-rotations.log
   ```

### SOP-6: Pod Restart (Unhealthy/Crashed)

**Frequency:** As needed  
**Duration:** 5-10 minutes  
**Responsibility:** DevOps/SRE

**Steps:**

1. Check pod status:
   ```bash
   kubectl get pod minio-0 -n ai-part-designer
   kubectl describe pod minio-0 -n ai-part-designer
   ```

2. Collect logs before restart:
   ```bash
   kubectl logs minio-0 -n ai-part-designer > /tmp/minio-crash-$(date +%s).log
   kubectl logs minio-0 -n ai-part-designer --previous >> /tmp/minio-crash-$(date +%s).log 2>/dev/null
   ```

3. Delete pod (StatefulSet will recreate):
   ```bash
   kubectl delete pod minio-0 -n ai-part-designer
   ```

4. Monitor recreation:
   ```bash
   kubectl get pod minio-0 -n ai-part-designer -w
   # Wait for Running and Ready 1/1
   ```

5. Verify health:
   ```bash
   kubectl exec minio-0 -n ai-part-designer -- wget -q -O- http://localhost:9000/minio/health/live
   ```

6. Check application connectivity:
   ```bash
   kubectl exec -it deployment/backend -n ai-part-designer -- curl http://minio:9000/minio/health/live
   ```

7. Review logs for errors:
   ```bash
   kubectl logs minio-0 -n ai-part-designer | tail -50
   ```

**Escalation:**
- If pod fails to restart after 3 attempts: Check PVC status, escalate to senior engineer
- If persistent failures: Review resource limits, check cluster capacity

## Incident Response

### Incident: MinIO Unavailable

**Symptoms:**
- Application errors: "Connection refused" or "Timeout" to MinIO
- Health checks failing
- Prometheus alert: `MinIODown`

**Initial Response:**

1. Check pod status:
   ```bash
   kubectl get pod minio-0 -n ai-part-designer
   ```

2. Check service:
   ```bash
   kubectl get svc minio -n ai-part-designer
   kubectl get endpoints minio -n ai-part-designer
   ```

3. Check logs:
   ```bash
   kubectl logs minio-0 -n ai-part-designer --tail=100
   ```

**Resolution Paths:**

A. **Pod crashed:**
   - Follow SOP-6 (Pod Restart)

B. **PVC issues:**
   ```bash
   kubectl describe pvc data-minio-0 -n ai-part-designer
   # If PVC stuck: Check StorageClass, CSI driver, node capacity
   ```

C. **Network policy blocking:**
   ```bash
   kubectl get networkpolicy -n ai-part-designer
   # Test connectivity from backend pod
   kubectl exec -it deployment/backend -n ai-part-designer -- nc -zv minio 9000
   ```

D. **Credential issues:**
   ```bash
   kubectl get secret minio-credentials -n ai-part-designer
   # Check External Secrets sync status
   kubectl describe externalsecret minio-credentials -n ai-part-designer
   ```

### Incident: High Disk Usage

**Symptoms:**
- Prometheus alert: `MinIONodeDiskFull`
- Upload failures
- Disk usage > 90%

**Initial Response:**

1. Check disk usage:
   ```bash
   kubectl exec minio-0 -n ai-part-designer -- df -h /data
   ```

2. Identify large buckets:
   ```bash
   kubectl port-forward -n ai-part-designer svc/minio 9000:9000 &
   mc du k8s-minio/ | sort -h
   ```

**Resolution Paths:**

A. **Temp files not expiring:**
   ```bash
   # Check lifecycle rules
   mc ilm ls k8s-minio/ai-part-designer-development-temp
   
   # Manually delete old temp files
   mc find k8s-minio/ai-part-designer-development-temp --older-than 7d --exec "mc rm {}"
   ```

B. **Old backups:**
   ```bash
   # Check db-backups bucket
   mc find k8s-minio/db-backups --older-than 30d --exec "mc rm {}"
   ```

C. **Storage expansion needed:**
   - Follow SOP-4 (Storage Expansion)

### Incident: High Error Rate

**Symptoms:**
- Prometheus alert: `MinIOHighErrorRate`
- Application errors in logs
- 500/503 responses from MinIO

**Initial Response:**

1. Check MinIO metrics:
   ```bash
   # View in Grafana or query Prometheus
   rate(minio_s3_errors_total[5m])
   ```

2. Check MinIO logs:
   ```bash
   kubectl logs minio-0 -n ai-part-designer | grep -i error | tail -50
   ```

**Resolution Paths:**

A. **Resource constraints:**
   ```bash
   kubectl top pod minio-0 -n ai-part-designer
   # If CPU/memory at limits, increase in StatefulSet
   ```

B. **Network issues:**
   ```bash
   # Test latency
   kubectl exec -it deployment/backend -n ai-part-designer -- time curl http://minio:9000/minio/health/live
   ```

C. **Invalid credentials:**
   - Check application credentials
   - Verify user policies in MinIO

## Maintenance Windows

### Monthly Maintenance (First Sunday, 02:00-04:00 UTC)

1. Update MinIO version (if new security patches)
2. Review and optimize bucket policies
3. Audit access logs
4. Review disk usage trends
5. Test disaster recovery procedure (quarterly)

### Quarterly Security Review

1. Rotate credentials (SOP-5)
2. Review user access policies
3. Audit bucket permissions
4. Update MinIO to latest stable version
5. Review security advisories

## Contacts

| Role | Contact | Escalation Level |
|------|---------|------------------|
| On-Call SRE | PagerDuty | L1 |
| Senior DevOps | Slack #devops | L2 |
| Platform Lead | Email | L3 |

## References

- [MinIO README](./README.md)
- [OpenBao Secrets Management](/k8s/base/openbao/README.md)
- [External Secrets Operator Docs](https://external-secrets.io/)
- [MinIO Admin Guide](https://min.io/docs/minio/linux/administration/)

---

*Last Updated: 2026-02-06*
