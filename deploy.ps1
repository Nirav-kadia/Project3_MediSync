# MediSync Deployment Script for Windows
# This script builds and deploys MediSync to AWS ECS

param(
    [switch]$SkipBuild,
    [switch]$SkipPush,
    [string]$Region = "us-east-1"
)

Write-Host "🏥 MediSync Deployment Script" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Check prerequisites
Write-Host "`n📋 Checking prerequisites..." -ForegroundColor Yellow

$commands = @("docker", "aws", "pulumi")
foreach ($cmd in $commands) {
    if (!(Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "❌ $cmd is not installed or not in PATH" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ $cmd found" -ForegroundColor Green
}

# Navigate to infra directory
Set-Location infra

# Get ECR repository URL
Write-Host "`n🔍 Getting ECR repository URL..." -ForegroundColor Yellow
$ecrRepo = pulumi stack output ecr_repo_url -s dev 2>$null

if (!$ecrRepo) {
    Write-Host "❌ ECR repository not found. Deploy infrastructure first:" -ForegroundColor Red
    Write-Host "   cd infra" -ForegroundColor Yellow
    Write-Host "   pulumi up" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ ECR Repository: $ecrRepo" -ForegroundColor Green

# Login to ECR
Write-Host "`n🔐 Logging into ECR..." -ForegroundColor Yellow
$loginCmd = aws ecr get-login-password --region $Region
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to get ECR login password" -ForegroundColor Red
    exit 1
}

$loginCmd | docker login --username AWS --password-stdin $ecrRepo
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to login to ECR" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Logged into ECR" -ForegroundColor Green

# Build Docker image
if (!$SkipBuild) {
    Write-Host "`n🔨 Building Docker image..." -ForegroundColor Yellow
    Set-Location ..
    docker build -t medisync:latest .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker build failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Docker image built" -ForegroundColor Green
    Set-Location infra
} else {
    Write-Host "`n⏭️  Skipping Docker build" -ForegroundColor Yellow
}

# Tag and push image
if (!$SkipPush) {
    Write-Host "`n📤 Pushing image to ECR..." -ForegroundColor Yellow
    Set-Location ..
    
    docker tag medisync:latest "${ecrRepo}:latest"
    docker push "${ecrRepo}:latest"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to push image" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ Image pushed to ECR" -ForegroundColor Green
    Set-Location infra
} else {
    Write-Host "`n⏭️  Skipping image push" -ForegroundColor Yellow
}

# Force ECS service update
Write-Host "`n🔄 Updating ECS service..." -ForegroundColor Yellow

$clusterName = pulumi stack output cluster_name -s dev
$serviceName = pulumi stack output service_name -s dev

aws ecs update-service `
    --cluster $clusterName `
    --service $serviceName `
    --force-new-deployment `
    --region $Region `
    --no-cli-pager

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to update ECS service" -ForegroundColor Red
    exit 1
}

Write-Host "✅ ECS service update initiated" -ForegroundColor Green

# Get ALB URL
$albUrl = pulumi stack output alb_url -s dev

Write-Host "`n✅ Deployment complete!" -ForegroundColor Green
Write-Host "`n🌐 Application URL: $albUrl" -ForegroundColor Cyan
Write-Host "`n📊 Monitor deployment:" -ForegroundColor Yellow
Write-Host "   aws ecs describe-services --cluster $clusterName --services $serviceName --region $Region" -ForegroundColor Gray
Write-Host "`n📝 View logs:" -ForegroundColor Yellow
Write-Host "   aws logs tail /ecs/medisync --follow --region $Region" -ForegroundColor Gray

Set-Location ..
