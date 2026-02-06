# Example Ingress Configurations

This directory contains example Ingress configurations for exposing the application externally.

## Prerequisites

- Ingress controller installed (e.g., nginx-ingress, traefik)
- cert-manager for automatic TLS certificates (optional but recommended)

## Nginx Ingress Example

### Simple HTTP Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-part-designer
  namespace: ai-part-designer-prod
  annotations:
    kubernetes.io/ingress.class: nginx
spec:
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-prod
            port:
              number: 80
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-prod
            port:
              number: 8000
```

### HTTPS with cert-manager (Recommended)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-part-designer
  namespace: ai-part-designer-prod
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    # WebSocket support for backend
    nginx.ingress.kubernetes.io/websocket-services: backend-prod
spec:
  tls:
  - hosts:
    - app.example.com
    - api.example.com
    secretName: ai-part-designer-tls
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-prod
            port:
              number: 80
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-prod
            port:
              number: 8000
---
# cert-manager ClusterIssuer (if not already created)
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
    - http01:
        ingress:
          class: nginx
```

### Single Domain with Path-Based Routing

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-part-designer
  namespace: ai-part-designer-prod
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    # Rewrite /api requests to remove /api prefix
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  tls:
  - hosts:
    - app.example.com
    secretName: ai-part-designer-tls
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /api(/|$)(.*)
        pathType: ImplementationSpecific
        backend:
          service:
            name: backend-prod
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-prod
            port:
              number: 80
```

### With Rate Limiting

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-part-designer
  namespace: ai-part-designer-prod
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    # Rate limiting
    nginx.ingress.kubernetes.io/limit-rps: "10"
    nginx.ingress.kubernetes.io/limit-connections: "5"
spec:
  tls:
  - hosts:
    - app.example.com
    - api.example.com
    secretName: ai-part-designer-tls
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-prod
            port:
              number: 80
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-prod
            port:
              number: 8000
```

## Traefik Ingress Example

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-part-designer
  namespace: ai-part-designer-prod
  annotations:
    kubernetes.io/ingress.class: traefik
    cert-manager.io/cluster-issuer: letsencrypt-prod
    traefik.ingress.kubernetes.io/router.tls: "true"
spec:
  tls:
  - hosts:
    - app.example.com
    - api.example.com
    secretName: ai-part-designer-tls
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-prod
            port:
              number: 80
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-prod
            port:
              number: 8000
```

## AWS ALB Ingress Example

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-part-designer
  namespace: ai-part-designer-prod
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    # SSL
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account:certificate/xxx
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    # Health check
    alb.ingress.kubernetes.io/healthcheck-path: /api/v1/health
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: '30'
spec:
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-prod
            port:
              number: 80
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-prod
            port:
              number: 8000
```

## GKE Ingress with Google-managed SSL

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-part-designer
  namespace: ai-part-designer-prod
  annotations:
    kubernetes.io/ingress.class: gce
    kubernetes.io/ingress.global-static-ip-name: ai-part-designer-ip
    networking.gke.io/managed-certificates: ai-part-designer-cert
spec:
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /*
        pathType: ImplementationSpecific
        backend:
          service:
            name: frontend-prod
            port:
              number: 80
  - host: api.example.com
    http:
      paths:
      - path: /*
        pathType: ImplementationSpecific
        backend:
          service:
            name: backend-prod
            port:
              number: 8000
---
apiVersion: networking.gke.io/v1
kind: ManagedCertificate
metadata:
  name: ai-part-designer-cert
  namespace: ai-part-designer-prod
spec:
  domains:
    - app.example.com
    - api.example.com
```

## Adding to Kustomize Overlay

To include an Ingress in your overlay:

1. Create the Ingress file:
```bash
# k8s/overlays/production/ingress.yaml
```

2. Add to kustomization.yaml:
```yaml
# k8s/overlays/production/kustomization.yaml
resources:
- ../../base
- ingress.yaml  # Add this line
```

3. Apply:
```bash
kubectl apply -k k8s/overlays/production
```

## Testing Ingress

```bash
# Check ingress status
kubectl get ingress -n ai-part-designer-prod

# Describe ingress for details
kubectl describe ingress ai-part-designer -n ai-part-designer-prod

# Test with curl
curl -H "Host: app.example.com" http://<ingress-ip>
curl -H "Host: api.example.com" http://<ingress-ip>/api/v1/health

# Test HTTPS
curl https://app.example.com
curl https://api.example.com/api/v1/health
```

## Common Issues

### 1. Certificate Not Working

Check cert-manager logs:
```bash
kubectl logs -n cert-manager -l app=cert-manager
kubectl describe certificate ai-part-designer-tls -n ai-part-designer-prod
```

### 2. 404 Not Found

Check service endpoints:
```bash
kubectl get endpoints -n ai-part-designer-prod
kubectl describe service backend-prod -n ai-part-designer-prod
```

### 3. WebSocket Connection Failures

Ensure WebSocket annotations are set:
```yaml
annotations:
  nginx.ingress.kubernetes.io/websocket-services: backend-prod
```

### 4. CORS Issues

Update backend CORS_ORIGINS environment variable to include your domain:
```yaml
- name: CORS_ORIGINS
  value: '["https://app.example.com"]'
```
