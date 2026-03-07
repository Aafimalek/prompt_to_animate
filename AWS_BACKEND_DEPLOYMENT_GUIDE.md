# AWS Backend Deployment Runbook (Prompt-to-Animate)

This is a full, end-to-end production deployment guide for this repository's backend on AWS.

It is written for your current setup:
- Frontend already on Vercel
- Backend is Python FastAPI + RQ worker
- Redis queue/progress store
- MongoDB database
- S3 + CloudFront for video storage/delivery
- You want to keep using your existing IAM user (same one used for S3)

The backend in this repo requires two running services:
1. API service (`uvicorn backend.main:app --host 0.0.0.0 --port 8000`)
2. Worker service (`python -m backend.worker`)

If you only deploy API and skip worker, generation jobs will queue and never complete.

---

## 0) Final Architecture (What You Are Building)

1. Docker image in ECR.
2. ECS Fargate cluster with two services:
   - `pta-api` (public, behind ALB)
   - `pta-worker` (private, no ALB)
3. ElastiCache Redis (queue, rate limit, progress keys).
4. MongoDB Atlas (or your managed MongoDB).
5. Secrets Manager for all env vars.
6. ALB + ACM + Route53 for HTTPS API domain.
7. Vercel frontend points `NEXT_PUBLIC_API_URL` to your API domain.

---

## 1) Pre-Deployment Checklist

Collect and keep these values ready before you start:

```text
AWS_ACCOUNT_ID=
AWS_REGION=ap-south-1
APP_NAME=prompt-to-animate
ENV_NAME=prod
ECR_REPO=prompt-to-animate
IMAGE_TAG=prod-001
CLUSTER_NAME=pta-cluster
API_SERVICE_NAME=pta-api
WORKER_SERVICE_NAME=pta-worker
API_TASK_FAMILY=pta-api-task
WORKER_TASK_FAMILY=pta-worker-task
API_DOMAIN=api.yourdomain.com
VPC_ID=
PRIVATE_SUBNET_1=
PRIVATE_SUBNET_2=
PUBLIC_SUBNET_1=
PUBLIC_SUBNET_2=
ALB_SG_ID=
API_TASK_SG_ID=
WORKER_TASK_SG_ID=
REDIS_SG_ID=
TARGET_GROUP_ARN=
ALB_ARN=
ALB_LISTENER_HTTPS_ARN=
SECRET_ARN=
MONGODB_URI=
REDIS_URL=
S3_BUCKET_NAME=
CLOUDFRONT_DOMAIN=
CLOUDFRONT_KEY_PAIR_ID=
```

Tools needed locally:
1. `aws` CLI configured
2. Docker Desktop
3. PowerShell terminal

Verify tooling:

```powershell
aws --version
docker --version
aws sts get-caller-identity
```

---

## 2) IAM: Use Existing IAM User for Deployment

You can use your current IAM user for deployment and also for runtime AWS keys (as your code currently expects `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`).

### 2.1 Attach deployment permissions to IAM user

For fast setup (broad policies):
1. `AmazonEC2ContainerRegistryPowerUser`
2. `AmazonECS_FullAccess`
3. `ElasticLoadBalancingFullAccess`
4. `CloudWatchLogsFullAccess`
5. `SecretsManagerReadWrite`
6. `AmazonVPCFullAccess`
7. `IAMFullAccess` (or minimum pass-role policy if you want tighter permissions)

### 2.2 Runtime S3 permissions for same IAM user

Attach a least-privilege policy scoped to your S3 bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BucketList",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME"
    },
    {
      "Sid": "ObjectRWDelete",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
    }
  ]
}
```

Optional if using SSE-KMS on bucket:
- add `kms:Decrypt`, `kms:Encrypt`, `kms:GenerateDataKey` for your key.

---

## 3) Create ECS IAM Roles

You need two ECS roles:
1. Execution role (pull image + read secrets + write logs)
2. Task role (runtime AWS calls, optional now if you keep static IAM keys)

### 3.1 Create execution role

1. IAM -> Roles -> Create role.
2. Trusted entity: `Elastic Container Service` -> `Elastic Container Service Task`.
3. Role name: `ecsTaskExecutionRole-pta`.
4. Attach policy: `AmazonECSTaskExecutionRolePolicy`.
5. Add inline policy for Secrets Manager read:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:prompt-to-animate/prod*"
    }
  ]
}
```

### 3.2 Create task role

1. Create role same trust relationship as ECS Task.
2. Name: `ptaTaskRole`.
3. If you keep static IAM keys in env for now, role can be minimal.
4. Future hardening: move S3 access to this role and remove static IAM keys from secrets.

---

## 4) Put Backend Secrets into Secrets Manager

Create one JSON secret:
- Name: `prompt-to-animate/prod`
- Type: Other type of secret (plain JSON)

Use this template and fill with your real values:

```json
{
  "MONGODB_URI": "mongodb+srv://...",
  "MONGODB_DATABASE": "prompt_to_animate",
  "REDIS_URL": "rediss://default:<token>@<endpoint>:6379",
  "AWS_ACCESS_KEY_ID": "...",
  "AWS_SECRET_ACCESS_KEY": "...",
  "AWS_REGION": "ap-south-1",
  "S3_BUCKET_NAME": "...",
  "CLOUDFRONT_DOMAIN": "...",
  "CLOUDFRONT_KEY_PAIR_ID": "...",
  "CLOUDFRONT_PRIVATE_KEY_BASE64": "...",
  "GROQ_API_KEY": "...",
  "AZURE_OPENAI_API_KEY": "",
  "AZURE_OPENAI_ENDPOINT": "",
  "AZURE_OPENAI_DEPLOYMENT": "gpt-5.2-chat",
  "CEREBRAS_API_KEY": "",
  "CEREBRAS_BASE_URL": "https://api.cerebras.ai/v1",
  "CEREBRAS_MODEL": "qwen-3-235b-a22b-instruct-2507",
  "CLERK_ISSUER": "https://...",
  "CLERK_JWKS_URL": "https://.../.well-known/jwks.json",
  "CLERK_AUTHORIZED_PARTIES": "https://www.yourdomain.com,https://your-project.vercel.app",
  "CLERK_JWT_AUDIENCE": "",
  "CLERK_JWT_KEY": "",
  "CORS_ALLOWED_ORIGINS": "https://www.yourdomain.com,https://your-project.vercel.app",
  "CORS_ALLOW_ORIGIN_REGEX": "",
  "RATE_LIMIT_GENERATE_PER_MINUTE": "6",
  "RATE_LIMIT_STATUS_PER_MINUTE": "120",
  "JOB_OWNER_TTL_SECONDS": "3600",
  "MANIM_RENDER_TIMEOUT_SECONDS": "240",
  "MANIM_RENDER_TIMEOUT_MAX_SECONDS": "1800",
  "MANIM_RENDER_REPAIR_ATTEMPTS": "2",
  "MANIM_TEMP_DIR": "/tmp/prompt_to_animate_manim",
  "MANIM_VISUAL_QA_ENABLED": "false",
  "MANIM_VISUAL_QA_MODE": "balanced"
}
```

PowerShell command to convert CloudFront private key to base64:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("private_key.pem"))
```

Get secret ARN:

```powershell
aws secretsmanager describe-secret --secret-id prompt-to-animate/prod --query ARN --output text
```

---

## 5) Networking Setup

Use one VPC with:
1. 2 public subnets (ALB)
2. 2 private subnets (ECS + Redis)
3. NAT gateway for outbound internet from private subnets

Security groups:
1. `alb-sg`
   - inbound: 80/443 from `0.0.0.0/0`
   - outbound: all
2. `api-task-sg`
   - inbound: 8000 from `alb-sg`
   - outbound: all
3. `worker-task-sg`
   - inbound: none
   - outbound: all
4. `redis-sg`
   - inbound: 6379 from `api-task-sg` and `worker-task-sg`
   - outbound: all

MongoDB Atlas access:
1. Allow ECS egress IPs (or use peering/private endpoint).
2. Ensure `MONGODB_URI` user/password are correct.

---

## 6) Redis Setup (ElastiCache)

1. Create Redis (serverless preferred for simpler ops).
2. Place in same VPC/private subnets.
3. Attach `redis-sg`.
4. Enable TLS/auth.
5. Build `REDIS_URL`:

```text
rediss://default:<AUTH_TOKEN>@<REDIS_ENDPOINT>:6379
```

Use `REDIS_URL` only. This code supports it directly.

---

## 7) Create ECR Repo and Push Backend Image

From repo root (`d:\Degree\MachineLearning\prompt_to_animate`):

```powershell
$AWS_REGION="ap-south-1"
$ECR_REPO="prompt-to-animate"
$IMAGE_TAG="prod-001"
$AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws ecr describe-repositories --repository-names $ECR_REPO --region $AWS_REGION 2>$null
if ($LASTEXITCODE -ne 0) {
  aws ecr create-repository --repository-name $ECR_REPO --region $AWS_REGION | Out-Null
}

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build -t "${ECR_REPO}:${IMAGE_TAG}" .
docker tag "${ECR_REPO}:${IMAGE_TAG}" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"
```

Resulting image URI:

```text
<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/prompt-to-animate:prod-001
```

---

## 8) Create CloudWatch Log Groups

```powershell
aws logs create-log-group --log-group-name /ecs/prompt-to-animate/api --region ap-south-1 2>$null
aws logs create-log-group --log-group-name /ecs/prompt-to-animate/worker --region ap-south-1 2>$null
aws logs put-retention-policy --log-group-name /ecs/prompt-to-animate/api --retention-in-days 30 --region ap-south-1
aws logs put-retention-policy --log-group-name /ecs/prompt-to-animate/worker --retention-in-days 30 --region ap-south-1
```

---

## 9) Create ECS Cluster

```powershell
aws ecs create-cluster --cluster-name pta-cluster --region ap-south-1
```

---

## 10) Create Task Definitions (API and Worker)

Below are complete templates. Save as `taskdef-api.json` and `taskdef-worker.json`.

Use:
- `executionRoleArn` = ARN of `ecsTaskExecutionRole-pta`
- `taskRoleArn` = ARN of `ptaTaskRole`
- `image` = pushed ECR image
- `valueFrom` = Secrets Manager ARN with JSON key syntax

JSON key syntax in ECS secrets:

```text
arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:prompt-to-animate/prod-XXXX:KEY::
```

### 10.1 API task definition template

```json
{
  "family": "pta-api-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "ephemeralStorage": { "sizeInGiB": 30 },
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole-pta",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ptaTaskRole",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/prompt-to-animate:prod-001",
      "essential": true,
      "portMappings": [
        { "containerPort": 8000, "hostPort": 8000, "protocol": "tcp" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/prompt-to-animate/api",
          "awslogs-region": "ap-south-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 45
      },
      "secrets": [
        { "name": "MONGODB_URI", "valueFrom": "SECRET_ARN:MONGODB_URI::" },
        { "name": "MONGODB_DATABASE", "valueFrom": "SECRET_ARN:MONGODB_DATABASE::" },
        { "name": "REDIS_URL", "valueFrom": "SECRET_ARN:REDIS_URL::" },
        { "name": "AWS_ACCESS_KEY_ID", "valueFrom": "SECRET_ARN:AWS_ACCESS_KEY_ID::" },
        { "name": "AWS_SECRET_ACCESS_KEY", "valueFrom": "SECRET_ARN:AWS_SECRET_ACCESS_KEY::" },
        { "name": "AWS_REGION", "valueFrom": "SECRET_ARN:AWS_REGION::" },
        { "name": "S3_BUCKET_NAME", "valueFrom": "SECRET_ARN:S3_BUCKET_NAME::" },
        { "name": "CLOUDFRONT_DOMAIN", "valueFrom": "SECRET_ARN:CLOUDFRONT_DOMAIN::" },
        { "name": "CLOUDFRONT_KEY_PAIR_ID", "valueFrom": "SECRET_ARN:CLOUDFRONT_KEY_PAIR_ID::" },
        { "name": "CLOUDFRONT_PRIVATE_KEY_BASE64", "valueFrom": "SECRET_ARN:CLOUDFRONT_PRIVATE_KEY_BASE64::" },
        { "name": "GROQ_API_KEY", "valueFrom": "SECRET_ARN:GROQ_API_KEY::" },
        { "name": "AZURE_OPENAI_API_KEY", "valueFrom": "SECRET_ARN:AZURE_OPENAI_API_KEY::" },
        { "name": "AZURE_OPENAI_ENDPOINT", "valueFrom": "SECRET_ARN:AZURE_OPENAI_ENDPOINT::" },
        { "name": "AZURE_OPENAI_DEPLOYMENT", "valueFrom": "SECRET_ARN:AZURE_OPENAI_DEPLOYMENT::" },
        { "name": "CEREBRAS_API_KEY", "valueFrom": "SECRET_ARN:CEREBRAS_API_KEY::" },
        { "name": "CEREBRAS_BASE_URL", "valueFrom": "SECRET_ARN:CEREBRAS_BASE_URL::" },
        { "name": "CEREBRAS_MODEL", "valueFrom": "SECRET_ARN:CEREBRAS_MODEL::" },
        { "name": "CLERK_ISSUER", "valueFrom": "SECRET_ARN:CLERK_ISSUER::" },
        { "name": "CLERK_JWKS_URL", "valueFrom": "SECRET_ARN:CLERK_JWKS_URL::" },
        { "name": "CLERK_AUTHORIZED_PARTIES", "valueFrom": "SECRET_ARN:CLERK_AUTHORIZED_PARTIES::" },
        { "name": "CLERK_JWT_AUDIENCE", "valueFrom": "SECRET_ARN:CLERK_JWT_AUDIENCE::" },
        { "name": "CLERK_JWT_KEY", "valueFrom": "SECRET_ARN:CLERK_JWT_KEY::" },
        { "name": "CORS_ALLOWED_ORIGINS", "valueFrom": "SECRET_ARN:CORS_ALLOWED_ORIGINS::" },
        { "name": "CORS_ALLOW_ORIGIN_REGEX", "valueFrom": "SECRET_ARN:CORS_ALLOW_ORIGIN_REGEX::" },
        { "name": "RATE_LIMIT_GENERATE_PER_MINUTE", "valueFrom": "SECRET_ARN:RATE_LIMIT_GENERATE_PER_MINUTE::" },
        { "name": "RATE_LIMIT_STATUS_PER_MINUTE", "valueFrom": "SECRET_ARN:RATE_LIMIT_STATUS_PER_MINUTE::" },
        { "name": "JOB_OWNER_TTL_SECONDS", "valueFrom": "SECRET_ARN:JOB_OWNER_TTL_SECONDS::" },
        { "name": "MANIM_RENDER_TIMEOUT_SECONDS", "valueFrom": "SECRET_ARN:MANIM_RENDER_TIMEOUT_SECONDS::" },
        { "name": "MANIM_RENDER_TIMEOUT_MAX_SECONDS", "valueFrom": "SECRET_ARN:MANIM_RENDER_TIMEOUT_MAX_SECONDS::" },
        { "name": "MANIM_RENDER_REPAIR_ATTEMPTS", "valueFrom": "SECRET_ARN:MANIM_RENDER_REPAIR_ATTEMPTS::" },
        { "name": "MANIM_TEMP_DIR", "valueFrom": "SECRET_ARN:MANIM_TEMP_DIR::" },
        { "name": "MANIM_VISUAL_QA_ENABLED", "valueFrom": "SECRET_ARN:MANIM_VISUAL_QA_ENABLED::" },
        { "name": "MANIM_VISUAL_QA_MODE", "valueFrom": "SECRET_ARN:MANIM_VISUAL_QA_MODE::" }
      ]
    }
  ]
}
```

### 10.2 Worker task definition template

```json
{
  "family": "pta-worker-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "ephemeralStorage": { "sizeInGiB": 80 },
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole-pta",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ptaTaskRole",
  "containerDefinitions": [
    {
      "name": "worker",
      "image": "ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/prompt-to-animate:prod-001",
      "essential": true,
      "command": ["python", "-m", "backend.worker"],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/prompt-to-animate/worker",
          "awslogs-region": "ap-south-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "secrets": [
        { "name": "MONGODB_URI", "valueFrom": "SECRET_ARN:MONGODB_URI::" },
        { "name": "MONGODB_DATABASE", "valueFrom": "SECRET_ARN:MONGODB_DATABASE::" },
        { "name": "REDIS_URL", "valueFrom": "SECRET_ARN:REDIS_URL::" },
        { "name": "AWS_ACCESS_KEY_ID", "valueFrom": "SECRET_ARN:AWS_ACCESS_KEY_ID::" },
        { "name": "AWS_SECRET_ACCESS_KEY", "valueFrom": "SECRET_ARN:AWS_SECRET_ACCESS_KEY::" },
        { "name": "AWS_REGION", "valueFrom": "SECRET_ARN:AWS_REGION::" },
        { "name": "S3_BUCKET_NAME", "valueFrom": "SECRET_ARN:S3_BUCKET_NAME::" },
        { "name": "CLOUDFRONT_DOMAIN", "valueFrom": "SECRET_ARN:CLOUDFRONT_DOMAIN::" },
        { "name": "CLOUDFRONT_KEY_PAIR_ID", "valueFrom": "SECRET_ARN:CLOUDFRONT_KEY_PAIR_ID::" },
        { "name": "CLOUDFRONT_PRIVATE_KEY_BASE64", "valueFrom": "SECRET_ARN:CLOUDFRONT_PRIVATE_KEY_BASE64::" },
        { "name": "GROQ_API_KEY", "valueFrom": "SECRET_ARN:GROQ_API_KEY::" },
        { "name": "AZURE_OPENAI_API_KEY", "valueFrom": "SECRET_ARN:AZURE_OPENAI_API_KEY::" },
        { "name": "AZURE_OPENAI_ENDPOINT", "valueFrom": "SECRET_ARN:AZURE_OPENAI_ENDPOINT::" },
        { "name": "AZURE_OPENAI_DEPLOYMENT", "valueFrom": "SECRET_ARN:AZURE_OPENAI_DEPLOYMENT::" },
        { "name": "CEREBRAS_API_KEY", "valueFrom": "SECRET_ARN:CEREBRAS_API_KEY::" },
        { "name": "CEREBRAS_BASE_URL", "valueFrom": "SECRET_ARN:CEREBRAS_BASE_URL::" },
        { "name": "CEREBRAS_MODEL", "valueFrom": "SECRET_ARN:CEREBRAS_MODEL::" },
        { "name": "CLERK_ISSUER", "valueFrom": "SECRET_ARN:CLERK_ISSUER::" },
        { "name": "CLERK_JWKS_URL", "valueFrom": "SECRET_ARN:CLERK_JWKS_URL::" },
        { "name": "CLERK_AUTHORIZED_PARTIES", "valueFrom": "SECRET_ARN:CLERK_AUTHORIZED_PARTIES::" },
        { "name": "CLERK_JWT_AUDIENCE", "valueFrom": "SECRET_ARN:CLERK_JWT_AUDIENCE::" },
        { "name": "CLERK_JWT_KEY", "valueFrom": "SECRET_ARN:CLERK_JWT_KEY::" },
        { "name": "CORS_ALLOWED_ORIGINS", "valueFrom": "SECRET_ARN:CORS_ALLOWED_ORIGINS::" },
        { "name": "CORS_ALLOW_ORIGIN_REGEX", "valueFrom": "SECRET_ARN:CORS_ALLOW_ORIGIN_REGEX::" },
        { "name": "RATE_LIMIT_GENERATE_PER_MINUTE", "valueFrom": "SECRET_ARN:RATE_LIMIT_GENERATE_PER_MINUTE::" },
        { "name": "RATE_LIMIT_STATUS_PER_MINUTE", "valueFrom": "SECRET_ARN:RATE_LIMIT_STATUS_PER_MINUTE::" },
        { "name": "JOB_OWNER_TTL_SECONDS", "valueFrom": "SECRET_ARN:JOB_OWNER_TTL_SECONDS::" },
        { "name": "MANIM_RENDER_TIMEOUT_SECONDS", "valueFrom": "SECRET_ARN:MANIM_RENDER_TIMEOUT_SECONDS::" },
        { "name": "MANIM_RENDER_TIMEOUT_MAX_SECONDS", "valueFrom": "SECRET_ARN:MANIM_RENDER_TIMEOUT_MAX_SECONDS::" },
        { "name": "MANIM_RENDER_REPAIR_ATTEMPTS", "valueFrom": "SECRET_ARN:MANIM_RENDER_REPAIR_ATTEMPTS::" },
        { "name": "MANIM_TEMP_DIR", "valueFrom": "SECRET_ARN:MANIM_TEMP_DIR::" },
        { "name": "MANIM_VISUAL_QA_ENABLED", "valueFrom": "SECRET_ARN:MANIM_VISUAL_QA_ENABLED::" },
        { "name": "MANIM_VISUAL_QA_MODE", "valueFrom": "SECRET_ARN:MANIM_VISUAL_QA_MODE::" }
      ]
    }
  ]
}
```

Register both task definitions:

```powershell
aws ecs register-task-definition --cli-input-json file://taskdef-api.json --region ap-south-1
aws ecs register-task-definition --cli-input-json file://taskdef-worker.json --region ap-south-1
```

---

## 11) Create ALB + Target Group

1. Create ALB in public subnets using `alb-sg`.
2. Target group type: IP.
3. Target group port: 8000.
4. Health check path: `/health`.
5. Success codes: `200`.
6. Set ALB idle timeout to `300` seconds (SSE safety margin).

Create listeners:
1. HTTP 80 -> redirect to HTTPS 443.
2. HTTPS 443 -> forward to API target group.

---

## 12) Create ECS Services

### 12.1 API service (`pta-api`)

1. Cluster: `pta-cluster`
2. Launch type: Fargate
3. Task definition: latest `pta-api-task`
4. Desired tasks: `1`
5. Network:
   - private subnets
   - security group: `api-task-sg`
   - public IP: disabled
6. Load balancer:
   - ALB target group on container `api`, port `8000`
7. Deployment config:
   - minimum healthy percent 100
   - maximum percent 200

### 12.2 Worker service (`pta-worker`)

1. Cluster: `pta-cluster`
2. Launch type: Fargate
3. Task definition: latest `pta-worker-task`
4. Desired tasks: `1` (increase when queue grows)
5. Network:
   - private subnets
   - security group: `worker-task-sg`
   - public IP: disabled
6. No load balancer.

---

## 13) Configure HTTPS Domain

1. ACM: request certificate for `api.yourdomain.com` in same region as ALB.
2. Validate cert (DNS validation easiest).
3. Attach certificate to ALB 443 listener.
4. Route53 record:
   - Type `A` (Alias)
   - Name `api`
   - Alias target: your ALB

---

## 14) Update Vercel Frontend

In Vercel project environment variables set:

```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

Then redeploy Vercel project.

Also verify these backend secret values include your frontend domains:
1. `CORS_ALLOWED_ORIGINS`
2. `CLERK_AUTHORIZED_PARTIES`

Use both custom domain and `*.vercel.app` origin if applicable.

---

## 15) First Deployment Validation (Mandatory)

### 15.1 Health check

```bash
curl https://api.yourdomain.com/health
```

Expect JSON response with `status` at least `healthy` or `degraded`.

### 15.2 API logs and worker logs

Check CloudWatch:
1. `/ecs/prompt-to-animate/api`
2. `/ecs/prompt-to-animate/worker`

No startup exceptions should appear.

### 15.3 End-to-end generation test

1. Login on frontend.
2. Trigger one generation.
3. Confirm:
   - Worker picks up job
   - S3 object created under `videos/...`
   - Response returns CloudFront signed URL
   - Chat record appears in MongoDB

---

## 16) Day-2 Deployment (New Image Version)

Whenever code changes:

1. Build and push new tag.
2. Create new task definition revision (API + worker) with new image tag.
3. Update services to latest task revision.
4. Wait for deployment stability.

PowerShell helper:

```powershell
$AWS_REGION="ap-south-1"
$CLUSTER="pta-cluster"

aws ecs update-service --cluster $CLUSTER --service pta-api --force-new-deployment --region $AWS_REGION
aws ecs update-service --cluster $CLUSTER --service pta-worker --force-new-deployment --region $AWS_REGION
```

---

## 17) Rollback Procedure

If new deployment fails:

1. In ECS service, choose previous task definition revision.
2. Update service to that known-good revision.
3. Force new deployment.
4. Confirm ALB target health and worker logs recover.

Keep at least last 2 stable task definition revisions.

---

## 18) Autoscaling and Reliability

Minimum production baseline:
1. API desired count: `2`
2. Worker desired count: `1` to `N` based on demand
3. Enable ECS service autoscaling:
   - API: CPU target tracking
   - Worker: custom queue-depth metric from Redis length

CloudWatch alarms:
1. API 5xx spikes
2. ECS task restarts > threshold
3. Worker CPU/memory saturation
4. ALB unhealthy host count > 0

---

## 19) Common Failures and Fixes

1. `403` on protected endpoints:
   - Token claims mismatch (`CLERK_ISSUER`, `CLERK_AUTHORIZED_PARTIES`, `CLERK_JWT_AUDIENCE`).
2. CORS blocked in browser:
   - Missing exact frontend origin in `CORS_ALLOWED_ORIGINS`.
3. Jobs stay pending:
   - Worker service down or Redis not reachable.
4. `/health` degraded with Redis/Mongo errors:
   - Security groups, route tables, NAT, URI/token invalid.
5. Signed URL generation fails:
   - Invalid `CLOUDFRONT_KEY_PAIR_ID` or bad base64 private key.
6. No S3 upload:
   - IAM access key/secret invalid or insufficient S3 policy.
7. API works locally but not in ECS:
   - Secrets not mapped correctly in task definition.

---

## 20) Security Hardening After Go-Live

After stable launch:

1. Move from static IAM user keys to ECS task role for S3.
2. Narrow IAM user permissions to least privilege.
3. Rotate secrets on a schedule.
4. Add AWS WAF in front of ALB.
5. Restrict MongoDB network to private connectivity.

---

## 21) Final "Nothing Missed" Checklist

Before announcing production ready, confirm all are true:

1. API ECS service is healthy behind ALB.
2. Worker ECS service is healthy and consumes queue.
3. Redis reachable from both API and worker.
4. Mongo reachable from both API and worker.
5. S3 upload works from worker.
6. CloudFront signed URL generation works.
7. Clerk auth works from Vercel frontend.
8. CORS allows all required frontend origins.
9. `NEXT_PUBLIC_API_URL` points to API domain.
10. Logs visible in CloudWatch.
11. Deployment/rollback tested at least once.

