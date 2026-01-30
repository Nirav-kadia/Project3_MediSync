# MediSync Infrastructure Deployment

This directory contains Pulumi infrastructure-as-code for deploying MediSync to AWS ECS Fargate.

## Architecture

- **ECS Fargate**: Serverless container orchestration
- **Application Load Balancer**: HTTP/HTTPS traffic distribution
- **ECR**: Docker image registry
- **CloudWatch**: Logging and monitoring
- **Neo4j AuraDB**: External managed graph database

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Pulumi Account** (free tier works)
3. **AWS CLI** configured
4. **Pulumi CLI** installed
5. **Docker** installed

## Setup Instructions

### 1. Install Pulumi

```bash
# Windows (PowerShell)
choco install pulumi

# Or download from: https://www.pulumi.com/docs/install/
```

### 2. Configure Pulumi

```bash
cd infra

# Login to Pulumi (creates free account if needed)
pulumi login

# Create a new stack (or select existing)
pulumi stack init dev

# Set AWS region
pulumi config set aws:region us-east-1
```

### 3. Set Secrets

```bash
# Set your secrets (these are encrypted)
pulumi config set --secret neo4j_password "your-neo4j-password"
pulumi config set --secret google_api_key "your-google-api-key"

# Optional: Override defaults
pulumi config set --secret neo4j_uri "neo4j+ssc://your-instance.databases.neo4j.io"
pulumi config set --secret neo4j_user "neo4j"
```

### 4. Deploy Infrastructure

```bash
# Preview changes
pulumi preview

# Deploy
pulumi up
```

This will create:
- ECR repository
- ECS cluster and service
- Application Load Balancer
- Security groups
- IAM roles
- CloudWatch log groups

### 5. Build and Push Docker Image

```bash
# Get ECR repository URL
ECR_REPO=$(pulumi stack output ecr_repo_url)

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_REPO

# Build image (from project root)
cd ..
docker build -t medisync .

# Tag and push
docker tag medisync:latest $ECR_REPO:latest
docker push $ECR_REPO:latest
```

### 6. Force Service Update

```bash
cd infra

# Get cluster and service names
CLUSTER=$(pulumi stack output cluster_name)
SERVICE=$(pulumi stack output service_name)

# Force new deployment
aws ecs update-service \
  --cluster $CLUSTER \
  --service $SERVICE \
  --force-new-deployment \
  --region us-east-1
```

### 7. Access Your Application

```bash
# Get the ALB URL
pulumi stack output alb_url
```

Visit the URL in your browser!

## GitHub Actions CI/CD

To enable automatic deployments:

### 1. Set GitHub Secrets

Go to your repository Settings → Secrets and variables → Actions, and add:

- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `PULUMI_ACCESS_TOKEN`: From https://app.pulumi.com/account/tokens

### 2. Push to Main Branch

```bash
git add .
git commit -m "Deploy infrastructure"
git push origin main
```

The GitHub Action will automatically:
1. Build Docker image
2. Push to ECR
3. Deploy infrastructure with Pulumi
4. Update ECS service

## Monitoring

### View Logs

```bash
# Get log group name
LOG_GROUP=$(pulumi stack output log_group_name)

# Stream logs
aws logs tail $LOG_GROUP --follow --region us-east-1
```

### Check Service Status

```bash
CLUSTER=$(pulumi stack output cluster_name)
SERVICE=$(pulumi stack output service_name)

aws ecs describe-services \
  --cluster $CLUSTER \
  --services $SERVICE \
  --region us-east-1
```

## Costs

Estimated monthly costs (us-east-1):
- ECS Fargate (0.5 vCPU, 1GB RAM): ~$15/month
- Application Load Balancer: ~$16/month
- Data transfer: Variable
- **Total: ~$31/month** (excluding Neo4j AuraDB)

## Cleanup

To destroy all resources:

```bash
cd infra
pulumi destroy
```

## Troubleshooting

### Service won't start

Check logs:
```bash
aws logs tail /ecs/medisync --follow --region us-east-1
```

### Health checks failing

- Ensure container port (5001) matches target group port
- Check security group allows ALB → ECS traffic
- Verify application starts successfully

### Can't connect to Neo4j

- Verify Neo4j AuraDB credentials in Pulumi config
- Check Neo4j instance is running
- Ensure IP whitelist includes AWS region IPs

## Configuration Reference

| Config Key | Required | Default | Description |
|------------|----------|---------|-------------|
| `neo4j_uri` | No | From .env | Neo4j connection URI |
| `neo4j_user` | No | `neo4j` | Neo4j username |
| `neo4j_password` | Yes | - | Neo4j password |
| `google_api_key` | Yes | - | Google Gemini API key |

## Support

For issues:
1. Check CloudWatch logs
2. Verify Pulumi config: `pulumi config`
3. Check ECS service events in AWS Console
