"""
MediSync Infrastructure - AWS ECS Fargate Deployment
Deploys FastHTML application with Neo4j AuraDB connection
"""
import pulumi
import pulumi_aws as aws
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Configuration
config = pulumi.Config()
app_name = "medisync"
container_port = 5001  # FastHTML default port

# Get all secrets from .env file
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
google_api_key = os.getenv("GOOGLE_API_KEY")

# Validate required secrets
if not neo4j_uri:
    raise Exception("NEO4J_URI not found in .env file")
if not neo4j_user:
    raise Exception("NEO4J_USER not found in .env file")
if not neo4j_password:
    raise Exception("NEO4J_PASSWORD not found in .env file")
if not google_api_key:
    raise Exception("GOOGLE_API_KEY not found in .env file")

print("Loaded configuration from .env file")
print(f"   NEO4J_URI: {neo4j_uri}")
print(f"   NEO4J_USER: {neo4j_user}")
print(f"   GOOGLE_API_KEY: {'*' * 20}")
print(f"   NEO4J_PASSWORD: {'*' * 20}")

# ============================================================================
# STEP 1: Create ECR Repository
# ============================================================================
ecr_repo = aws.ecr.Repository(
    f"{app_name}-ecr",
    name=app_name,
    force_delete=True,
    image_scanning_configuration={
        "scan_on_push": True
    },
    image_tag_mutability="MUTABLE"
)

# ECR Lifecycle Policy - Keep only last 5 images
lifecycle_policy = aws.ecr.LifecyclePolicy(
    f"{app_name}-lifecycle",
    repository=ecr_repo.name,
    policy=json.dumps({
        "rules": [{
            "rulePriority": 1,
            "description": "Keep last 5 images",
            "selection": {
                "tagStatus": "any",
                "countType": "imageCountMoreThan",
                "countNumber": 5
            },
            "action": {
                "type": "expire"
            }
        }]
    })
)

pulumi.export("ecr_repo_url", ecr_repo.repository_url)
pulumi.export("ecr_repo_name", ecr_repo.name)

# ============================================================================
# STEP 2: IAM Roles
# ============================================================================

# ECS Task Execution Role (for pulling images, writing logs)
task_exec_role = aws.iam.Role(
    f"{app_name}-task-exec-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    })
)

aws.iam.RolePolicyAttachment(
    f"{app_name}-task-exec-policy",
    role=task_exec_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
)

# ECS Task Role (for application permissions)
task_role = aws.iam.Role(
    f"{app_name}-task-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    })
)

# ============================================================================
# STEP 3: CloudWatch Logs
# ============================================================================
log_group = aws.cloudwatch.LogGroup(
    f"{app_name}-logs",
    name=f"/ecs/{app_name}",
    retention_in_days=7
)

# ============================================================================
# STEP 4: Networking
# ============================================================================

# Get default VPC
default_vpc = aws.ec2.get_vpc(default=True)

# Get public subnets
public_subnets = aws.ec2.get_subnets(
    filters=[{
        "name": "vpc-id",
        "values": [default_vpc.id]
    }, {
        "name": "map-public-ip-on-launch",
        "values": ["true"]
    }]
)

# ALB Security Group
alb_sg = aws.ec2.SecurityGroup(
    f"{app_name}-alb-sg",
    description="Security group for Application Load Balancer",
    vpc_id=default_vpc.id,
    ingress=[
        {
            "protocol": "tcp",
            "from_port": 80,
            "to_port": 80,
            "cidr_blocks": ["0.0.0.0/0"],
            "description": "HTTP from anywhere"
        },
        {
            "protocol": "tcp",
            "from_port": 443,
            "to_port": 443,
            "cidr_blocks": ["0.0.0.0/0"],
            "description": "HTTPS from anywhere"
        }
    ],
    egress=[{
        "protocol": "-1",
        "from_port": 0,
        "to_port": 0,
        "cidr_blocks": ["0.0.0.0/0"],
        "description": "All outbound"
    }],
    tags={"Name": f"{app_name}-alb-sg"}
)

# ECS Security Group
ecs_sg = aws.ec2.SecurityGroup(
    f"{app_name}-ecs-sg",
    description="Security group for ECS tasks",
    vpc_id=default_vpc.id,
    ingress=[{
        "protocol": "tcp",
        "from_port": container_port,
        "to_port": container_port,
        "security_groups": [alb_sg.id],
        "description": "Allow traffic from ALB"
    }],
    egress=[{
        "protocol": "-1",
        "from_port": 0,
        "to_port": 0,
        "cidr_blocks": ["0.0.0.0/0"],
        "description": "All outbound"
    }],
    tags={"Name": f"{app_name}-ecs-sg"}
)

# ============================================================================
# STEP 5: Application Load Balancer
# ============================================================================
alb = aws.lb.LoadBalancer(
    f"{app_name}-alb",
    internal=False,
    load_balancer_type="application",
    security_groups=[alb_sg.id],
    subnets=public_subnets.ids,
    enable_deletion_protection=False,
    tags={"Name": f"{app_name}-alb"}
)

# Target Group
target_group = aws.lb.TargetGroup(
    f"{app_name}-tg",
    port=container_port,
    protocol="HTTP",
    vpc_id=default_vpc.id,
    target_type="ip",
    deregistration_delay=30,
    health_check={
        "enabled": True,
        "healthy_threshold": 2,
        "interval": 30,
        "matcher": "200",
        "path": "/",
        "port": "traffic-port",
        "protocol": "HTTP",
        "timeout": 10,
        "unhealthy_threshold": 3
    },
    tags={"Name": f"{app_name}-tg"}
)

# HTTP Listener
listener = aws.lb.Listener(
    f"{app_name}-listener",
    load_balancer_arn=alb.arn,
    port=80,
    protocol="HTTP",
    default_actions=[{
        "type": "forward",
        "target_group_arn": target_group.arn
    }]
)

# ============================================================================
# STEP 6: ECS Cluster
# ============================================================================
cluster = aws.ecs.Cluster(
    f"{app_name}-cluster",
    name=f"{app_name}-cluster",
    settings=[{
        "name": "containerInsights",
        "value": "enabled"
    }]
)

# ============================================================================
# STEP 7: ECS Task Definition
# ============================================================================
task_definition = aws.ecs.TaskDefinition(
    f"{app_name}-task",
    family=app_name,
    cpu="512",
    memory="1024",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    execution_role_arn=task_exec_role.arn,
    task_role_arn=task_role.arn,
    container_definitions=pulumi.Output.all(
        ecr_repo.repository_url,
        log_group.name
    ).apply(lambda args: json.dumps([{
        "name": app_name,
        "image": f"{args[0]}:latest",
        "essential": True,
        "portMappings": [{
            "containerPort": container_port,
            "protocol": "tcp"
        }],
        "environment": [
            {"name": "NEO4J_URI", "value": neo4j_uri},
            {"name": "NEO4J_USER", "value": neo4j_user},
            {"name": "NEO4J_PASSWORD", "value": neo4j_password},
            {"name": "GOOGLE_API_KEY", "value": google_api_key},
            {"name": "PHOENIX_ENABLED", "value": "false"}
        ],
        "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
                "awslogs-group": args[1],
                "awslogs-region": aws.get_region().name,
                "awslogs-stream-prefix": "ecs"
            }
        },
        "healthCheck": {
            "command": ["CMD-SHELL", "curl -f http://localhost:5001/ || exit 1"],
            "interval": 30,
            "timeout": 5,
            "retries": 3,
            "startPeriod": 60
        }
    }]))
)

# ============================================================================
# STEP 8: ECS Service
# ============================================================================
service = aws.ecs.Service(
    f"{app_name}-service",
    name=f"{app_name}-service",
    cluster=cluster.id,
    task_definition=task_definition.arn,
    desired_count=1,
    launch_type="FARGATE",
    platform_version="LATEST",
    health_check_grace_period_seconds=60,
    network_configuration={
        "assign_public_ip": True,
        "subnets": public_subnets.ids,
        "security_groups": [ecs_sg.id]
    },
    load_balancers=[{
        "target_group_arn": target_group.arn,
        "container_name": app_name,
        "container_port": container_port
    }],
    deployment_maximum_percent=200,
    deployment_minimum_healthy_percent=100,
    opts=pulumi.ResourceOptions(depends_on=[listener])
)

# ============================================================================
# EXPORTS
# ============================================================================
pulumi.export("alb_url", pulumi.Output.concat("http://", alb.dns_name))
pulumi.export("alb_dns_name", alb.dns_name)
pulumi.export("cluster_name", cluster.name)
pulumi.export("service_name", service.name)
pulumi.export("target_group_arn", target_group.arn)
pulumi.export("log_group_name", log_group.name)
