# DNS Configuration Guide for AI Part Designer

This guide explains how to configure DNS records for external access to the AI Part Designer application after deploying NGINX Ingress Controller.

## Overview

The AI Part Designer supports two routing configurations:

1. **Single Domain with Path-Based Routing** - All traffic through one domain
2. **Multi-Domain with Subdomain Routing** - Separate domains for frontend and API

## Prerequisites

- NGINX Ingress Controller deployed and running
- Load balancer external IP or hostname assigned
- Access to your DNS provider's management console

## Step 1: Get Ingress Load Balancer Address

After deploying the Helm chart with ingress enabled, retrieve the external address:

```bash
# Get the external IP or hostname
kubectl get svc -n ai-part-designer -l app.kubernetes.io/name=ingress-nginx

# Example output:
# NAME                                    TYPE           EXTERNAL-IP
# ai-part-designer-ingress-nginx-controller  LoadBalancer   203.0.113.50
```

Note the `EXTERNAL-IP` value. This will be used in your DNS records.

## Step 2: Configure DNS Records

### Option A: Single Domain Configuration

For path-based routing (e.g., `app.assemblematic.ai` with `/api` for backend):

**DNS Records:**
```
A       app.assemblematic.ai      203.0.113.50
```

**Helm Values:**
```yaml
ingressEnabled: true
ingressHost: "app.assemblematic.ai"
ingressMultiDomain: false
ingressTlsSecret: "ai-part-designer-tls"
ingressCertIssuer: "letsencrypt-prod"
```

**Access URLs:**
- Frontend: `https://app.assemblematic.ai`
- API: `https://app.assemblematic.ai/api`
- API Docs: `https://app.assemblematic.ai/docs`

### Option B: Multi-Domain Configuration

For subdomain-based routing (separate domains for frontend and API):

**DNS Records:**
```
A       app.assemblematic.ai      203.0.113.50
A       api.assemblematic.ai      203.0.113.50
```

**Helm Values:**
```yaml
ingressEnabled: true
ingressMultiDomain: true
ingressFrontendHost: "app.assemblematic.ai"
ingressBackendHost: "api.assemblematic.ai"
ingressTlsSecret: "ai-part-designer-tls"
ingressCertIssuer: "letsencrypt-prod"
```

**Access URLs:**
- Frontend: `https://app.assemblematic.ai`
- API: `https://api.assemblematic.ai`
- API Docs: `https://api.assemblematic.ai/docs`

## Step 3: Verify DNS Propagation

Wait for DNS propagation (typically 5-60 minutes):

```bash
# Check DNS resolution
dig app.assemblematic.ai +short
nslookup app.assemblematic.ai

# For multi-domain setup, also check:
dig api.assemblematic.ai +short
```

## Step 4: Verify TLS Certificate Provisioning

After DNS propagates, cert-manager will automatically provision certificates:

```bash
# Check certificate status
kubectl get certificate -n ai-part-designer

# Check certificate details
kubectl describe certificate ai-part-designer-tls -n ai-part-designer

# Check cert-manager logs if issues occur
kubectl logs -n cert-manager -l app=cert-manager -f
```

Expected output after successful provisioning:
```
NAME                    READY   SECRET                  AGE
ai-part-designer-tls    True    ai-part-designer-tls    5m
```

## Step 5: Test Access

```bash
# Test HTTPS redirect
curl -I http://app.assemblematic.ai
# Should return 301 or 308 redirect to HTTPS

# Test HTTPS access
curl -I https://app.assemblematic.ai
# Should return 200 OK

# Test API health endpoint
curl https://api.assemblematic.ai/api/v1/health
# OR for single domain:
curl https://app.assemblematic.ai/api/v1/health
```

## Environment-Specific Configurations

### Development

Development typically uses port-forwarding instead of ingress:

```bash
# Port forward frontend
kubectl port-forward -n ai-part-designer svc/frontend 8080:80

# Port forward backend
kubectl port-forward -n ai-part-designer svc/backend 8000:8000
```

For local DNS testing with ingress:
```
# Add to /etc/hosts (requires ingress external IP)
203.0.113.50  dev.ai-part-designer.local
```

```yaml
# values-dev.yaml
ingressEnabled: false  # Use port-forward by default
ingressHost: "dev.ai-part-designer.local"
ingressCertIssuer: "selfsigned"
```

### Staging

Staging uses Let's Encrypt staging server for testing:

```yaml
# values-staging.yaml
ingressEnabled: true
installIngress: true
installCerts: true
ingressHost: "staging.ai-part-designer.assemblematic.ai"
ingressCertIssuer: "letsencrypt-staging"
```

**DNS Records:**
```
A       staging.ai-part-designer.assemblematic.ai      203.0.113.51
```

**Note:** Let's Encrypt staging certificates are not trusted by browsers. This is intentional for testing without hitting rate limits.

### Production

Production uses Let's Encrypt production server:

```yaml
# values-production.yaml
ingressEnabled: true
installIngress: true
installCerts: true
ingressMultiDomain: true
ingressFrontendHost: "app.ai-part-designer.com"
ingressBackendHost: "api.ai-part-designer.com"
ingressCertIssuer: "letsencrypt-prod"
```

**DNS Records:**
```
A       app.ai-part-designer.com      203.0.113.52
A       api.ai-part-designer.com      203.0.113.52
```

## Cloud Provider Specific Notes

### AWS (EKS)

For AWS Load Balancer, you'll get a hostname instead of IP:

```bash
kubectl get svc -n ai-part-designer -l app.kubernetes.io/name=ingress-nginx
# EXTERNAL-IP: a1b2c3d4e5f6.us-west-2.elb.amazonaws.com
```

Use CNAME records:
```
CNAME   app.assemblematic.ai      a1b2c3d4e5f6.us-west-2.elb.amazonaws.com
CNAME   api.assemblematic.ai      a1b2c3d4e5f6.us-west-2.elb.amazonaws.com
```

### GCP (GKE)

GKE provides an external IP. Use A records as shown above.

### Azure (AKS)

AKS provides an external IP. Use A records as shown above.

### Self-Hosted / Bare Metal

For on-premise deployments:

1. Use NodePort service type:
```yaml
ingress-nginx:
  controller:
    service:
      type: NodePort
```

2. Configure external load balancer (HAProxy, MetalLB, etc.) to forward to node IPs
3. Create DNS A records pointing to load balancer IP

## Troubleshooting

### Certificate Not Issuing

Check cert-manager Certificate resource:
```bash
kubectl describe certificate ai-part-designer-tls -n ai-part-designer
```

Common issues:
- DNS not propagated yet (wait 5-60 minutes)
- Firewall blocking port 80 (needed for HTTP-01 challenge)
- ClusterIssuer not created (check with `kubectl get clusterissuer`)

### 404 Not Found

Check Ingress is created and has correct service names:
```bash
kubectl get ingress -n ai-part-designer
kubectl describe ingress ai-part-designer -n ai-part-designer
```

Check backend services are running:
```bash
kubectl get svc -n ai-part-designer
kubectl get endpoints -n ai-part-designer
```

### CORS Errors

Update backend CORS configuration to include your domain:

```yaml
# In backend configmap or environment
corsOrigins: '["https://app.assemblematic.ai"]'
```

For multi-domain setup:
```yaml
corsOrigins: '["https://app.assemblematic.ai", "https://api.assemblematic.ai"]'
```

### Rate Limiting Too Strict

Adjust rate limits in Helm values:

```yaml
ingressRateLimitRps: "200"           # Requests per second
ingressRateLimitConnections: "100"   # Concurrent connections
ingressRateLimitBurst: "10"          # Burst multiplier
```

## Security Recommendations

1. **Always use HTTPS in production** - The ingress configuration enforces HTTPS redirects
2. **Use Let's Encrypt production** - Only use staging for testing
3. **Configure appropriate rate limits** - Protect against abuse
4. **Enable HSTS** - Already configured with 1-year max age
5. **Review security headers** - Pre-configured in ingress annotations
6. **Restrict CORS origins** - Configure backend to only allow your domains

## Additional Resources

- [NGINX Ingress Controller Documentation](https://kubernetes.github.io/ingress-nginx/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [Let's Encrypt Rate Limits](https://letsencrypt.org/docs/rate-limits/)
- [DNS Propagation Checker](https://www.whatsmydns.net/)
