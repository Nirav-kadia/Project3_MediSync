# MediSync Deployment Guide

## What I've Created

Your Pulumi infrastructure has been updated and improved with:

### 1. Infrastructure Code (`infra/__main__.py`)
- ✅ ECR repository with lifecycle policies
- ✅ ECS Fargate cluster with Container Insights
- ✅ Application Load Balancer with health checks
- ✅ Proper security groups (ALB and ECS)
- ✅ IAM roles (execution and task roles)
- ✅ CloudWatch logging
- ✅ Secrets management via Pulumi config
- ✅ Improved resource naming and tagging

### 2. Docker Configuration
- `Dockerfile` - Production-ready container image
- `.dockerignore` - Optimized build context

### 3. CI/CD Pipeline
- `.github/workflows/deploy.yml` - Automated deployment on push to main

### 4. Deployment Scripts
- `deploy.ps1` - Windows PowerShell deployment script
- `infra/README.md` - Complete deployment documentation

## Key Improvements Over Your Original Code

1. **Security**: Secrets stored in Pulumi config (encrypted), not hardcoded
2. **Port Configuration**: Changed to 5001 (FastHTML default)
3. **Container Name**: Changed from "fastapi" to "medisync"
4. **Resource Sizing**: Increased to 512 CPU / 1024 MB memory
5. **Health Checks**: Added container health check
6. **Monitoring**: Enabled Container Insights
7. **Lifecycle**: Added ECR image cleanup policy
8. **Task Role**: Added separate task role for application permissions

## Quick Start

### Option 1: Manual Deployment

```powershell
# 1. Install Pulumi
choco install pulumi

# 2. Setup infrastructure
cd infra
pulumi login
pulumi stack init dev
pulumi config set aws:region us-east-1

# 3. Set secrets
pulumi config set --secret neo4j_password "n66M978Cm1zU-vdSdXCC7AGtwOw2gS1wn2UZAvHYNcI"
pulumi config set --secret google_api_key "AIzaSyBovrkeTtXOyMYlTOQoCn6RmjDH9DTiZQ8"

# 4. Deploy infrastructure
pulumi up

# 5. Build and deploy application
cd ..
.\deploy.ps1
```

### Option 2: GitHub Actions (Automated)

1. Set GitHub Secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `PULUMI_ACCESS_TOKEN`

2. Push to main branch - automatic deployment!

## What Happens During Deployment

1. **Infrastructure Creation** (first time only):
   - Creates ECR repository
   - Sets up ECS cluster
   - Configures load balancer
   - Creates security groups
   - Sets up IAM roles

2. **Application Deployment**:
   - Builds Docker image
   - Pushes to ECR
   - Updates ECS service
   - Performs rolling deployment

## Accessing Your Application

After deployment:

```powershell
cd infra
pulumi stack output alb_url
```

Visit the URL in your browser!

## Monitoring

### View Logs
```powershell
aws logs tail /ecs/medisync --follow --region us-east-1
```

### Check Service Status
```powershell
cd infra
$cluster = pulumi stack output cluster_name
$service = pulumi stack output service_name
aws ecs describe-services --cluster $cluster --services $service
```

## Cost Estimate

- ECS Fargate: ~$15/month
- Application Load Balancer: ~$16/month
- **Total: ~$31/month** (excluding Neo4j AuraDB)

## Troubleshooting

### Service won't start
```powershell
# Check logs
aws logs tail /ecs/medisync --follow

# Check service events
aws ecs describe-services --cluster medisync-cluster --services medisync-service
```

### Can't access application
- Wait 2-3 minutes for deployment to complete
- Check target group health in AWS Console
- Verify security groups allow traffic

### Image push fails
```powershell
# Re-login to ECR
$ecrRepo = pulumi stack output ecr_repo_url -s dev
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ecrRepo
```

## Next Steps

1. **Custom Domain**: Add Route53 and ACM certificate
2. **HTTPS**: Configure SSL/TLS on ALB
3. **Auto Scaling**: Add ECS auto-scaling policies
4. **Monitoring**: Set up CloudWatch alarms
5. **Backup**: Configure automated backups

## Cleanup

To destroy all resources:

```powershell
cd infra
pulumi destroy
```

## Support

- Pulumi Docs: https://www.pulumi.com/docs/
- AWS ECS Docs: https://docs.aws.amazon.com/ecs/
- Issues: Check CloudWatch logs first!
