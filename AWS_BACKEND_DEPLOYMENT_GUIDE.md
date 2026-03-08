# AWS Backend Deployment Guide (Beginner, End-to-End)

This guide deploys your backend with exactly this architecture:

1. Docker image in ECR
2. ECS Fargate cluster with 2 services
   - `pta-api` (public behind ALB)
   - `pta-worker` (private, no ALB)
3. Upstash Redis only (`REDIS_URL`)
4. MongoDB Atlas only (`MONGODB_URI`)
5. Secrets Manager for all env vars
6. ALB + ACM + DNS provider for HTTPS backend domain
   - In your deployment: DNS is managed in Vercel (not Route53)
7. Vercel frontend points to `NEXT_PUBLIC_API_URL=https://api.manimancer.fun`

This matches your current codebase:
- API command: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- Worker command: `python -m backend.worker`

Important:
- API and Worker are both required.
- If worker is not running, jobs will stay queued and generation will never finish.

---

## 0) AWS Services Explained (Quick Beginner Map)

Use this as a mental model before configuring anything.

1. ECR
   - What it is: AWS Docker registry.
   - Why you need it: ECS pulls your backend image from here.

2. ECS Fargate
   - What it is: Serverless container runtime.
   - Why you need it: Runs `pta-api` and `pta-worker` without managing EC2 servers.

3. ALB (Application Load Balancer)
   - What it is: Traffic router for HTTP/HTTPS.
   - Why you need it: Public entrypoint to API service.

4. ACM (AWS Certificate Manager)
   - What it is: SSL/TLS certificate manager.
   - Why you need it: HTTPS certificate for `https://api.manimancer.fun`.
   - Renewal: Automatic.

5. DNS provider (Vercel DNS in your current setup)
   - What it is: Authoritative DNS where your domain records are managed.
   - Why you need it: Maps `api.manimancer.fun` to your ALB and hosts ACM validation CNAME.

6. Secrets Manager
   - What it is: Secure storage for secrets/env vars.
   - Why you need it: Inject API keys, DB URLs, auth config into ECS tasks.

7. CloudWatch Logs
   - What it is: Central logs for AWS services.
   - Why you need it: Debug API and worker startup/runtime issues.

8. VPC + Subnets + NAT
   - What it is: Network boundaries and internet routing.
   - Why you need it: Keep ECS tasks private while still allowing outbound internet to Upstash/Atlas/LLM APIs.

---

## 1) What You Need Before Starting

1. AWS account with billing enabled.
2. Your domain `manimancer.fun` (DNS currently managed in Vercel for your setup).
3. Vercel frontend already working.
4. Upstash account and Redis database.
5. MongoDB Atlas project and cluster.
6. S3 bucket + CloudFront distribution already configured for video delivery.
7. Local machine with:
   - Docker Desktop
   - AWS CLI
   - PowerShell

Check local tools:

```powershell
aws --version
docker --version
aws sts get-caller-identity
```

---

## 2) Deployment Order (Do In This Order)

1. Collect all required keys/values.
2. Create Upstash Redis and copy `REDIS_URL`.
3. Create MongoDB Atlas DB user + network access and copy `MONGODB_URI`.
4. Create/verify IAM roles.
5. Put all secrets into Secrets Manager.
6. Create VPC networking + security groups.
7. Create ALB + target group.
8. Request ACM certificate (`api.manimancer.fun`).
9. Configure DNS records in your DNS provider (Vercel in your setup) and complete ACM validation.
10. Create ECR repo and push image.
11. Create ECS cluster.
12. Create ECS task definitions (API + Worker).
13. Create ECS services (API + Worker).
14. Update Vercel env var and redeploy.
15. Run smoke tests.

---

## 2.1) Start Here First (Do This Right Now)

If you are starting from zero, begin exactly here:

1. Open AWS Console and set region to `ap-south-1` (top-right region selector).
2. Open IAM and confirm you are logged in as user `<DEPLOYMENT_IAM_USER>`.
3. Complete Section `7.1` and `7.2` first (permissions and inline policy).
4. Complete Section `8.1` next (create Secrets Manager secret from exact JSON).
5. Then do networking in Section `9` and ALB in Section `10`.
6. Then do DNS + certificate in Sections `11` and `12`.
7. Then do image push and ECS Sections `13` to `19`.
8. End with Section `20` and Section `21`.

If you follow this order exactly, you will avoid most setup loops.

---

## 2.2) Zero-Confusion Execution Plan (First 60 Minutes)

Run this exact sequence:

1. Minute 0-10
   - Complete IAM user policies in `7.1`.
   - Complete IAM inline S3 policy in `7.2`.
2. Minute 10-20
   - Create ECS roles in `7.3` and `7.4`.
3. Minute 20-30
   - Create Secrets Manager secret in `8.1`.
   - Copy secret ARN (`8.2`).
4. Minute 30-45
   - Create VPC and security groups (`9.1` and `9.2`).
5. Minute 45-60
   - Create target group + ALB (`10.1`, `10.2`).
   - Request certificate (`11.1`) and then add DNS records for validation/routing (`12`).

After that, continue with ECR + ECS sections.

---

## 3) Collect Required Values (Fill This First)

Create a local notes file and fill these values (use placeholders first, then replace with your own real values):

```text
AWS_REGION=ap-south-1
AWS_ACCOUNT_ID=<AWS_ACCOUNT_ID>
APP_NAME=prompt-to-animate
ENV=prod

API_DOMAIN=api.yourdomain.com
FRONTEND_DOMAIN=https://yourdomain.com
FRONTEND_VERCEL_DOMAIN=https://yourproject.vercel.app

ECR_REPO=prompt-to-animate
IMAGE_TAG=prod-001
ECR_IMAGE_URI=<AWS_ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/prompt-to-animate:prod-001

CLUSTER_NAME=pta-cluster
API_TASK_FAMILY=pta-api-task
WORKER_TASK_FAMILY=pta-worker-task
API_SERVICE=pta-api
WORKER_SERVICE=pta-worker

VPC_ID=
PUBLIC_SUBNET_1=
PUBLIC_SUBNET_2=
PRIVATE_SUBNET_1=
PRIVATE_SUBNET_2=

ALB_SG_ID=
API_TASK_SG_ID=
WORKER_TASK_SG_ID=

ALB_ARN=
TARGET_GROUP_ARN=
LISTENER_HTTPS_ARN=

ACM_CERT_ARN=
SECRET_ARN=

UPSTASH_REDIS_URL=rediss://default:<password>@<host>:6379
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>/<db>
MONGODB_DATABASE=prompt_to_animate

S3_BUCKET_NAME=<S3_BUCKET_NAME>
CLOUDFRONT_DOMAIN=<CLOUDFRONT_DOMAIN>
CLOUDFRONT_KEY_PAIR_ID=<CLOUDFRONT_KEY_PAIR_ID>
CLOUDFRONT_PRIVATE_KEY_BASE64=<BASE64_ENCODED_PRIVATE_KEY>

AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY_ID>
AWS_SECRET_ACCESS_KEY=<AWS_SECRET_ACCESS_KEY>

GROQ_API_KEY=<GROQ_API_KEY>
AZURE_OPENAI_API_KEY=<AZURE_OPENAI_API_KEY>
AZURE_OPENAI_ENDPOINT=https://<resource>.cognitiveservices.azure.com/
AZURE_OPENAI_DEPLOYMENT=<AZURE_OPENAI_DEPLOYMENT>
CEREBRAS_API_KEY=<CEREBRAS_API_KEY>
GROQ_MODEL=<MODEL_NAME>
GROQ_FALLBACK_MODELS=<MODEL_1>,<MODEL_2>

CLERK_ISSUER=https://clerk.yourdomain.com
CLERK_JWKS_URL=https://clerk.yourdomain.com/.well-known/jwks.json
CLERK_AUTHORIZED_PARTIES=https://yourdomain.com,http://localhost:3000,https://*.vercel.app
CLERK_JWT_AUDIENCE=
CLERK_JWT_KEY=-----BEGIN PUBLIC KEY-----
...
-----END PUBLIC KEY-----

CORS_ALLOWED_ORIGINS=https://yourdomain.com,http://localhost:3000
CORS_ALLOW_ORIGIN_REGEX=^https://.*[.]vercel[.]app$

RATE_LIMIT_GENERATE_PER_MINUTE=6
RATE_LIMIT_STATUS_PER_MINUTE=120
JOB_OWNER_TTL_SECONDS=3600
```

Important safety rule:
1. Never paste real secret values into this guide.
2. Keep real values only in AWS Secrets Manager / Vercel env UI.
3. Never commit `.env` or private key files to GitHub.

---

## 4) Upstash Redis Setup (Required)

### 4.1 Create Redis database

1. Log in to Upstash dashboard.
2. Create database.
3. Choose region close to AWS region.
4. Open DB details.
5. Copy TLS connection string (`rediss://...`).

### 4.2 Save the exact URL

Set:

```text
UPSTASH_REDIS_URL=rediss://default:<password>@<host>:6379
```

Use this exact value as `REDIS_URL` in Secrets Manager.

---

## 5) MongoDB Atlas Setup (Required)

### 5.1 Create Atlas cluster

1. Log in to Atlas.
2. Create project.
3. Create cluster (M0/M10 based on needs).

### 5.2 Create DB user

1. Atlas -> Security -> Database Access.
2. Add new database user.
3. Save username/password securely.

### 5.3 Network access

Because ECS tasks run in private subnets and use NAT, Atlas sees NAT public IP.

1. Atlas -> Security -> Network Access.
2. Add IP access list entry for NAT Elastic IP.
3. Temporary setup option: `0.0.0.0/0` (not recommended long term).

### 5.4 Get connection string

1. Atlas -> Connect -> Drivers.
2. Copy URI.
3. Replace `<username>`, `<password>`, DB name.
4. Save as:

```text
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/prompt_to_animate?retryWrites=true&w=majority
MONGODB_DATABASE=prompt_to_animate
```

---

## 6) Prepare CloudFront Private Key for ECS

Your code supports `CLOUDFRONT_PRIVATE_KEY_BASE64` (best for ECS).

If you have `private_key.pem` locally:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("private_key.pem"))
```

Store output as:

```text
CLOUDFRONT_PRIVATE_KEY_BASE64=<very_long_base64_string>
```

---

## 7) IAM Setup

You said you want to use the same IAM user you already use for S3. That works.

### 7.1 IAM user permissions for deployment

Attach these managed policies to your deployment IAM user:

1. `AmazonEC2ContainerRegistryPowerUser`
2. `AmazonECS_FullAccess`
3. `ElasticLoadBalancingFullAccess`
4. `CloudWatchLogsFullAccess`
5. `SecretsManagerReadWrite`
6. `AmazonVPCFullAccess`
7. `IAMFullAccess` (or scoped `iam:PassRole` policy)
8. `AmazonRoute53FullAccess` (optional: only if you manage DNS in Route53)
9. `AWSCertificateManagerFullAccess`

If you see this error:
`The selected policies exceed this account's quota`

What it means:
1. IAM user has a limit on attached managed policies (typically 10).
2. Your user already has many attached policies, so adding more fails.

Fastest fix path (recommended for setup phase):
1. Detach some old/unused managed policies from your user.
2. Attach only `AdministratorAccess` temporarily (single policy).
3. Complete deployment.
4. Replace `AdministratorAccess` later with least-privilege policies.

Console steps for this fix:
1. IAM -> Users -> `<DEPLOYMENT_IAM_USER>` -> `Permissions`.
2. Under `Permissions policies`, sort by `Policy type = Managed`.
3. Select old policies you don't need right now.
4. Click `Remove`.
5. Click `Add permissions` -> `Attach policies directly`.
6. Select `AdministratorAccess`.
7. Click `Add permissions`.

Exact console steps:
1. AWS Console -> IAM -> Users.
2. Click user: `<DEPLOYMENT_IAM_USER>`.
3. Open `Permissions` tab.
4. Click `Add permissions` -> `Attach policies directly`.
5. Search and select each policy listed above.
6. Click `Add permissions`.
7. Refresh and confirm each policy appears under `Permissions policies`.

### 7.2 IAM user permissions for runtime S3 operations

Attach this inline policy (replace bucket name):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBucket",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::<S3_BUCKET_NAME>"
    },
    {
      "Sid": "ObjectReadWriteDelete",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::<S3_BUCKET_NAME>/*"
    }
  ]
}
```

Exact console steps to add this inline policy:
1. IAM -> Users -> `<DEPLOYMENT_IAM_USER>`.
2. `Permissions` tab -> `Add permissions`.
3. Click `Create inline policy`.
4. Switch to `JSON` tab.
5. Delete existing JSON and paste the policy JSON above.
6. Click `Next`.
7. Policy name: `manimancer-s3-runtime-inline`.
8. Click `Create policy`.
9. Confirm it appears under `Permissions policies`.

### 7.3 Create ECS execution role

1. IAM -> Roles -> Create role.
2. Trusted entity: AWS service.
3. Use case: `Elastic Container Service` -> `Elastic Container Service Task`.
4. Role name: `ecsTaskExecutionRole-pta`.
5. Attach policy: `AmazonECSTaskExecutionRolePolicy`.
6. Add inline policy for Secrets Manager read:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:ap-south-1:<AWS_ACCOUNT_ID>:secret:prompt-to-animate/prod*"
    }
  ]
}
```

Exact console steps:
1. IAM -> Roles -> `Create role`.
2. Trusted entity type: `AWS service`.
3. Use case: `Elastic Container Service` -> `Elastic Container Service Task`.
4. Click `Next`.
5. Attach policy `AmazonECSTaskExecutionRolePolicy`.
6. Role name: `ecsTaskExecutionRole-pta`.
7. Click `Create role`.
8. Open created role -> `Add permissions` -> `Create inline policy`.
9. Go to `JSON` tab -> paste the Secrets Manager policy above.
10. Click `Next`.
11. Inline policy name: `secrets-read-prompt-to-animate`.
12. Click `Create policy`.

### 7.4 Create ECS task role

1. Same trust relationship as above.
2. Role name: `ptaTaskRole`.
3. Keep minimal for now (runtime AWS calls currently use access key/secret from env).

Exact console steps:
1. IAM -> Roles -> `Create role`.
2. Trusted entity type: `AWS service`.
3. Use case: `Elastic Container Service` -> `Elastic Container Service Task`.
4. Click `Next` with no extra policies.
5. Role name: `ptaTaskRole`.
6. Click `Create role`.

### 7.5 Verify IAM is correctly configured (must do)

Use these checks before moving to networking:

1. IAM -> Users -> `<DEPLOYMENT_IAM_USER>` -> Permissions
   - Confirm all managed policies from `7.1` are attached.
   - Confirm inline policy `manimancer-s3-runtime-inline` exists.
2. IAM -> Roles
   - Confirm role `ecsTaskExecutionRole-pta` exists and has:
     - `AmazonECSTaskExecutionRolePolicy`
     - inline policy `secrets-read-prompt-to-animate`
   - Confirm role `ptaTaskRole` exists.
3. CLI verification:

```powershell
aws iam get-role --role-name ecsTaskExecutionRole-pta
aws iam get-role --role-name ptaTaskRole
```

If these commands fail, fix IAM before continuing.

---

## 8) Secrets Manager Setup

What this does:
1. Stores all backend env vars in one secure place.
2. ECS injects them into container environment at runtime.
3. You avoid hardcoding keys in task definitions.

### 8.1 Create one JSON secret

1. AWS Console -> Secrets Manager -> Store a new secret.
2. Secret type: `Other type of secrets`.
3. Enter key/value as JSON.
4. Secret name: `prompt-to-animate/prod`.

Exact console steps:
1. Click `Store a new secret`.
2. Under `Secret type`, choose `Other type of secret`.
3. Toggle to `Plaintext` (not key/value table).
4. Paste the JSON block below exactly.
5. Click `Next`.
6. Secret name: `prompt-to-animate/prod`.
7. Description: `Backend production env for prompt-to-animate` (optional).
8. Click `Next`.
9. Disable automatic rotation for now.
10. Click `Next` -> `Store`.

Use this template JSON (replace placeholders with your real values before saving in Secrets Manager):

```json
{
  "MONGODB_URI": "mongodb+srv://<user>:<password>@<cluster>/<db>",
  "MONGODB_DATABASE": "prompt_to_animate",
  "REDIS_URL": "rediss://default:<password>@<host>:6379",
  "AWS_ACCESS_KEY_ID": "<AWS_ACCESS_KEY_ID>",
  "AWS_SECRET_ACCESS_KEY": "<AWS_SECRET_ACCESS_KEY>",
  "AWS_REGION": "ap-south-1",
  "S3_BUCKET_NAME": "<S3_BUCKET_NAME>",
  "CLOUDFRONT_DOMAIN": "<CLOUDFRONT_DOMAIN>",
  "CLOUDFRONT_KEY_PAIR_ID": "<CLOUDFRONT_KEY_PAIR_ID>",
  "CLOUDFRONT_PRIVATE_KEY_BASE64": "<BASE64_ENCODED_PRIVATE_KEY>",
  "GROQ_API_KEY": "<GROQ_API_KEY>",
  "AZURE_OPENAI_API_KEY": "<AZURE_OPENAI_API_KEY>",
  "AZURE_OPENAI_ENDPOINT": "https://<resource>.cognitiveservices.azure.com/",
  "AZURE_OPENAI_DEPLOYMENT": "<AZURE_OPENAI_DEPLOYMENT>",
  "CEREBRAS_API_KEY": "<CEREBRAS_API_KEY>",
  "GROQ_MODEL": "<MODEL_NAME>",
  "GROQ_FALLBACK_MODELS": "<MODEL_1>,<MODEL_2>",
  "CLERK_ISSUER": "https://clerk.yourdomain.com",
  "CLERK_JWKS_URL": "https://clerk.yourdomain.com/.well-known/jwks.json",
  "CLERK_AUTHORIZED_PARTIES": "https://yourdomain.com,http://localhost:3000,https://*.vercel.app",
  "CLERK_JWT_AUDIENCE": "",
  "CLERK_JWT_KEY": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
  "CORS_ALLOWED_ORIGINS": "https://yourdomain.com,http://localhost:3000",
  "CORS_ALLOW_ORIGIN_REGEX": "^https://.*[.]vercel[.]app$",
  "RATE_LIMIT_GENERATE_PER_MINUTE": "6",
  "RATE_LIMIT_STATUS_PER_MINUTE": "120",
  "JOB_OWNER_TTL_SECONDS": "3600",
  "MANIM_VISUAL_QA_ENABLED": "false",
  "MANIM_VISUAL_QA_MODE": "balanced",
  "MANIM_VISUAL_QA_MAX_REPAIRS": "1",
  "MANIM_VISUAL_QA_LOG_ARTIFACTS": "false",
  "MANIM_RENDER_TIMEOUT_SECONDS": "180",
  "MANIM_RENDER_TIMEOUT_MAX_SECONDS": "3600",
  "MANIM_TEMP_DIR": "",
  "MANIM_TIMELINE_PACING_ENABLED": "true",
  "MANIM_PACING_TOLERANCE_SECONDS": "12",
  "MANIM_AUTO_TIMESCALE_ENABLED": "true",
  "MANIM_MULTI_CANDIDATE_ENABLED": "true",
  "MANIM_MULTI_CANDIDATE_COUNT": "3",
  "MANIM_MULTI_CANDIDATE_VISUAL_QA": "true",
  "MANIM_SCENE_MEMORY_ENABLED": "true",
  "MANIM_SCENE_MEMORY_TOP_K": "3",
  "MANIM_REWARD_WEIGHTS_PATH": "backend/benchmarks/reward_weights.json",
  "MANIM_VLM_CRITIC_ENABLED": "false",
  "MANIM_VLM_CRITIC_FRAME_COUNT": "1"
}
```


Notes:
1. At least one LLM provider must be configured.
2. If using Groq only, keep `GROQ_API_KEY` non-empty.
3. Keep `REDIS_URL` exactly from Upstash.

### 8.2 Copy secret ARN

```powershell
aws secretsmanager describe-secret --secret-id prompt-to-animate/prod --query ARN --output text
```

Save output as `SECRET_ARN`.

### 8.3 How ECS reads secret keys (important)

When creating task definitions in console:
1. In container section, go to `Environment variables`.
2. Choose `Add from Secrets Manager`.
3. Select secret: `prompt-to-animate/prod`.
4. Select key: example `MONGODB_URI`.
5. Set env var name exactly same: `MONGODB_URI`.
6. Repeat for every key.

If env var name and secret key name do not match expected backend names, app will fail.

### 8.4 Secret format pitfalls (read before saving)

1. Do not wrap whole JSON in extra quotes.
2. Keep valid JSON only (no trailing commas).
3. For `CLERK_JWT_KEY`, keep the `\\n` escaped newlines in JSON (do not convert to multiline PEM in this JSON block).
4. Do not include spaces around key names.
5. Keep `REDIS_URL` starting with `rediss://`.
6. After saving, reopen secret and verify every key exists.

Quick JSON validity check locally:

```powershell
@'
{
  "ok": "test"
}
'@ | python -m json.tool
```

---

## 9) VPC and Networking (AWS Console)

What this does:
1. Keeps backend containers private.
2. Exposes only ALB publicly.
3. Allows private tasks outbound internet via NAT.

### 9.1 Create VPC

Use VPC wizard:
1. VPC with public and private subnets.
2. 2 AZs.
3. 2 public subnets.
4. 2 private subnets.
5. 1 NAT gateway minimum.

Exact console steps:
1. AWS Console -> VPC -> `Create VPC`.
2. Select `VPC and more`.
3. Name tag auto-generation: `pta`.
4. IPv4 CIDR: keep default (`10.0.0.0/16`) unless you need custom.
5. Number of Availability Zones: `2`.
6. Number of public subnets: `2`.
7. Number of private subnets: `2`.
8. NAT gateways: `1 per AZ` (best) or `1` (cheaper).
9. VPC endpoints: `None` for first setup.
10. Click `Create VPC`.

Why NAT is required:
- Private ECS tasks must access Upstash, Atlas, ECR, and LLM APIs over internet.

Substep checklist after VPC wizard:
1. Route table for public subnets should have `0.0.0.0/0 -> Internet Gateway`.
2. Route table for private subnets should have `0.0.0.0/0 -> NAT Gateway`.
3. NAT gateway should be in a public subnet and have an Elastic IP.
4. Save NAT Elastic IP; Atlas allowlist uses this IP.

How to capture exact IDs (needed later):
1. VPC -> Your VPCs -> copy `VPC ID`.
2. VPC -> Subnets -> copy 2 public + 2 private subnet IDs.
3. VPC -> NAT Gateways -> copy `Elastic IP`.
4. Paste all into Section `3` value block.

### 9.2 Security groups

Create 3 security groups:

1. `alb-sg`
   - Inbound: HTTP 80 from `0.0.0.0/0`
   - Inbound: HTTPS 443 from `0.0.0.0/0`
   - Outbound: all

2. `api-task-sg`
   - Inbound: TCP 8000 from `alb-sg`
   - Outbound: all

3. `worker-task-sg`
   - Inbound: none
   - Outbound: all

Exact console steps:
1. VPC -> Security Groups -> `Create security group`.
2. Create `alb-sg` first in your new VPC.
3. Add inbound `HTTP 80` source `0.0.0.0/0`.
4. Add inbound `HTTPS 443` source `0.0.0.0/0`.
5. Keep outbound allow all.
6. Create `api-task-sg`.
7. Inbound rule: Custom TCP `8000`, source `alb-sg` (select security group source).
8. Keep outbound allow all.
9. Create `worker-task-sg`.
10. No inbound rules.
11. Keep outbound allow all.

---

## 10) Create ALB and Target Group

What this does:
1. Receives public HTTPS traffic.
2. Forwards traffic to private ECS API tasks.
3. Health checks API via `/health`.

### 10.1 Target group

1. EC2 Console -> Target Groups -> Create.
2. Target type: `IP`.
3. Protocol: HTTP.
4. Port: 8000.
5. VPC: your VPC.
6. Health check path: `/health`.
7. Health check protocol: HTTP.
8. Success code: `200`.
9. Name: `pta-api-tg`.

Exact console values:
1. Target type: `IP addresses`.
2. Protocol version: `HTTP1`.
3. Health check advanced settings -> Healthy threshold `2`, Unhealthy threshold `3`.
4. Success codes `200`.

Register targets:
1. Skip manual registration now.
2. ECS service will auto-register/de-register task IPs.

### 10.2 Application Load Balancer

1. EC2 Console -> Load Balancers -> Create ALB.
2. Scheme: Internet-facing.
3. IPv4.
4. Select public subnets.
5. Security group: `alb-sg`.
6. Listener: HTTP 80 initially.
7. Default action: forward to `pta-api-tg`.
8. Name: `pta-api-alb`.

Exact console values:
1. Scheme: `Internet-facing`.
2. IP address type: `IPv4`.
3. Security group: `alb-sg`.
4. Listener 80 action: forward to `pta-api-tg` for now.

After creation:
1. ALB attributes -> Edit idle timeout -> set `300` seconds (SSE stability).

Immediate validation:
1. EC2 -> Target Groups -> `pta-api-tg` should exist.
2. EC2 -> Load Balancers -> `pta-api-alb` should show `Active`.
3. Security group on ALB must be `alb-sg`.

---

## 11) Request ACM Certificate and Attach HTTPS

What this does:
1. Enables trusted HTTPS for your API domain.
2. Removes need for Certbot on servers.
3. Renews certificate automatically.

### 11.1 Request certificate

1. ACM Console (same region as ALB, e.g. `ap-south-1`).
2. Request public certificate.
3. Domain: `api.manimancer.fun`.
4. Validation: DNS.
5. Create.

Exact console steps:
1. ACM -> `Request`.
2. `Request a public certificate`.
3. Domain name: `api.manimancer.fun`.
4. Validation method: `DNS validation`.
5. Click `Request`.

### 11.2 Validate certificate

1. ACM gives CNAME record.
2. Add this CNAME in your DNS provider (Vercel DNS in your setup).
3. Wait until cert status is `Issued`.
4. If DNS is managed in Vercel, add record there. If DNS is managed elsewhere, add there.

If cert stays `Pending validation`:
1. Confirm CNAME name/value copied exactly.
2. Confirm record is in correct hosted zone.
3. Wait DNS propagation (can take a few minutes).

### 11.3 Add HTTPS listener

1. Open ALB -> Listeners.
2. Add HTTPS 443 listener.
3. Select issued ACM certificate.
4. Forward to `pta-api-tg`.
5. Optional: change HTTP 80 listener action to redirect to HTTPS 443.

Exact console steps:
1. EC2 -> Load Balancers -> select `pta-api-alb`.
2. `Listeners and rules` tab -> `Add listener`.
3. Protocol `HTTPS`, port `443`.
4. Select ACM certificate `api.manimancer.fun`.
5. Forward action -> choose `pta-api-tg`.
6. Save.
7. Edit HTTP:80 listener -> action `Redirect to HTTPS:443`.

---

## 12) DNS Setup (Vercel DNS in Your Current Deployment)

What DNS does:
1. Maps `api.manimancer.fun` to your ALB DNS name.
2. Hosts ACM validation CNAME so certificate can be issued.

For your current setup, **Route53 is not required** because DNS is already managed in Vercel.

### 12.1 Add records in Vercel DNS (current path)

In Vercel Project/Domain DNS settings, add:

1. API traffic record
   - Type: `CNAME`
   - Name: `api`
   - Value/Target: your ALB DNS name (example: `pta-api-alb-xxxx.ap-south-1.elb.amazonaws.com`)
2. ACM validation record
   - Type: `CNAME`
   - Name: from ACM exactly (starts with `_` and is long)
   - Value/Target: from ACM exactly (starts with `_`)

Important:
1. Copy ACM validation record exactly, no edits.
2. Keep only one active CNAME for `api`.
3. If ACM fails with CAA error, update CAA policy at DNS provider to allow Amazon CA issuance.

### 12.2 DNS verification commands

Check API domain resolution:

```powershell
nslookup api.manimancer.fun
```

Expected:
1. Domain resolves to ALB target.
2. Browser opens `https://api.manimancer.fun/health`.
3. ACM certificate status becomes `Issued`.

### 12.3 Optional Route53 path (only if you move DNS to AWS later)

Use Route53 only if you choose to migrate DNS management from Vercel/other provider to AWS.

---

## 13) ECR: Create Repository and Push Docker Image

What this does:
1. Builds your backend image from local code.
2. Pushes image to AWS registry.
3. ECS pulls this image to run API/worker tasks.

From repo root:

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

Set:

```text
ECR_IMAGE_URI=<AWS_ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/prompt-to-animate:prod-001
```

If docker build fails:
1. Confirm Docker Desktop is running.
2. Run command from repository root (where `Dockerfile` exists).
3. Re-run with clean image tag.

---

## 14) Create ECS Cluster

What this does:
1. Logical home for API and worker services.
2. Lets you deploy/update both services together.

### 14.0 Which AWS login to use (important)

Use your deployment IAM user (example: `<DEPLOYMENT_IAM_USER>`) for this section and all remaining sections.

Do not switch to root user for routine deployment work.

Quick terminal check before opening ECS console:

```powershell
aws sts get-caller-identity --query Arn --output text
```

Expected:

```text
arn:aws:iam::<AWS_ACCOUNT_ID>:user/<DEPLOYMENT_IAM_USER>
```

### 14.1 Pre-check required resources before creating cluster

Do these checks first so cluster creation does not block later:

1. Confirm ECR image exists:

```powershell
aws ecr describe-images --region ap-south-1 --repository-name prompt-to-animate --query "sort_by(imageDetails,& imagePushedAt)[-1].[imageTags[0],imagePushedAt]" --output table
```

2. Confirm ECS IAM roles exist:

```powershell
aws iam get-role --role-name ecsTaskExecutionRole-pta --query "Role.RoleName" --output text
aws iam get-role --role-name ptaTaskRole --query "Role.RoleName" --output text
```

3. If any role command fails, complete Sections `7.3` and `7.4` first.
4. Confirm region in console is `ap-south-1 (Mumbai)`.

### 14.2 Create cluster in AWS Console (click-by-click)

1. Open AWS Console.
2. In top-right region selector, choose `Asia Pacific (Mumbai) ap-south-1`.
3. Search `ECS` in global search and open `Elastic Container Service`.
4. Left menu -> `Clusters`.
5. Click `Create cluster`.
6. Cluster name: `pta-cluster`.
7. Infrastructure:
8. Select `AWS Fargate (serverless)`.
9. Keep EC2 capacity providers disabled/not selected.
10. Monitoring:
11. Enable `Container Insights` if the option is shown.
12. Service discovery:
13. Keep default/off for now.
14. Execute command:
15. Optional; keep disabled for first deployment.
16. Tags:
17. Optional; you can add `Project=prompt-to-animate`.
18. Click `Create`.

### 14.3 If you see a different/new ECS UI

Some accounts show a simplified create page:

1. Select `Networking only` or `Fargate` style cluster.
2. Name it `pta-cluster`.
3. Keep default VPC integration off at cluster level (you configure VPC per service later).
4. Create cluster.

### 14.4 Validation after cluster create

1. ECS -> Clusters -> open `pta-cluster`.
2. Check top status: `Active`.
3. Services tab should show `0` services right now.
4. Tasks tab should show `0` tasks right now.
5. Terminal verification:

```powershell
aws ecs list-clusters --region ap-south-1 --output text
```

Expected output contains:

```text
...cluster/pta-cluster
```

### 14.5 If cluster creation fails

1. Make sure you are not in a different AWS account.
2. Make sure region is `ap-south-1`.
3. Confirm IAM user has `AdministratorAccess` or equivalent ECS permissions.
4. Retry in an incognito/private browser tab if console cache is stale.

---

## 15) Create CloudWatch Log Groups

What this does:
1. Stores application logs for API and worker.
2. Gives first place to debug startup/runtime failures.

```powershell
aws logs create-log-group --log-group-name /ecs/prompt-to-animate/api --region ap-south-1 2>$null
aws logs create-log-group --log-group-name /ecs/prompt-to-animate/worker --region ap-south-1 2>$null
aws logs put-retention-policy --log-group-name /ecs/prompt-to-animate/api --retention-in-days 30 --region ap-south-1
aws logs put-retention-policy --log-group-name /ecs/prompt-to-animate/worker --retention-in-days 30 --region ap-south-1
```

---

## 16) Create API Task Definition (ECS Console)

What this does:
1. Defines how API container runs.
2. Defines CPU/memory/ports/logging/secrets for API.

1. ECS -> Task Definitions -> Create new task definition.
2. Launch type: Fargate.
3. Family: `pta-api-task`.
4. CPU/Memory: `1 vCPU` / `2 GB`.
5. Task role: `ptaTaskRole`.
6. Execution role: `ecsTaskExecutionRole-pta`.
7. Ephemeral storage: `30 GiB`.

Exact values to type on task definition page:
1. Task definition family: `pta-api-task`
2. Launch type compatibility: `AWS Fargate`
3. Operating system/Architecture: `Linux/X86_64`
4. CPU: `1 vCPU`
5. Memory: `2 GB`
6. Task role: `ptaTaskRole`
7. Task execution role: `ecsTaskExecutionRole-pta`
8. Ephemeral storage: `30 GiB`

Container section:
1. Container name: `api`.
2. Image URI: `ECR_IMAGE_URI`.
3. Essential: yes.
4. Port mapping: `8000`.
5. Command override: leave empty (Dockerfile already uses uvicorn).

Container advanced:
1. Essential container: enabled.
2. Read-only root filesystem: keep disabled (Manim writes temp data).
3. Linux parameters: default.

Health check command:

```text
CMD-SHELL,curl -f http://localhost:8000/health || exit 1
```

Logs:
1. Log driver: `awslogs`.
2. Group: `/ecs/prompt-to-animate/api`.
3. Stream prefix: `ecs`.

Exact log options:
1. awslogs-group: `/ecs/prompt-to-animate/api`
2. awslogs-region: `ap-south-1`
3. awslogs-stream-prefix: `ecs`

Secrets:
1. Add one secret per env var.
2. Source: `prompt-to-animate/prod`.
3. Secret key: select corresponding JSON key.
4. Env var name must exactly match key names used in backend.

Minimum secrets to map:
1. `MONGODB_URI`
2. `MONGODB_DATABASE`
3. `REDIS_URL`
4. `AWS_ACCESS_KEY_ID`
5. `AWS_SECRET_ACCESS_KEY`
6. `AWS_REGION`
7. `S3_BUCKET_NAME`
8. `CLOUDFRONT_DOMAIN`
9. `CLOUDFRONT_KEY_PAIR_ID`
10. `CLOUDFRONT_PRIVATE_KEY_BASE64`
11. `GROQ_API_KEY` (or Azure keys)
12. `CLERK_ISSUER`
13. `CLERK_JWKS_URL`
14. `CLERK_AUTHORIZED_PARTIES`
15. `CLERK_JWT_AUDIENCE`
16. `CLERK_JWT_KEY`
17. `CORS_ALLOWED_ORIGINS`
18. `CORS_ALLOW_ORIGIN_REGEX`
19. `RATE_LIMIT_GENERATE_PER_MINUTE`
20. `RATE_LIMIT_STATUS_PER_MINUTE`
21. `JOB_OWNER_TTL_SECONDS`
22. `GROQ_MODEL`
23. `GROQ_FALLBACK_MODELS`
24. `CEREBRAS_API_KEY`
25. `MANIM_RENDER_TIMEOUT_SECONDS`
26. `MANIM_RENDER_TIMEOUT_MAX_SECONDS`
27. `MANIM_RENDER_REPAIR_ATTEMPTS`
28. `MANIM_VISUAL_QA_ENABLED`
29. `MANIM_VISUAL_QA_MODE`
30. `MANIM_VISUAL_QA_MAX_REPAIRS`
31. `MANIM_VISUAL_QA_LOG_ARTIFACTS`
32. `MANIM_TIMELINE_PACING_ENABLED`
33. `MANIM_PACING_TOLERANCE_SECONDS`
34. `MANIM_AUTO_TIMESCALE_ENABLED`
35. `MANIM_MULTI_CANDIDATE_ENABLED`
36. `MANIM_MULTI_CANDIDATE_COUNT`
37. `MANIM_MULTI_CANDIDATE_VISUAL_QA`
38. `MANIM_SCENE_MEMORY_ENABLED`
39. `MANIM_SCENE_MEMORY_TOP_K`
40. `MANIM_REWARD_WEIGHTS_PATH`
41. `MANIM_VLM_CRITIC_ENABLED`
42. `MANIM_VLM_CRITIC_FRAME_COUNT`

Create task definition.

Post-create check:
1. Open task definition revision.
2. Confirm container port is `8000`.
3. Confirm log group is `/ecs/prompt-to-animate/api`.
4. Confirm all required secrets are present.
5. Confirm revision number incremented (ex: `pta-api-task:1`).

---

## 17) Create Worker Task Definition (ECS Console)

What this does:
1. Defines background worker process that consumes Redis queue.
2. Handles rendering/upload logic.

1. ECS -> Task Definitions -> Create new.
2. Launch type: Fargate.
3. Family: `pta-worker-task`.
4. CPU/Memory: start with `2 vCPU` / `4 GB` (increase if rendering heavy).
5. Task role: `ptaTaskRole`.
6. Execution role: `ecsTaskExecutionRole-pta`.
7. Ephemeral storage: `80 GiB`.

Exact values to type on task definition page:
1. Task definition family: `pta-worker-task`
2. Launch type compatibility: `AWS Fargate`
3. Operating system/Architecture: `Linux/X86_64`
4. CPU: `2 vCPU`
5. Memory: `4 GB`
6. Task role: `ptaTaskRole`
7. Task execution role: `ecsTaskExecutionRole-pta`
8. Ephemeral storage: `80 GiB`

Container section:
1. Name: `worker`.
2. Image: same `ECR_IMAGE_URI`.
3. Command override:

```text
python,-m,backend.worker
```

4. No port mapping required.
5. Log group: `/ecs/prompt-to-animate/worker`.

Exact log options:
1. awslogs-group: `/ecs/prompt-to-animate/worker`
2. awslogs-region: `ap-south-1`
3. awslogs-stream-prefix: `ecs`

Secrets:
1. Map the same secret keys as API task.
2. Keep API and worker env values identical.

Important:
1. If one secret is missing in worker but present in API, jobs can fail while health still looks okay.
2. Always copy same full secret mapping list from API task.

Create task definition.

Post-create check:
1. Command is exactly `python,-m,backend.worker`.
2. No port mapping.
3. Log group is `/ecs/prompt-to-animate/worker`.
4. Same secrets as API task.
5. Revision number exists (ex: `pta-worker-task:1`).

---

## 18) Create ECS API Service

What this does:
1. Runs API tasks continuously.
2. Registers task IPs into ALB target group.

1. ECS -> Cluster `pta-cluster` -> Services -> Create.
2. Launch type: Fargate.
3. Task definition: latest `pta-api-task`.
4. Service name: `pta-api`.
5. Desired tasks: `1`.

Exact console steps:
1. ECS -> Clusters -> `pta-cluster` -> `Services` -> `Create`.
2. Compute options: `Launch type`.
3. Launch type: `FARGATE`.
4. Task definition family: `pta-api-task`, latest revision.
5. Service name: `pta-api`.
6. Desired tasks: `1`.
7. Deployment type: `Rolling update`.
8. Minimum healthy percent: `100`.
9. Maximum percent: `200`.

Networking:
1. VPC: your VPC.
2. Subnets: private subnets only.
3. Security group: `api-task-sg`.
4. Assign public IP: disabled.

Load balancer:
1. Type: Application Load Balancer.
2. Existing ALB: `pta-api-alb`.
3. Container: `api`, port `8000`.
4. Target group: `pta-api-tg`.

Service health grace period:
1. Set health check grace period to `60` seconds (if UI shows option).
2. This prevents early false failures on startup.

Deploy:
1. Create service.
2. Wait for task to become healthy.
3. Open Target Group -> Targets -> confirm healthy status.

Verification:
1. ECS service events show successful deployment.
2. Target group health shows healthy target(s).
3. Task `Last status` is `RUNNING`.
4. No restart loop in service events.

---

## 19) Create ECS Worker Service

What this does:
1. Runs worker tasks continuously.
2. Processes queued generation jobs from Redis.

1. ECS -> Cluster `pta-cluster` -> Services -> Create.
2. Launch type: Fargate.
3. Task definition: latest `pta-worker-task`.
4. Service name: `pta-worker`.
5. Desired tasks: `1`.

Exact console steps:
1. ECS -> Clusters -> `pta-cluster` -> `Services` -> `Create`.
2. Launch type: `FARGATE`.
3. Task definition family: `pta-worker-task`, latest revision.
4. Service name: `pta-worker`.
5. Desired tasks: `1`.
6. Deployment type: `Rolling update`.
7. Minimum healthy percent: `100`.
8. Maximum percent: `200`.

Networking:
1. VPC: same VPC.
2. Subnets: private subnets.
3. Security group: `worker-task-sg`.
4. Public IP: disabled.

Load balancer:
1. None.

Create service and wait for running state.

Verification:
1. ECS service events show running tasks.
2. Worker logs show startup and Redis connection success.
3. Task `Last status` remains `RUNNING` for several minutes.

---

## 20) Update Vercel

What this does:
1. Frontend starts calling AWS backend URL.
2. Removes localhost API target in production.

In Vercel project settings -> Environment Variables:

```env
NEXT_PUBLIC_API_URL=https://api.manimancer.fun
```

Redeploy frontend.

Do not copy your local `frontend/.env.local` secrets into this guide or GitHub.
Keep those values only in Vercel Environment Variables.

Also verify backend secrets include:
1. `CORS_ALLOWED_ORIGINS` with your frontend domains.
2. `CLERK_AUTHORIZED_PARTIES` with your frontend domains.

Vercel click path:
1. Vercel Dashboard -> Project -> Settings -> Environment Variables.
2. Add `NEXT_PUBLIC_API_URL`.
3. Set value for Production (and Preview if needed).
4. Redeploy latest commit.

---

## 21) Smoke Tests (Do All)

Before testing, wait until all are true:
1. ACM cert status is `Issued`.
2. ALB listener 443 exists and forwards to `pta-api-tg`.
3. API ECS service has at least one healthy target in target group.
4. Worker ECS service has one `RUNNING` task.

### 21.1 Health endpoint

```bash
curl https://api.manimancer.fun/health
```

Expected:
- JSON response.
- Redis and Mongo show connected.

If this fails:
1. Check ALB security group allows 443 inbound.
2. Check API service task is running.
3. Check target group health.

### 21.2 API docs

Open:

```text
https://api.manimancer.fun/docs
```

If not loading, check ALB, service health, and security groups.

### 21.3 Full generation flow

1. Open frontend (Vercel).
2. Sign in.
3. Generate one video.
4. Verify:
   - API logs show request
   - Worker logs show dequeued/render/upload
   - New object appears in S3 under `videos/...`
   - Frontend gets CloudFront signed URL
   - MongoDB chat record is created

---

## 22) Routine Deployments (After First Time)

When code changes:

1. Build and push new image tag.
2. Create new task definition revision with new image URI.
3. Update API service to latest task revision.
4. Update Worker service to latest task revision.
5. Wait until both services are stable.

Quick force deploy command:

```powershell
$AWS_REGION="ap-south-1"
$CLUSTER="pta-cluster"
aws ecs update-service --cluster $CLUSTER --service pta-api --force-new-deployment --region $AWS_REGION
aws ecs update-service --cluster $CLUSTER --service pta-worker --force-new-deployment --region $AWS_REGION
```

---

## 23) Rollback (If New Deploy Fails)

1. ECS -> Service -> Deployments/Task definition revision.
2. Choose previous known-good revision.
3. Update service to that revision.
4. Repeat for API and Worker.
5. Verify health and logs.

---

## 24) Common Problems and Exact Fixes

1. `CORS` errors in browser
   - Fix `CORS_ALLOWED_ORIGINS` value in secret.
   - Include exact origin including protocol.

2. `403` auth errors
   - Fix Clerk envs: `CLERK_ISSUER`, `CLERK_JWKS_URL`, `CLERK_AUTHORIZED_PARTIES`, `CLERK_JWT_AUDIENCE`.
   - Ensure frontend sends Bearer token.

3. Jobs stuck pending
   - Worker service not running or cannot reach Upstash.
   - Check worker logs and `REDIS_URL`.

4. `/health` shows degraded
   - Redis/Mongo unreachable.
   - Check NAT, route tables, and Atlas allowlist.

5. No video uploaded to S3
   - Bad `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`.
   - Missing S3 permissions.

6. Signed CloudFront URL fails
   - Invalid `CLOUDFRONT_KEY_PAIR_ID` or wrong base64 private key.

7. ECS task keeps restarting
   - Open CloudWatch logs.
   - Usually missing/misnamed env var or invalid secret mapping.

8. API task is healthy but generation never completes
   - Worker service missing or worker task crashing.
   - Check `/ecs/prompt-to-animate/worker` logs.

9. ACM cert issued but HTTPS still not working
   - HTTPS listener not attached on ALB.
   - Listener may still be HTTP-only.

10. DNS resolves but reaches wrong site
   - `api` CNAME is pointing to wrong target or stale record still exists.
   - Confirm `nslookup api.manimancer.fun` resolves to your ALB DNS name.


### 24.1 Real Debugging Timeline (What We Actually Hit)

1. IAM policy quota error while adding permissions
   - Symptom: `The selected policies exceed this account's quota` in IAM user permissions screen.
   - Cause: User already had too many attached managed policies.
   - Fix: Temporarily attach only `AdministratorAccess` to deployment IAM user, complete deployment, then reduce to least-privilege later.

2. ECS cluster creation failed with service-linked role error
   - Symptom: `Unable to assume the service linked role` while creating cluster from console.
   - Cause: ECS service-linked role was not initialized.
   - Fix: Run CLI once: `aws ecs create-cluster --cluster-name pta-cluster --region ap-south-1`, then refresh console.

3. ALB created in private subnets by mistake
   - Symptom: Warning that selected subnets had no route to internet gateway; ALB would not receive internet traffic.
   - Cause: Private subnets were selected for internet-facing ALB.
   - Fix: Recreate/update ALB using public subnets only (one in each AZ).

4. Target group VPC mismatch risk
   - Symptom: Target group creation defaults to default VPC.
   - Cause: Wrong VPC selected while creating `pta-api-tg`.
   - Fix: Ensure target group VPC is `pta-vpc` (same VPC used by ALB and ECS services).

5. ACM certificate failed with CAA error
   - Symptom: ACM status `Failed` with message about certificate authority authorization (CAA).
   - Cause: DNS provider policy blocked Amazon CA issuance.
   - Fix: Delete failed cert, request new cert, add DNS validation CNAME correctly, and allow Amazon CA in DNS CAA records if configured.

6. DNS hosted outside AWS (Vercel DNS)
   - Symptom: Confusion about whether Route53 delegation is mandatory.
   - Cause: Domain DNS was managed in Vercel, not Hostinger/Route53.
   - Fix: No Route53 required in this case. Add ALB CNAME and ACM validation CNAME directly in Vercel DNS.

7. PowerShell vs Bash env variable syntax confusion
   - Symptom: `ECR_IMAGE_URI=...` returned `CommandNotFoundException` in PowerShell.
   - Cause: Bash syntax used in PowerShell terminal.
   - Fix: Use PowerShell format: `$ECR_IMAGE_URI = "<value>"`.

8. ECS task failed to start due secret JSON escaping
   - Symptom: API task crash with startup config parse errors.
   - Cause: Regex string in secret JSON used escaping that broke JSON decoding.
   - Fix: Save regex as `^https://.*[.]vercel[.]app$` in Secrets Manager JSON and redeploy service.

9. API service showed `0/1` tasks temporarily
   - Symptom: Service active but task count still not running right after create.
   - Cause: Initial deployment still in progress.
   - Fix: Wait for deployment events; validate task becomes `RUNNING`, target becomes healthy, and `/health` returns 200.

10. Health check test showed PowerShell parsing warning
    - Symptom: `Invoke-WebRequest parses the content... UseBasicParsing` warning.
    - Cause: PowerShell default behavior on HTML parsing.
    - Fix: Safe to ignore for JSON endpoint; request succeeded with `200 OK` and healthy Redis/Mongo status.

---

## 25) Final Checklist Before You Call It Done

1. `https://api.manimancer.fun/health` works.
2. `https://api.manimancer.fun/docs` works.
3. API ECS service healthy behind ALB.
4. Worker ECS service healthy.
5. Upstash reachable from both tasks.
6. Atlas reachable from both tasks.
7. S3 upload succeeds.
8. CloudFront signed URL generation succeeds.
9. Clerk auth works from frontend.
10. Vercel uses correct `NEXT_PUBLIC_API_URL`.

---

## 26) Exactly Which Keys Are Required vs Optional

Required:
1. `MONGODB_URI`
2. `MONGODB_DATABASE`
3. `REDIS_URL`
4. `AWS_ACCESS_KEY_ID`
5. `AWS_SECRET_ACCESS_KEY`
6. `AWS_REGION`
7. `S3_BUCKET_NAME`
8. `CLOUDFRONT_DOMAIN`
9. `CLOUDFRONT_KEY_PAIR_ID`
10. `CLOUDFRONT_PRIVATE_KEY_BASE64`
11. One LLM provider key set (`GROQ_API_KEY` or Azure config)
12. `CLERK_ISSUER`
13. `CLERK_AUTHORIZED_PARTIES`
14. `CORS_ALLOWED_ORIGINS`

Strongly recommended:
1. `CLERK_JWKS_URL`
2. `CLERK_JWT_AUDIENCE`
3. `RATE_LIMIT_GENERATE_PER_MINUTE`
4. `RATE_LIMIT_STATUS_PER_MINUTE`
5. `JOB_OWNER_TTL_SECONDS`

Optional tuning:
1. `MANIM_RENDER_TIMEOUT_SECONDS`
2. `MANIM_RENDER_TIMEOUT_MAX_SECONDS`
3. `MANIM_RENDER_REPAIR_ATTEMPTS`
4. `MANIM_TEMP_DIR`
5. `MANIM_VISUAL_QA_ENABLED`
6. `MANIM_VISUAL_QA_MODE`
