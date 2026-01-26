# ADR-009: Deployment Platform and Infrastructure

## Status
Proposed

## Context
We need to select a deployment platform and define our infrastructure architecture. Requirements:
- Containerized deployments for consistency
- Auto-scaling for varying load
- Managed database and Redis options
- Cost-effective for startup phase
- Room to grow with demand
- CI/CD integration
- Monitoring and logging
- Multi-region capability for future

## Decision
We will deploy on **AWS** using a containerized architecture with **ECS Fargate** for initial deployment, with a path to EKS (Kubernetes) as we scale.

Infrastructure choices:
- **Compute**: ECS Fargate (containers without managing servers)
- **Database**: RDS PostgreSQL (managed)
- **Cache/Queue**: ElastiCache Redis
- **Storage**: S3 + CloudFront (per ADR-008)
- **Load Balancer**: Application Load Balancer (ALB)
- **DNS**: Route 53
- **Secrets**: AWS Secrets Manager
- **IaC**: Terraform

## Consequences

### Positive
- **Managed services**: Less operational overhead for DB, Redis
- **Fargate**: No EC2 instances to manage
- **Auto-scaling**: Built-in scaling for ECS services
- **AWS ecosystem**: Tight integration between services
- **Cost control**: Pay for what you use with Fargate

### Negative
- **Vendor lock-in**: Deep integration with AWS services
- **Fargate cold starts**: 30-60 second startup time (mitigated by min capacity)
- **Learning curve**: AWS-specific concepts and IAM

### Future Path
- Migrate to EKS when Kubernetes benefits outweigh complexity
- Add multi-region deployment for DR/latency
- Consider spot instances for workers

## Options Considered

| Option | Pros | Cons | Score |
|--------|------|------|-------|
| **AWS ECS Fargate** | Managed, scalable, AWS integration | Vendor lock-in | ⭐⭐⭐⭐⭐ |
| AWS EKS | Kubernetes, portable | More complex | ⭐⭐⭐⭐ |
| GCP Cloud Run | Simple, fast scaling | Less ecosystem | ⭐⭐⭐⭐ |
| DigitalOcean App Platform | Simple, affordable | Less scale/features | ⭐⭐⭐ |
| Self-hosted K8s | Full control | Operational burden | ⭐⭐ |

## Technical Details

### Architecture Diagram
```
                              ┌─────────────────────────────┐
                              │        Route 53             │
                              │    aipartdesigner.com       │
                              └──────────────┬──────────────┘
                                             │
                              ┌──────────────▼──────────────┐
                              │       CloudFront CDN        │
                              │   (Static assets, files)    │
                              └──────────────┬──────────────┘
                                             │
                              ┌──────────────▼──────────────┐
                              │   Application Load Balancer │
                              │        (HTTPS only)         │
                              └──────────────┬──────────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
         ┌──────────▼──────────┐  ┌──────────▼──────────┐  ┌──────────▼──────────┐
         │   ECS Fargate       │  │   ECS Fargate       │  │   ECS Fargate       │
         │   Frontend          │  │   Backend API       │  │   Workers           │
         │   (React + Nginx)   │  │   (FastAPI)         │  │   (Celery)          │
         │   Min: 2, Max: 10   │  │   Min: 2, Max: 20   │  │   Min: 2, Max: 20   │
         └─────────────────────┘  └──────────┬──────────┘  └──────────┬──────────┘
                                             │                        │
                    ┌────────────────────────┼────────────────────────┤
                    │                        │                        │
         ┌──────────▼──────────┐  ┌──────────▼──────────┐  ┌──────────▼──────────┐
         │   RDS PostgreSQL    │  │   ElastiCache       │  │   S3 Bucket         │
         │   db.t3.medium      │  │   Redis Cluster     │  │   File Storage      │
         │   Multi-AZ          │  │   cache.t3.medium   │  │                     │
         └─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

### VPC Layout
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            VPC (10.0.0.0/16)                                │
│  ┌───────────────────────────────┐  ┌───────────────────────────────┐      │
│  │   Public Subnet A (10.0.1.0/24)│  │   Public Subnet B (10.0.2.0/24)│      │
│  │   - NAT Gateway               │  │   - NAT Gateway               │      │
│  │   - ALB                       │  │   - ALB                       │      │
│  └───────────────────────────────┘  └───────────────────────────────┘      │
│  ┌───────────────────────────────┐  ┌───────────────────────────────┐      │
│  │   Private Subnet A (10.0.3.0/24│  │   Private Subnet B (10.0.4.0/24│      │
│  │   - ECS Tasks                 │  │   - ECS Tasks                 │      │
│  │   - RDS Primary               │  │   - RDS Standby               │      │
│  │   - ElastiCache               │  │   - ElastiCache               │      │
│  └───────────────────────────────┘  └───────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Terraform Structure
```
infrastructure/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   └── production/
├── modules/
│   ├── vpc/
│   ├── ecs/
│   ├── rds/
│   ├── elasticache/
│   ├── s3/
│   └── alb/
└── shared/
    └── ecr/
```

### ECS Task Definition
```hcl
# modules/ecs/api.tf
resource "aws_ecs_task_definition" "api" {
  family                   = "ai-part-designer-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "api"
      image = "${aws_ecr_repository.api.repository_url}:${var.image_tag}"
      
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]
      
      environment = [
        { name = "ENVIRONMENT", value = var.environment },
        { name = "DATABASE_HOST", value = aws_db_instance.main.address },
        { name = "REDIS_HOST", value = aws_elasticache_cluster.main.cache_nodes[0].address },
      ]
      
      secrets = [
        { name = "DATABASE_PASSWORD", valueFrom = aws_secretsmanager_secret.db_password.arn },
        { name = "SECRET_KEY", valueFrom = aws_secretsmanager_secret.app_secret.arn },
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.api.name
          awslogs-region        = var.region
          awslogs-stream-prefix = "api"
        }
      }
      
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_service" "api" {
  name            = "api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_min_capacity
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }
}

resource "aws_appautoscaling_target" "api" {
  max_capacity       = var.api_max_capacity
  min_capacity       = var.api_min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "api-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
```

### GitHub Actions CI/CD
```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        default: 'staging'
        type: choice
        options: [staging, production]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: ai-part-designer

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    outputs:
      image_tag: ${{ steps.build.outputs.image_tag }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Build and push API image
        id: build
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY-api:$IMAGE_TAG -f backend/Dockerfile backend/
          docker push $ECR_REGISTRY/$ECR_REPOSITORY-api:$IMAGE_TAG
          echo "image_tag=$IMAGE_TAG" >> $GITHUB_OUTPUT

  deploy-staging:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.event.inputs.environment == 'staging'
    environment: staging
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster ai-part-designer-staging \
            --service api \
            --force-new-deployment

  deploy-production:
    needs: [build-and-push, deploy-staging]
    runs-on: ubuntu-latest
    if: github.event.inputs.environment == 'production'
    environment: production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster ai-part-designer-production \
            --service api \
            --force-new-deployment
```

### Cost Estimation (MVP Scale)

| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| ECS Fargate (API) | 2 tasks, 0.5 vCPU, 1GB | ~$30 |
| ECS Fargate (Workers) | 2 tasks, 1 vCPU, 2GB | ~$60 |
| ECS Fargate (Frontend) | 2 tasks, 0.25 vCPU, 0.5GB | ~$15 |
| RDS PostgreSQL | db.t3.medium, Multi-AZ | ~$70 |
| ElastiCache Redis | cache.t3.medium | ~$50 |
| ALB | Standard usage | ~$20 |
| S3 + CloudFront | 100GB storage, 100GB transfer | ~$30 |
| NAT Gateway | 2 AZs | ~$65 |
| Route 53 | 1 hosted zone | ~$1 |
| Secrets Manager | 5 secrets | ~$2 |
| **Total** | | **~$343/month** |

## Environment Strategy

| Environment | Purpose | Scale |
|-------------|---------|-------|
| Development | Local + shared dev resources | Minimal |
| Staging | Pre-production testing | 50% of production |
| Production | Live users | Full scale |

## References
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
