# MediSync - Quick Start Guide

## Prerequisites Checklist

- [ ] AWS Account with admin access
- [ ] AWS CLI installed and configured
- [ ] Pulumi CLI installed
- [ ] Docker installed
- [ ] Git installed
- [ ] .env file with credentials (already exists ✅)

## 5-Minute Setup

### 1. Install Pulumi (if not installed)
```powershell
choco install pulumi
# OR download from: https://www.pulumi.com/docs/install/
```

### 2. Initialize Pulumi Stack
```powershell
cd infra
pulumi login
pulumi stack init dev
pulumi config set aws:region us-east-1
```

**Note:** No need to set secrets manually! The infrastructure reads from your `.env` file automatically.

### 3. Deploy Infrastructure
```powershell
pulumi up
# Review changes and confirm with 'yes'
```

### 4. Deploy Application
```powershell
cd ..
.\deploy.ps1
```

### 5. Access Application
```powershell
cd infra
pulumi stack output alb_url
# Open the URL in your browser
```

## What Changed?

✅ **Simplified Setup**: All credentials are read from your `.env` file
✅ **No Manual Secrets**: No need to run `pulumi config set --secret` commands
✅ **Automatic Loading**: Infrastructure automatically loads `.env` on deployment

## Common Commands

### View Application URL
```powershell
cd infra
pulumi stack output alb_url
```

### View Logs
```powershell
aws logs tail /ecs/medisync --follow
```

### Redeploy Application
```powershell
.\deploy.ps1
```

### Update Infrastructure
```powershell
cd infra
pulumi up
```

### Destroy Everything
```powershell
cd infra
pulumi destroy
```

## Troubleshooting

### "Environment variable not found"
Make sure your `.env` file exists in the project root with all required variables:
- `GOOGLE_API_KEY`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`

### "pulumi: command not found"
Install Pulumi: `choco install pulumi`

### "No stacks found"
Run: `pulumi stack init dev`

### "AWS credentials not found"
Run: `aws configure`

### Service won't start
Check logs: `aws logs tail /ecs/medisync --follow`

### Can't access application
Wait 2-3 minutes after deployment, then check ALB health checks in AWS Console

## GitHub Actions Setup

For automatic deployment on push to main:

1. Go to repository Settings → Secrets
2. Add these secrets (see `GITHUB_SECRETS_SETUP.md` for details):
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `PULUMI_ACCESS_TOKEN`
   - `GOOGLE_API_KEY`
   - `NEO4J_URI`
   - `NEO4J_USER`
   - `NEO4J_PASSWORD`
3. Push to main branch → automatic deployment!

## Cost

~$31/month for AWS resources (excluding Neo4j AuraDB)

## Support

- Full docs: `infra/README.md`
- Deployment guide: `DEPLOYMENT.md`
- GitHub secrets: `GITHUB_SECRETS_SETUP.md`
- Issues: Check CloudWatch logs first
