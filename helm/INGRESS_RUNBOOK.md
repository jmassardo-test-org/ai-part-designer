# NGINX Ingress and cert-manager Operations Runbook

## Overview

This runbook provides operational procedures for managing NGINX Ingress Controller and cert-manager in the AI Part Designer platform.

**Owner:** Platform Operations Team  
**On-Call Contact:** Platform on-call rotation  
**Last Updated:** 2026-02-07

---

## Quick Reference

| Component | Health Check | Dashboard | Logs |
|-----------|--------------|-----------|------|
| NGINX Ingress | `kubectl get pods -n <namespace> -l app.kubernetes.io/name=ingress-nginx` | Grafana (if enabled) | `kubectl logs -n <namespace> -l app.kubernetes.io/name=ingress-nginx` |
| cert-manager | `kubectl get pods -n cert-manager` | N/A | `kubectl logs -n cert-manager -l app=cert-manager` |
| Certificates | `kubectl get certificate -n <namespace>` | N/A | `kubectl describe certificate <name> -n <namespace>` |

---

## Standard Operating Procedures

### SOP-01: Check Ingress Health

**Frequency:** Daily (automated monitoring)  
**Duration:** 2 minutes

```bash
# 1. Check ingress controller pods
kubectl get pods -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx

# Expected: All pods Running/Ready
# RUNNING   1/1     Running   0          5d

# 2. Check load balancer external IP
kubectl get svc -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx

# Expected: EXTERNAL-IP assigned
# TYPE           EXTERNAL-IP      PORT(S)
# LoadBalancer   203.0.113.50     80:30080/TCP,443:30443/TCP

# 3. Test HTTP→HTTPS redirect
curl -I http://app.example.com

# Expected: 301 or 308 redirect

# 4. Test HTTPS access
curl -I https://app.example.com

# Expected: 200 OK
```

**Success Criteria:**
- All pods in Running state
- External IP assigned
- HTTP redirects to HTTPS
- HTTPS returns 200 OK

**Failure Actions:** See Troubleshooting section

---

### SOP-02: Check Certificate Health

**Frequency:** Daily (automated monitoring)  
**Duration:** 2 minutes

```bash
# 1. List all certificates
kubectl get certificate -n ai-part-designer-prod

# Expected: READY = True
# NAME                    READY   SECRET                  AGE
# ai-part-designer-tls    True    ai-part-designer-tls    30d

# 2. Check certificate expiry
kubectl get certificate -n ai-part-designer-prod -o json | \
  jq '.items[] | {name: .metadata.name, notAfter: .status.notAfter}'

# Expected: notAfter > 30 days from now

# 3. Check certificate details
kubectl describe certificate ai-part-designer-tls -n ai-part-designer-prod

# Expected: Status.Conditions shows Ready=True
```

**Success Criteria:**
- All certificates show READY=True
- Certificates have > 30 days until expiry
- No error conditions

**Failure Actions:** See SOP-06 for certificate renewal

---

### SOP-03: Monitor Rate Limiting

**Frequency:** Weekly or when investigating 503 errors  
**Duration:** 5 minutes

```bash
# 1. Check NGINX logs for rate limit drops
kubectl logs -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx \
  --tail=1000 | grep "limiting requests"

# Look for patterns indicating heavy rate limiting

# 2. Check Prometheus metrics (if available)
# Query: rate(nginx_ingress_controller_requests{status="503"}[5m])

# 3. Identify top client IPs being rate limited
kubectl logs -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx \
  --tail=5000 | grep "limiting requests" | awk '{print $7}' | sort | uniq -c | sort -rn | head -10
```

**Decision Tree:**
- **Legitimate traffic spike**: Increase rate limits temporarily (see SOP-08)
- **Abuse/attack**: Keep limits, consider blocking IP at firewall
- **Normal operation**: No action needed

---

### SOP-04: Update Ingress Configuration

**Frequency:** As needed  
**Duration:** 10 minutes  
**Change Window:** Non-peak hours recommended

```bash
# 1. Backup current configuration
kubectl get ingress ai-part-designer-ingress -n ai-part-designer-prod -o yaml > ingress-backup-$(date +%Y%m%d-%H%M%S).yaml

# 2. Edit configuration
kubectl edit ingress ai-part-designer-ingress -n ai-part-designer-prod

# OR via Helm:
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --reuse-values \
  --set ingressRateLimitRps=200 \
  --wait

# 3. Verify changes applied
kubectl get ingress ai-part-designer-ingress -n ai-part-designer-prod -o yaml

# 4. Test access
curl -I https://app.example.com
curl https://api.example.com/api/v1/health

# 5. Monitor for 5 minutes
kubectl logs -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx -f
```

**Rollback Procedure:**
```bash
# If issues detected:
kubectl apply -f ingress-backup-<timestamp>.yaml

# OR via Helm:
helm rollback ai-part-designer -n ai-part-designer-prod
```

---

### SOP-05: Rotate TLS Certificates Manually

**Frequency:** Emergency only (normal renewal is automatic)  
**Duration:** 10 minutes

```bash
# 1. Delete existing certificate (triggers recreation)
kubectl delete certificate ai-part-designer-tls -n ai-part-designer-prod

# 2. Monitor certificate recreation
kubectl get certificate -n ai-part-designer-prod -w

# Expected: READY changes from False to True within 5 minutes

# 3. Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager -f

# 4. Verify new certificate
kubectl describe certificate ai-part-designer-tls -n ai-part-designer-prod

# 5. Test HTTPS access
curl -vI https://app.example.com 2>&1 | grep "subject:\|issuer:\|expire"
```

**Success Criteria:**
- Certificate recreated successfully
- HTTPS still works
- New expiry date set

---

### SOP-06: Certificate Renewal Failure Recovery

**Frequency:** As needed when renewal fails  
**Duration:** 15 minutes

```bash
# 1. Check certificate status
kubectl describe certificate ai-part-designer-tls -n ai-part-designer-prod

# Look for error messages in Events section

# 2. Check CertificateRequest
kubectl get certificaterequest -n ai-part-designer-prod
kubectl describe certificaterequest <name> -n ai-part-designer-prod

# 3. Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager --tail=100

# 4. Common issues and fixes:

# Issue: DNS not resolving
# Fix: Verify DNS records are correct and propagated
dig app.example.com +short

# Issue: HTTP-01 challenge failing
# Fix: Ensure port 80 is accessible from internet
curl -I http://app.example.com/.well-known/acme-challenge/test

# Issue: Rate limit hit
# Fix: Switch to staging issuer temporarily
kubectl patch ingress ai-part-designer-ingress -n ai-part-designer-prod \
  --type=json -p='[{"op": "replace", "path": "/metadata/annotations/cert-manager.io~1cluster-issuer", "value": "letsencrypt-staging"}]'

# 5. Force certificate renewal
kubectl delete certificaterequest -n ai-part-designer-prod --all
kubectl delete secret ai-part-designer-tls -n ai-part-designer-prod
kubectl delete certificate ai-part-designer-tls -n ai-part-designer-prod

# Wait for recreation
kubectl get certificate -n ai-part-designer-prod -w
```

---

### SOP-07: Scale Ingress Controller

**Frequency:** During traffic spikes or maintenance  
**Duration:** 5 minutes

```bash
# 1. Check current replica count
kubectl get deployment -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx

# 2. Scale up (for high traffic)
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --reuse-values \
  --set ingress-nginx.controller.replicaCount=4 \
  --wait

# 3. Verify scaling
kubectl get pods -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx

# 4. Monitor performance
# Check request latency, error rate, CPU/memory usage

# 5. Scale down after spike
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --reuse-values \
  --set ingress-nginx.controller.replicaCount=2 \
  --wait
```

---

### SOP-08: Adjust Rate Limits

**Frequency:** As needed based on traffic patterns  
**Duration:** 5 minutes

```bash
# 1. Review current limits
kubectl get ingress ai-part-designer-ingress -n ai-part-designer-prod -o yaml | grep limit

# 2. Adjust limits via Helm
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --reuse-values \
  --set ingressRateLimitRps=200 \
  --set ingressRateLimitConnections=100 \
  --set ingressRateLimitBurst=10 \
  --wait

# 3. Monitor impact
kubectl logs -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx -f

# 4. Verify no legitimate traffic blocked
# Check application logs and user reports
```

**Recommended Limits:**
- **Development**: 500 RPS, 200 connections
- **Staging**: 200 RPS, 100 connections  
- **Production**: 100 RPS, 50 connections (adjust based on usage)

---

### SOP-09: Enable/Disable Ingress

**Frequency:** Maintenance windows or emergencies  
**Duration:** 10 minutes

```bash
# Disable ingress (route through port-forward or alternate path)
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --reuse-values \
  --set ingressEnabled=false \
  --wait

# Enable ingress
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --reuse-values \
  --set ingressEnabled=true \
  --wait

# Verify status
kubectl get ingress -n ai-part-designer-prod
```

---

## Troubleshooting Guide

### Issue: 502 Bad Gateway

**Symptoms:** Users see "502 Bad Gateway" error

**Diagnosis:**
```bash
# Check backend pod health
kubectl get pods -n ai-part-designer-prod -l app=backend
kubectl get pods -n ai-part-designer-prod -l app=frontend

# Check service endpoints
kubectl get endpoints -n ai-part-designer-prod

# Check ingress controller logs
kubectl logs -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx --tail=100
```

**Resolution:**
1. If backend pods unhealthy: Investigate application issues
2. If no endpoints: Check service selector matches pod labels
3. If ingress logs show connection refused: Backend not listening on expected port

---

### Issue: 503 Service Temporarily Unavailable

**Symptoms:** Users see "503" error or rate limit message

**Diagnosis:**
```bash
# Check for rate limiting in logs
kubectl logs -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx --tail=500 | grep limiting

# Check backend capacity
kubectl top pods -n ai-part-designer-prod -l app=backend
```

**Resolution:**
1. If rate limited: See SOP-08 to adjust limits
2. If backend overloaded: Scale backend deployment
3. If ingress controller overloaded: See SOP-07 to scale ingress

---

### Issue: Certificate Not Renewing

**Symptoms:** Certificate expiry < 30 days, READY=False

**Diagnosis:**
```bash
kubectl describe certificate ai-part-designer-tls -n ai-part-designer-prod
kubectl get certificaterequest -n ai-part-designer-prod
kubectl logs -n cert-manager -l app=cert-manager --tail=100
```

**Resolution:** See SOP-06

---

### Issue: Slow Response Times

**Symptoms:** High latency reported by users or monitoring

**Diagnosis:**
```bash
# Check ingress metrics
kubectl top pods -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx

# Check backend latency
curl -w "@curl-format.txt" -o /dev/null -s https://api.example.com/api/v1/health

# Check ingress logs for slow requests
kubectl logs -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx | grep "request_time" | awk '{print $NF}' | sort -rn | head
```

**Resolution:**
1. If ingress controller CPU high: Scale ingress (SOP-07)
2. If backend slow: Investigate application performance
3. If timeout configuration too low: Increase proxy timeouts

---

## Monitoring and Alerting

### Key Metrics to Monitor

| Metric | Warning Threshold | Critical Threshold | Action |
|--------|-------------------|-------------------|---------|
| Certificate Expiry | < 30 days | < 7 days | Investigate renewal failure |
| Ingress Controller CPU | > 70% | > 90% | Scale ingress controller |
| 5xx Error Rate | > 1% | > 5% | Investigate backend health |
| Request Latency (p95) | > 500ms | > 1000ms | Investigate performance |
| Rate Limit Drops | > 100/min | > 1000/min | Consider adjusting limits |

### Alerting Rules

```yaml
# Example Prometheus alerting rules
groups:
- name: ingress
  rules:
  - alert: CertificateExpiringSoon
    expr: certmanager_certificate_expiration_timestamp_seconds - time() < 7 * 24 * 3600
    annotations:
      summary: "Certificate {{ $labels.name }} expiring in < 7 days"
      
  - alert: IngressHighErrorRate
    expr: rate(nginx_ingress_controller_requests{status=~"5.."}[5m]) > 0.05
    annotations:
      summary: "Ingress 5xx error rate > 5%"
```

---

## Disaster Recovery

### Scenario: Complete Ingress Controller Failure

**RTO:** 15 minutes  
**RPO:** 0 (stateless component)

```bash
# 1. Verify failure
kubectl get pods -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx

# 2. Reinstall ingress controller
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --reuse-values \
  --force \
  --wait

# 3. Verify recovery
kubectl get svc -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx
curl -I https://app.example.com

# 4. Check DNS still points to external IP
dig app.example.com +short
```

---

### Scenario: All Certificates Expired

**RTO:** 30 minutes  
**RPO:** 0

```bash
# 1. Delete all expired certificates
kubectl delete certificate --all -n ai-part-designer-prod

# 2. Ensure DNS records are correct
dig app.example.com +short
dig api.example.com +short

# 3. Recreate certificates
kubectl apply -k k8s/overlays/production

# 4. Monitor recreation
kubectl get certificate -n ai-part-designer-prod -w

# 5. If Let's Encrypt rate limited, use staging temporarily
kubectl patch ingress ai-part-designer-ingress -n ai-part-designer-prod \
  --type=json -p='[{"op": "replace", "path": "/metadata/annotations/cert-manager.io~1cluster-issuer", "value": "letsencrypt-staging"}]'
```

---

## Maintenance Windows

### Pre-Maintenance Checklist

- [ ] Notify users of maintenance window
- [ ] Backup current ingress configuration
- [ ] Backup current certificates
- [ ] Verify rollback procedure
- [ ] Have on-call engineer available

### Post-Maintenance Checklist

- [ ] Verify ingress controller pods healthy
- [ ] Verify certificates valid
- [ ] Test HTTP→HTTPS redirect
- [ ] Test frontend access
- [ ] Test API access
- [ ] Monitor for 1 hour post-change
- [ ] Update runbook with lessons learned

---

## Escalation Paths

| Severity | First Response | Escalation (if unresolved in 30 min) |
|----------|---------------|-------------------------------------|
| SEV1 (Complete outage) | Platform On-Call | Platform Lead + Engineering Manager |
| SEV2 (Degraded service) | Platform On-Call | Platform Lead |
| SEV3 (Minor issue) | Platform Team | Platform Lead (next business day) |

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-07 | Initial creation | Platform Ops Agent |

---

## References

- [NGINX Ingress Controller Docs](https://kubernetes.github.io/ingress-nginx/)
- [cert-manager Docs](https://cert-manager.io/docs/)
- [Let's Encrypt Rate Limits](https://letsencrypt.org/docs/rate-limits/)
- [DNS Configuration Guide](../k8s/DNS_CONFIGURATION.md)
- [Ingress Setup Guide](./INGRESS_SETUP.md)
