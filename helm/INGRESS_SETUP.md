# NGINX Ingress and cert-manager Setup Guide

This guide covers the setup and configuration of NGINX Ingress Controller and cert-manager for external access to the AI Part Designer application.

## Overview

The Helm chart includes optional dependencies for:
- **NGINX Ingress Controller** - Routes external traffic to frontend and backend services
- **cert-manager** - Automates TLS certificate provisioning and renewal

## When to Enable Ingress

| Environment | Ingress Enabled | Use Case |
|-------------|-----------------|----------|
| Development | No (default) | Use `kubectl port-forward` for local access |
| Staging | Yes | Test production-like setup with real domains |
| Production | Yes | Full external access with production certificates |

## Quick Start

### Enable Ingress in Helm Values

The chart provides three ClusterIssuers for different scenarios:

1. **letsencrypt-prod** - Production trusted certificates (strict rate limits)
2. **letsencrypt-staging** - Testing certificates (relaxed rate limits, not trusted)
3. **selfsigned** - Self-signed certificates for dev/internal use

### Staging Deployment with Ingress

```bash
# Update values-staging.yaml or use --set flags
helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-staging \
  --create-namespace \
  --values helm/ai-part-designer/values-staging.yaml \
  --set installIngress=true \
  --set installCerts=true \
  --set ingressEnabled=true \
  --set ingressHost=staging.yourdomain.com \
  --set ingressCertIssuer=letsencrypt-staging \
  --wait \
  --timeout 15m
```

### Production Deployment with Ingress

```bash
# Update values-production.yaml with your actual domain
helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --create-namespace \
  --values helm/ai-part-designer/values-production.yaml \
  --wait \
  --timeout 20m
```

Production values already include:
```yaml
installIngress: true
installCerts: true
ingressEnabled: true
ingressCertIssuer: "letsencrypt-prod"
```

## Configuration Options

### Single Domain vs Multi-Domain Routing

#### Single Domain (Path-Based Routing)

All traffic through one domain with path prefixes:

```yaml
ingressEnabled: true
ingressMultiDomain: false
ingressHost: "app.example.com"
```

**Routes:**
- `https://app.example.com/` → Frontend
- `https://app.example.com/api` → Backend API
- `https://app.example.com/docs` → API Documentation

**Best for:** Simpler DNS setup, single certificate

#### Multi-Domain (Subdomain Routing)

Separate subdomains for frontend and API:

```yaml
ingressEnabled: true
ingressMultiDomain: true
ingressFrontendHost: "app.example.com"
ingressBackendHost: "api.example.com"
```

**Routes:**
- `https://app.example.com/` → Frontend
- `https://api.example.com/` → Backend API
- `https://api.example.com/docs` → API Documentation

**Best for:** Clear API separation, independent scaling

### Rate Limiting Configuration

Protect against abuse with configurable rate limits:

```yaml
# Development - Relaxed limits
ingressRateLimitRps: "500"           # 500 requests/sec per IP
ingressRateLimitConnections: "200"   # 200 concurrent connections
ingressRateLimitBurst: "10"          # Allow 10x burst

# Production - Strict limits
ingressRateLimitRps: "100"           # 100 requests/sec per IP
ingressRateLimitConnections: "50"    # 50 concurrent connections
ingressRateLimitBurst: "5"           # Allow 5x burst
```

Rate limiting applies per client IP address.

### File Upload Limits

CAD files and exports require larger request sizes:

```yaml
ingressMaxBodySize: "100m"              # Max upload size (100MB default)
ingressClientBodyBufferSize: "10m"      # Client buffer size
```

### Timeout Configuration

AI CAD generation can take time:

```yaml
ingressProxyConnectTimeout: "300"    # 5 minutes
ingressProxySendTimeout: "300"       # 5 minutes
ingressProxyReadTimeout: "300"       # 5 minutes
```

### Security Headers

Pre-configured security headers (customizable):

```yaml
ingressSecurityHeaders:
  xFrameOptions: "DENY"              # Prevent clickjacking

ingressHstsMaxAge: "31536000"        # HSTS: 1 year
ingressHstsPreload: "true"           # Submit to preload list
```

Headers automatically applied:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security` with preload

### Additional Annotations

Add custom NGINX annotations:

```yaml
ingressAdditionalAnnotations:
  nginx.ingress.kubernetes.io/custom-annotation: "value"
  kubernetes.io/tls-acme: "true"
```

## Post-Deployment Steps

### 1. Get Load Balancer External Address

```bash
kubectl get svc -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx

# Example output:
# NAME                                         TYPE           EXTERNAL-IP
# ai-part-designer-ingress-nginx-controller    LoadBalancer   203.0.113.50
```

### 2. Configure DNS Records

See [DNS Configuration Guide](../k8s/DNS_CONFIGURATION.md) for detailed instructions.

**Quick setup for single domain:**
```
A       app.example.com      <EXTERNAL-IP>
```

**Quick setup for multi-domain:**
```
A       app.example.com      <EXTERNAL-IP>
A       api.example.com      <EXTERNAL-IP>
```

### 3. Verify Certificate Provisioning

```bash
# Watch certificate status
kubectl get certificate -n ai-part-designer-prod -w

# Expected output after DNS propagates:
# NAME                    READY   SECRET                  AGE
# ai-part-designer-tls    True    ai-part-designer-tls    5m
```

Certificate issuance typically takes 2-5 minutes after DNS propagates.

### 4. Test Access

```bash
# Test HTTP→HTTPS redirect
curl -I http://app.example.com
# Should return: 301 or 308 Moved Permanently

# Test HTTPS access
curl https://app.example.com
# Should return: 200 OK with HTML

# Test API health check
curl https://api.example.com/api/v1/health
# OR for single domain:
curl https://app.example.com/api/v1/health
# Should return: {"status": "healthy"}
```

## Troubleshooting

### Certificate Not Issuing

**Symptoms:** Certificate shows `READY: False`

**Diagnosis:**
```bash
kubectl describe certificate ai-part-designer-tls -n ai-part-designer-prod
kubectl get certificaterequest -n ai-part-designer-prod
kubectl logs -n cert-manager -l app=cert-manager
```

**Common causes:**
1. DNS not propagated (wait 5-60 minutes)
2. Port 80 blocked by firewall (required for HTTP-01 challenge)
3. ClusterIssuer misconfigured
4. Rate limit hit (switch to staging issuer)

**Fix:**
```bash
# Switch to staging issuer temporarily
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --reuse-values \
  --set ingressCertIssuer=letsencrypt-staging
```

### Ingress Controller Not Starting

**Diagnosis:**
```bash
kubectl get pods -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx
kubectl logs -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx
```

**Common causes:**
1. Admission webhook not ready
2. Resource constraints
3. Port conflicts

**Fix:**
```bash
# Check admission webhook
kubectl get validatingwebhookconfiguration | grep ingress

# Increase resources if needed
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --reuse-values \
  --set ingress-nginx.controller.resources.requests.memory=512Mi
```

### 404 Not Found

**Diagnosis:**
```bash
kubectl get ingress -n ai-part-designer-prod
kubectl describe ingress ai-part-designer-ingress -n ai-part-designer-prod
kubectl get endpoints -n ai-part-designer-prod
```

**Common causes:**
1. Backend pods not running
2. Service name mismatch
3. Ingress rules incorrect

**Fix:** Verify backend pods are healthy:
```bash
kubectl get pods -n ai-part-designer-prod -l app=backend
kubectl get pods -n ai-part-designer-prod -l app=frontend
```

### Rate Limiting Too Aggressive

**Symptoms:** Users getting 503 or 429 errors

**Fix:** Increase rate limits:
```bash
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --reuse-values \
  --set ingressRateLimitRps=200 \
  --set ingressRateLimitConnections=100
```

### CORS Errors

**Symptoms:** Browser console shows CORS policy errors

**Fix:** Update backend CORS configuration:
```bash
# For single domain
kubectl set env deployment/backend -n ai-part-designer-prod \
  CORS_ORIGINS='["https://app.example.com"]'

# For multi-domain
kubectl set env deployment/backend -n ai-part-designer-prod \
  CORS_ORIGINS='["https://app.example.com","https://api.example.com"]'
```

## Upgrading Configuration

### Update Ingress Settings

```bash
# Modify values file, then:
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --values helm/ai-part-designer/values-production.yaml \
  --wait
```

### Switch Certificate Issuer

```bash
# From staging to production
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --reuse-values \
  --set ingressCertIssuer=letsencrypt-prod

# Delete old certificate to trigger reissuance
kubectl delete certificate ai-part-designer-tls -n ai-part-designer-prod
```

## Uninstalling Ingress

To remove ingress while keeping the application:

```bash
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --reuse-values \
  --set installIngress=false \
  --set installCerts=false \
  --set ingressEnabled=false
```

## Security Best Practices

1. **Always use production certificates in production** - Never use staging or self-signed
2. **Configure appropriate rate limits** - Balance user experience and abuse protection
3. **Enable HSTS with preload** - Already configured, consider submitting to preload list
4. **Regular certificate monitoring** - Set up alerts for expiring certificates
5. **Review NGINX logs** - Monitor for unusual traffic patterns
6. **Use multi-domain for API isolation** - Separate frontend and API domains
7. **Keep ingress-nginx updated** - Apply security patches regularly

## Monitoring

### Certificate Expiration

```bash
# Check certificate expiry
kubectl get certificate -n ai-part-designer-prod -o json | \
  jq '.items[] | {name: .metadata.name, notAfter: .status.notAfter}'
```

### Ingress Metrics

If Prometheus is enabled:

```promql
# Request rate per second
rate(nginx_ingress_controller_requests[5m])

# Error rate
rate(nginx_ingress_controller_requests{status=~"5.."}[5m])

# Certificate expiry time
certmanager_certificate_expiration_timestamp_seconds
```

## Additional Resources

- [Complete DNS Configuration Guide](../k8s/DNS_CONFIGURATION.md)
- [NGINX Ingress Controller Docs](https://kubernetes.github.io/ingress-nginx/)
- [cert-manager Docs](https://cert-manager.io/docs/)
- [Let's Encrypt Rate Limits](https://letsencrypt.org/docs/rate-limits/)
