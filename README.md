# 🎬 Manimancer

> **Turn your ideas into stunning 2D animations with AI.**

🌐 **Live Demo:** [manimancer.fun](https://www.manimancer.fun)

Manimancer is a full-stack web application that generates high-quality educational animations from simple text prompts. Powered by AI (Groq LLM) and the Manim library, it transforms your concepts into professional visualizations in seconds.

---

## 📋 Table of Contents

- [Features](#-features)
- [Demo](#-demo)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Production Deployment](#-production-deployment)
- [Docker Deployment (Local)](#-docker-deployment-local-development)
- [Data Persistence](#-data-persistence)
- [Testing Guide](#-testing-guide)
- [How It Works](#-how-it-works)
- [API Reference](#-api-reference)
- [Configuration](#-configuration)
- [Example Prompts](#-example-prompts)
- [Troubleshooting](#-troubleshooting)
- [Authentication](#-authentication)
- [Pricing Plans](#-pricing-plans)
- [License](#-license)

---

## ✨ Features

| Feature | Description |
|:--------|:------------|
| 🪄 **AI-Powered Generation** | Describe what you want in plain English, and the AI writes production-ready Manim code |
| 🎥 **Resolution Selector** | Choose from **720p 30fps**, **1080p 60fps**, or **4K 60fps** based on your tier |
| ⏱️ **Configurable Duration** | Choose from Short (5s), Medium (15s), Long (1m), Deep Dive (2m+), or Extended (5m) |
| 📜 **Code Transparency** | Inspect the generated Manim Python code powering your animation |
| 💾 **One-Click Download** | Save your creations directly to your device |
| ☁️ **Cloud Storage (S3)** | Videos stored securely in AWS S3 with CloudFront CDN delivery |
| 🔐 **Signed URLs** | Time-limited, private access to videos via CloudFront signed URLs |
| 🔐 **User Authentication** | Secure sign-in/sign-up with Clerk (modal-based, no redirect) |
| 🗄️ **MongoDB Persistence** | Chat history and video references saved per-user in MongoDB Atlas |
| 💳 **Dodo Payments** | Secure payment processing for subscriptions and one-time purchases |
| 💎 **Pricing Plans** | Free, Basic ($3), and Pro ($20/mo) tiers with resolution access |
| 🌗 **Dark Mode** | Beautiful glassmorphic UI with full dark mode support |
| 📱 **Responsive Design** | Works seamlessly on desktop and mobile devices |
| 📚 **History Sidebar** | Browse and replay your previously generated animations (persisted) |
| ⚡ **Real-Time Progress** | Server-Sent Events (SSE) provide live generation progress updates |

---

## 🎬 Demo

| Generate Animation | Progress Tracking |
|:-------------------|:------------------|
| Enter a prompt, select duration, click generate | Watch real-time progress through 6 stages |

### Animation Lengths

| Option | Duration | Best For |
|:-------|:---------|:---------|
| **Short (5s)** | 5-10 seconds | Quick concepts, single visualizations |
| **Medium (15s)** | 15-20 seconds | 2-3 step explanations |
| **Long (1m)** | 55-70 seconds | Detailed tutorials with multiple sections |
| **Deep Dive (2m+)** | 110-130 seconds | Comprehensive lessons with 6 sections and examples |
| **Extended (5m)** | 280-320 seconds | University mini-lectures with 8 sections |

### Video Resolutions

| Resolution | Manim Flag | Free Tier | Basic Tier | Pro Tier |
|:-----------|:-----------|:----------|:-----------|:---------|
| **720p 30fps** | `-qm` | ✅ | ✅ (1 credit) | ✅ (1 credit) |
| **1080p 60fps** | `-qh` | 🔒 Locked | ✅ (1 credit) | ✅ (1 credit) |
| **4K 60fps** | `-qk` | 🔒 Locked | ✅ (2.5 credits) | ✅ (1 credit) |

---

## 🏗️ Architecture

### Production Deployment

| Component | Platform | URL |
|:----------|:---------|:----|
| **Frontend** | Vercel | [manimancer.fun](https://www.manimancer.fun) |
| **Backend API** | DigitalOcean App Platform | [manimancer-api-n4gox.ondigitalocean.app](https://manimancer-api-n4gox.ondigitalocean.app) |
| **Worker** | DigitalOcean App Platform | Same app, separate container |
| **Database** | MongoDB Atlas | Cloud-hosted |
| **Redis** | Upstash | Serverless Redis |
| **Video Storage** | AWS S3 + CloudFront | CDN-delivered with signed URLs |

### High-Level System Architecture

```mermaid
flowchart TB
    subgraph Browser["🌐 User's Browser"]
        subgraph Frontend["Next.js 16 Frontend (Vercel)"]
            Clerk["Clerk Auth<br/>(Sign In/Up Modal)"]
            UI["AnimationGenerator<br/>Component"]
            Sidebar["History Sidebar<br/>+ Upgrade Button"]
            Pricing["PricingModal<br/>(3 Tiers)"]
        end
    end
    
    subgraph DigitalOcean["🌊 DigitalOcean App Platform"]
        subgraph API["Backend API (Web Service)"]
            FastAPI["FastAPI Backend"]
            LLM["llm_service.py"]
        end
        
        subgraph Worker["Background Worker"]
            RQ["RQ Worker<br/>(Video Generation)"]
            Manim["manim_service.py"]
        end
    end
    
    subgraph External["☁️ External Services"]
        Groq["Groq LLM API<br/>(Kimi K2 Model)"]
        ClerkAPI["Clerk API"]
        S3["AWS S3 Bucket"]
        CloudFront["CloudFront CDN"]
        Upstash["Upstash Redis"]
        MongoAtlas["MongoDB Atlas"]
    end
    
    Clerk --> ClerkAPI
    UI -->|"POST /generate-stream"| FastAPI
    FastAPI --> LLM
    LLM -->|"Prompt"| Groq
    Groq -->|"Manim Code"| LLM
    FastAPI -->|"Enqueue Job"| Upstash
    Upstash --> RQ
    RQ --> Manim
    Manim -->|"Render Video"| S3
    S3 --> CloudFront
    CloudFront -->|"Signed URL"| UI
    FastAPI -->|"Save Chat"| MongoAtlas
```

### Request Flow Sequence

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant C as 🔐 Clerk
    participant F as 🖥️ Frontend
    participant B as ⚙️ Backend
    participant G as 🤖 Groq LLM
    participant M as 🎬 Manim

    Note over U,C: Authentication (optional)
    U->>C: Click Sign In/Up
    C-->>U: Modal authentication
    C-->>F: Session token

    Note over U,M: Animation Generation
    U->>F: Enter prompt + select duration
    F->>B: POST /generate-stream
    
    B->>F: SSE: Step 1 - Analyzing prompt
    B->>G: Compose scene plan (Pass 1)
    B->>F: SSE: Step 2 - Composing scenes
    G-->>B: Return scene plan JSON
    B->>G: Generate code from plan (Pass 2)
    B->>F: SSE: Step 3 - Generating code
    G-->>B: Return Python code
    B->>F: SSE: Step 4 - Validating / repairing / visual QA
    
    B->>M: Execute manim -qh script.py
    B->>F: SSE: Step 5 - Rendering / finalizing
    M-->>B: Generate video.mp4
    
    B-->>F: SSE: Step 6 - Complete {video_url, code}
    F-->>U: Display video + code viewer
```

---

## 🛠️ Tech Stack

### Frontend

| Technology | Version | Purpose |
|:-----------|:--------|:--------|
| [Next.js](https://nextjs.org/) | 16.0.10 | React framework with App Router |
| [React](https://react.dev/) | 19.2.1 | UI component library |
| [TypeScript](https://www.typescriptlang.org/) | 5.x | Type-safe JavaScript |
| [TailwindCSS](https://tailwindcss.com/) | 4.x | Utility-first CSS framework |
| [Framer Motion](https://www.framer.com/motion/) | 12.x | Smooth animations and transitions |
| [Clerk](https://clerk.com/) | 6.36.2 | Authentication (modal-based sign in/up) |
| [Lucide React](https://lucide.dev/) | 0.556.0 | Beautiful icon library |
| [next-themes](https://github.com/pacocoursey/next-themes) | 0.4.6 | Dark mode support |
| [@dodopayments/nextjs](https://dodopayments.com) | Latest | Payment processing SDK |

### Backend

| Technology | Version | Purpose |
|:-----------|:--------|:--------|
| [Python](https://www.python.org/) | 3.10+ | Backend runtime |
| [FastAPI](https://fastapi.tiangolo.com/) | Latest | Modern async web framework with SSE support |
| [Uvicorn](https://www.uvicorn.org/) | Latest | ASGI server |
| [LangChain Groq](https://python.langchain.com/) | Latest | LLM integration |
| [Manim CE](https://www.manim.community/) | Latest | Mathematical animation engine |
| [Motor](https://motor.readthedocs.io/) | Latest | Async MongoDB driver (motor.motor_asyncio) |
| [PyMongo](https://pymongo.readthedocs.io/) | Latest | MongoDB driver (used by Motor) |
| [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) | Latest | AWS SDK for Python (S3 uploads) |
| [Cryptography](https://cryptography.io/) | Latest | RSA signing for CloudFront URLs |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | Latest | Environment variable management |

### AI/LLM

| Component | Details |
|:----------|:--------|
| **Provider** | [Groq Cloud](https://groq.com/) (ultra-fast inference) |
| **Model** | `moonshotai/kimi-k2-instruct-0905` |
| **Temperature** | 0.2 (slightly creative, but focused for consistent animations) |
| **Context** | Detailed system prompt with Manim best practices, timing guides, and visual standards |

---

## 📁 Project Structure

```
prompt_to_animate/
│
├── .env                              # ⚠️ Backend: GROQ_API_KEY, AWS, MongoDB
├── .gitignore                        # Git ignore rules
├── README.md                         # This file
│
├── backend/                          # 🐍 Python FastAPI Backend
│   ├── __init__.py                   # Package marker
│   ├── main.py                       # FastAPI app, routes (/generate, /generate-stream, /chats)
│   ├── llm_service.py                # 2-pass generation (compose -> codegen -> validate/repair)
│   ├── prompts/                      # Versioned runtime prompt assets
│   │   ├── composer_system.md
│   │   ├── codegen_system.md
│   │   ├── repair_system.md
│   │   └── length_profiles.json
│   ├── manim_service.py              # Manim CLI execution, S3 upload integration
│   ├── s3_service.py                 # ⚠️ AWS S3 upload + CloudFront signed URL generation
│   ├── database.py                   # MongoDB connection management (Motor async)
│   ├── models.py                     # Pydantic schemas for chat documents
│   ├── temp/                         # 🔄 Temporary Python scripts (auto-cleaned)
│   │   └── .gitkeep
│   ├── tests/                        # Backend unit tests
│   └── venv/                         # 🔄 Python virtual environment
│
├── private_key.pem                   # ⚠️🔒 CloudFront RSA private key (DO NOT COMMIT)
├── public_key.pem                    # 🔄 CloudFront public key (uploaded to AWS)
│
├── frontend/                         # ⚛️ Next.js 16 Frontend
│   ├── .env.local                    # ⚠️ Frontend: Clerk + Dodo Payments keys
│   ├── app/                          # Next.js App Router
│   │   ├── layout.tsx                # Root layout (ClerkProvider, ThemeProvider)
│   │   ├── page.tsx                  # Main page
│   │   ├── globals.css               # Global styles & design tokens
│   │   ├── favicon.ico               # App icon
│   │   ├── icon.svg                  # SVG icon
│   │   └── api/                      # API Routes
│   │       ├── checkout/route.ts     # Dodo Payments checkout handler
│   │       ├── webhook/dodo/route.ts # Dodo Payments webhook handler
│   │       └── customer-portal/route.ts # Subscription management
│   ├── components/                   # React Components
│   │   ├── AnimationGenerator.tsx    # Main generator with SSE progress
│   │   ├── Sidebar.tsx               # History sidebar + Clerk auth + Upgrade button
│   │   ├── PricingModal.tsx          # Pricing plans modal (Free/Basic/Pro)
│   │   ├── Navbar.tsx                # Top navigation bar
│   │   ├── Footer.tsx                # Page footer
│   │   ├── Logo.tsx                  # Manimancer logo (Nabla font)
│   │   ├── ThemeProvider.tsx         # Dark mode provider
│   │   └── icons/                    # Custom SVG icons
│   ├── lib/                          # Utilities
│   │   ├── utils.ts                  # cn() helper (clsx + tailwind-merge)
│   │   └── api.ts                    # API functions for chat operations
│   ├── public/                       # Static assets
│   ├── package.json                  # Node.js dependencies
│   ├── tsconfig.json                 # TypeScript configuration
│   ├── next.config.ts                # Next.js configuration
│   ├── postcss.config.mjs            # PostCSS configuration
│   ├── eslint.config.mjs             # ESLint configuration
│   ├── node_modules/                 # 🔄 npm packages
│   └── .next/                        # 🔄 Build cache
│
└── generated_animations/             # 🔄 Output videos (served at /videos/*)
    └── .gitkeep
```

### Legend

| Symbol | Meaning |
|:-------|:--------|
| ⚠️ | You must create/configure this file |
| 🔄 | Auto-generated (not tracked in git) |
| 🐍 | Python |
| ⚛️ | React/Next.js |

---

## 🚀 Getting Started

### Prerequisites

| Requirement | Version | Check Command | Installation |
|:------------|:--------|:--------------|:-------------|
| **Python** | 3.10+ | `python --version` | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 18+ | `node --version` | [nodejs.org](https://nodejs.org/) |
| **npm** | 9+ | `npm --version` | Comes with Node.js |
| **FFmpeg** | Latest | `ffmpeg -version` | [ffmpeg.org](https://ffmpeg.org/download.html) |
| **LaTeX** | Optional | `latex --version` | [MiKTeX](https://miktex.org/) or [TeX Live](https://www.tug.org/texlive/) |

> **Why FFmpeg?** Manim uses FFmpeg to encode video frames into MP4 files.
> **Why LaTeX?** Optional, but required for mathematical equations (`MathTex`).

### Step-by-Step Setup

#### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Aafimalek/prompt_to_animate.git
cd prompt_to_animate
```

#### 2️⃣ Set Up the Backend

```bash
# Navigate to backend directory
cd backend

# Create Python virtual environment
python -m venv venv

# Activate the virtual environment
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install fastapi uvicorn langchain-groq python-dotenv manim boto3 cryptography motor pymongo

# Return to project root
cd ..
```

#### 3️⃣ Configure Backend Environment

Create a `.env` file in the **project root**:

```env
# Groq LLM API Key
GROQ_API_KEY=your_groq_api_key_here

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_REGION=ap-south-1
S3_BUCKET_NAME=your_bucket_name

# CloudFront Configuration
CLOUDFRONT_DOMAIN=your_distribution.cloudfront.net
CLOUDFRONT_KEY_PAIR_ID=your_key_pair_id
CLOUDFRONT_PRIVATE_KEY_PATH=./private_key.pem

# MongoDB Configuration (for chat history persistence)
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database_name
MONGODB_DATABASE=prompt_to_animate
```

> 🔑 **Get your FREE Groq API key:** [console.groq.com](https://console.groq.com/) → Sign up → Create API Key

> ☁️ **AWS credentials are optional for local development.** If not configured, videos will be served locally from `/videos/`.

> 🗄️ **Get your FREE MongoDB Atlas connection string:** [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas) → Create a cluster → Connect → Drivers → Copy connection string

#### 4️⃣ Set Up AWS S3 + CloudFront (Optional but Recommended)

For production deployments with secure, scalable video delivery:

**Step 1: Create S3 Bucket**
1. Go to [AWS S3 Console](https://s3.console.aws.amazon.com/s3/)
2. Click **Create bucket**
3. Name it (e.g., `manimancer-videos`)
4. **Block all public access**: Keep enabled (we'll use CloudFront)
5. Create the bucket

**Step 2: Create IAM User**
1. Go to **IAM** → **Users** → **Create user**
2. Name it (e.g., `manimancer-s3-user`)
3. Attach policies: `AmazonS3FullAccess`, `CloudFrontFullAccess`
4. Go to **Security credentials** → **Create access key**
5. Copy `Access Key ID` and `Secret Access Key` to your `.env`

**Step 3: Create CloudFront Distribution**
1. Go to [CloudFront Console](https://console.aws.amazon.com/cloudfront/)
2. Click **Create distribution**
3. **Origin domain**: Select your S3 bucket
4. **Origin access**: Select **Origin access control settings (recommended)**
5. Create a new OAC and update the S3 bucket policy when prompted
6. **Restrict viewer access**: **Yes**
7. Create a **key group** (see Step 4)
8. Create the distribution and copy the **Domain name** to your `.env`

**Step 4: Generate RSA Key Pair for Signed URLs**

```bash
# Generate private key (keep this secret!)
openssl genrsa -out private_key.pem 2048

# Generate public key (upload to CloudFront)
openssl rsa -pubout -in private_key.pem -out public_key.pem
```

**Step 5: Upload Public Key to CloudFront**
1. Go to **CloudFront** → **Key management** → **Public keys**
2. Click **Create public key**
3. Paste contents of `public_key.pem`
4. Copy the **Key ID** to your `.env` as `CLOUDFRONT_KEY_PAIR_ID`

**Step 6: Create Key Group**
1. Go to **CloudFront** → **Key management** → **Key groups**
2. Create a key group with your public key
3. Attach the key group to your distribution's behavior

> 🔒 **Security Note:** The `private_key.pem` is in `.gitignore` and should **NEVER** be committed to version control.

#### 5️⃣ Set Up the Frontend

```bash
cd frontend
npm install
cd ..
```

#### 6️⃣ Configure Clerk Authentication

1. Create a free account at [clerk.com](https://clerk.com)
2. Create a new application in the Clerk Dashboard
3. Get your API keys from **Configure → API Keys**
4. Create `frontend/.env.local`:

```env
# Clerk Authentication Keys
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_key_here
CLERK_SECRET_KEY=sk_test_your_key_here

# Redirect URLs (modal mode, redirect back to home)
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/

# Dodo Payments Configuration
DODO_PAYMENTS_API_KEY=your_api_key_from_dashboard
DODO_PAYMENTS_WEBHOOK_KEY=whsec_your_webhook_secret
DODO_PAYMENTS_RETURN_URL=https://your-domain.com/
DODO_PAYMENTS_ENVIRONMENT=live_mode
```

> ⚠️ **Important:** Do NOT set `NEXT_PUBLIC_CLERK_SIGN_IN_URL` or `NEXT_PUBLIC_CLERK_SIGN_UP_URL` — the app uses modal mode.

> 💳 **Get your Dodo Payments credentials:** [app.dodopayments.com](https://app.dodopayments.com) → Settings → API Keys

#### 7️⃣ Run the Application

Open **two terminal windows**:

**Terminal 1 — Backend Server:**

```bash
# From project root (Windows)
backend\venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000

# From project root (macOS/Linux)
backend/venv/bin/python -m uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend Dev Server:**

```bash
cd frontend
npm run dev
```

#### 7️⃣ Open the App

Navigate to **http://localhost:3000** in your browser.

---

## 🌐 Production Deployment

Manimancer is deployed using **DigitalOcean App Platform** (backend) and **Vercel** (frontend).

### Current Production URLs

| Service | URL |
|:--------|:----|
| **Frontend** | [manimancer.fun](https://www.manimancer.fun) |
| **Backend API** | [manimancer-api-n4gox.ondigitalocean.app](https://manimancer-api-n4gox.ondigitalocean.app) |
| **API Docs** | [/docs](https://manimancer-api-n4gox.ondigitalocean.app/docs) |
| **Health Check** | [/health](https://manimancer-api-n4gox.ondigitalocean.app/health) |

### DigitalOcean App Platform Setup

The backend runs on DigitalOcean App Platform with two components:

| Component | Type | Specs | Cost | Run Command |
|:----------|:-----|:------|:-----|:------------|
| **API** | Web Service | 1 vCPU, 1GB RAM | $12/mo | `uvicorn backend.main:app --host 0.0.0.0 --port 8000` |
| **Worker** | Worker | 2 vCPU, 4GB RAM | $50/mo | `python -m backend.worker` |

**Total: ~$62/month**

#### Environment Variables (DigitalOcean)

Both API and Worker components need these environment variables:

```env
GROQ_API_KEY=your_groq_api_key
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=ap-south-1
S3_BUCKET_NAME=your_s3_bucket_name
CLOUDFRONT_DOMAIN=your_cloudfront_domain.cloudfront.net
CLOUDFRONT_KEY_PAIR_ID=your_key_pair_id
CLOUDFRONT_PRIVATE_KEY_BASE64=your_base64_encoded_private_key
REDIS_URL=rediss://your_upstash_redis_url
MONGODB_URI=mongodb+srv://your_mongodb_atlas_uri
MONGODB_DATABASE=prompt_to_animate
MANIM_VISUAL_QA_ENABLED=false
MANIM_VISUAL_QA_MODE=balanced
MANIM_VISUAL_QA_MAX_REPAIRS=1
MANIM_VISUAL_QA_LOG_ARTIFACTS=false
```

### Vercel Frontend Setup

1. Import the repository on [Vercel](https://vercel.com)
2. Set the root directory to `frontend`
3. Add environment variables:

```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_your_key
CLERK_SECRET_KEY=sk_live_your_key
NEXT_PUBLIC_API_URL=https://manimancer-api-n4gox.ondigitalocean.app
DODO_PAYMENTS_API_KEY=your_dodo_api_key
DODO_PAYMENTS_WEBHOOK_KEY=whsec_your_webhook_secret
```

4. Deploy and add custom domain (manimancer.fun)

---

## 🐳 Docker Deployment (Local Development)

The recommended way to run Manimancer locally is using Docker Compose, which handles all dependencies automatically.

### Quick Start

```bash
# Start all services (API, Worker, Redis, MongoDB)
docker-compose up -d

# Stop services (data persists)
docker-compose stop

# Restart services
docker-compose up -d

# View logs
docker logs pta-api -f      # API logs
docker logs pta-worker -f   # Worker logs
```

### Container Services

| Container | Image | Port | Purpose |
|:----------|:------|:-----|:--------|
| `pta-api` | prompt_to_animate-backend-api | 8000 | FastAPI backend server |
| `pta-worker` | prompt_to_animate-backend-worker | - | RQ worker for video generation |
| `pta-redis` | redis:7-alpine | 6379 | Job queue and caching |
| `pta-mongo` | mongo:7 | 27017 | Database persistence |

### Docker Architecture

```mermaid
flowchart LR
    subgraph Network["pta-network"]
        API["pta-api<br/>:8000"]
        Worker["pta-worker"]
        Redis["pta-redis<br/>:6379"]
        Mongo["pta-mongo<br/>:27017"]
    end
    
    subgraph Volumes["Persistent Volumes"]
        MongoVol["mongo-data"]
        RedisVol["redis-data"]
    end
    
    API -->|"Enqueue Jobs"| Redis
    Worker -->|"Process Jobs"| Redis
    API --> Mongo
    Mongo --> MongoVol
    Redis --> RedisVol
```

### System Dependencies (Installed in Docker)

The Docker image includes all Manim dependencies:

| Package | Version | Purpose |
|:--------|:--------|:--------|
| FFmpeg | 7.1.3 | Video encoding |
| dvisvgm | 3.4.4 | LaTeX to SVG conversion |
| pdfTeX | TeX Live 2025 | Mathematical equations |
| manimpango | 0.6.1 | Pango text rendering |
| Cairo | Latest | Vector graphics |

---

## 💾 Data Persistence

### How Docker Volumes Work

Your data is stored in Docker volumes, which persist on your disk independently of containers.

| Command | Container Status | Volume Status | Data Preserved |
|:--------|:-----------------|:--------------|:---------------|
| `docker-compose stop` | Stopped | ✅ Untouched | ✅ **Yes** |
| `docker-compose down` | Removed | ✅ Untouched | ✅ **Yes** |
| `docker-compose down -v` | Removed | ❌ **Deleted** | ❌ **No** |
| Restart PC | Stopped | ✅ Untouched | ✅ **Yes** |
| Docker Desktop restart | Stopped | ✅ Untouched | ✅ **Yes** |

> ⚠️ **Warning:** Never use `docker-compose down -v` unless you want to delete all user data!

### Volume Locations

| Volume | Purpose | Typical Size |
|:-------|:--------|:-------------|
| `prompt_to_animate_mongo-data` | User accounts, chats, credits | ~10-100 MB |
| `prompt_to_animate_redis-data` | Job queue cache | ~1-10 MB |

### Check Volume Status

```bash
# List project volumes
docker volume ls --filter "name=prompt_to_animate"

# Inspect a volume
docker volume inspect prompt_to_animate_mongo-data
```

### Data Flow

- **User accounts & credits** → MongoDB → `mongo-data` volume (persistent)
- **Chat history** → MongoDB → `mongo-data` volume (persistent)
- **Job queue** → Redis → `redis-data` volume (ephemeral)
- **Generated videos** → AWS S3 (cloud, not in Docker)

---

## 🧪 Testing Guide

Use this checklist to verify all components are working correctly.

### 1. Backend Health Check

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{"status":"healthy","services":{"redis":"connected","mongodb":"connected"}}
```

### 2. Redis Connection

```bash
docker exec pta-redis redis-cli ping
```

**Expected:** `PONG`

### 3. MongoDB Connection

```bash
# Check users collection
docker exec pta-mongo mongosh prompt_to_animate --eval "db.users.find().pretty()"

# Check chats collection
docker exec pta-mongo mongosh prompt_to_animate --eval "db.chats.find().pretty()"
```

### 4. Worker Status

```bash
docker logs pta-worker --tail 20
```

Look for: `Worker rq:worker:... started`

### 5. Video Generation Test

| Step | Expected Result |
|:-----|:----------------|
| 1. Open http://localhost:3000 | Homepage loads |
| 2. Sign in with Clerk | Auth modal → redirects to app |
| 3. Enter: "Show a circle" | Prompt accepted |
| 4. Select: Medium (15s) | Duration selected |
| 5. Click Generate | Progress indicators appear |
| 6. Wait for completion | Video plays in browser |

### 6. Authentication (Clerk)

| Test | How to Verify |
|:-----|:--------------|
| Sign Up | Create new account → should redirect to `/` |
| Sign In | Existing account → should redirect to `/` |
| Sign Out | Click avatar → Sign out → buttons change |
| Protected Route | Try generating without sign-in → should be blocked |

### 7. Payment Integration (Dodo)

| Step | Expected Result |
|:-----|:----------------|
| 1. Click Upgrade | Pricing modal opens |
| 2. Select Pro ($20/mo) | Redirected to Dodo checkout |
| 3. Use test card: `4242 4242 4242 4242` | Payment processes |
| 4. Return to app | Credits updated |

### 8. Verify Credits in MongoDB

```bash
docker exec pta-mongo mongosh prompt_to_animate --eval "db.users.find({}, {clerk_id:1, tier:1, basic_credits:1}).pretty()"
```

### Complete System Verification

```bash
# All-in-one health check
echo "=== Container Status ===" && docker-compose ps
echo "=== API Health ===" && curl -s http://localhost:8000/health
echo "=== Redis ===" && docker exec pta-redis redis-cli ping
echo "=== MongoDB ===" && docker exec pta-mongo mongosh --eval "db.adminCommand('ping')"
```

---

## ⚙️ How It Works

### Generation Pipeline

```mermaid
flowchart LR
    A["👤 User Input"] --> B["🖥️ Frontend"]
    B -->|"POST /generate-stream"| C["⚙️ Backend API"]
    C --> D["🧭 Compose Scenes (LLM Pass 1)"]
    D --> E["🧠 Generate Code (LLM Pass 2)"]
    E --> F["✅ Strict Validation Gate"]
    F -->|"Auto-repair (max 2 retries)"| E
    F -->|"Python Code"| G["🎬 Manim Render"]
    G -->|"MP4 Video"| H["📁 Storage"]
    H --> I["🎥 Video Player"]
```

### SSE Progress Steps

The `/generate-stream` endpoint sends **6 progress updates** via Server-Sent Events:

| Step | Status | Description |
|:-----|:-------|:------------|
| 1 | `analyzing` | Analyzing your prompt |
| 2 | `composing` | Building internal scene-by-scene plan |
| 3 | `generating` | Generating Manim code from scene plan |
| 4 | `validating` / `repairing` / `quality_checking` / `quality_repairing` | Static validation plus optional visual QA and repair |
| 5 | `rendering` / `finalizing` | Rendering + upload/finalization |
| 6 | `complete` | Video ready! Returns `video_url` and `code` |

### Duration Mapping

| Selection | Target Duration | LLM Instructions |
|:----------|:----------------|:-----------------|
| **Medium (15s)** | 15-20 seconds | ~2 sections, concise reveal, min 6 `wait()` calls |
| **Long (1m)** | 55-65 seconds | ~5 sections, worked explanation, min 25 `wait()` calls |
| **Deep Dive (2m)** | 110-130 seconds | ~6 sections, deep walkthrough, min 40 `wait()` calls |
| **Extended (5m)** | 280-320 seconds | ~8 sections, lecture style pacing, min 80 `wait()` calls |

---

## 📡 API Reference

### Base URLs

| Environment | URL |
|:------------|:----|
| **Production** | `https://manimancer-api-n4gox.ondigitalocean.app` |
| **Local Development** | `http://localhost:8000` |

### Endpoints

#### `POST /generate`

Standard request/response endpoint (no streaming).

**Request Body:**
```json
{
  "prompt": "Explain the Pythagorean theorem",
  "length": "Medium (15s)",
  "resolution": "720p"
}
```

**Response:**
```json
{
  "video_url": "http://localhost:8000/videos/abc123.mp4",
  "code": "from manim import *\n\nclass GenScene(Scene):..."
}
```

#### `POST /generate-stream`

Streaming endpoint using Server-Sent Events (SSE).

**Request Body:**
```json
{
  "prompt": "Explain the Pythagorean theorem",
  "length": "Medium (15s)",
  "resolution": "1080p",
  "clerk_id": "user_abc123",
  "style_pack": "classic_clean",
  "voiceover_mode": "none",
  "voiceover_text": "",
  "export_mode": "video"
}
```

**Resolution options:** `720p`, `1080p`, `4k`

**Response:** `text/event-stream`

```
data: {"step": 1, "status": "analyzing", "message": "Analyzing your prompt..."}

data: {"step": 2, "status": "composing", "message": "Composing internal scene plan..."}

data: {"step": 2, "status": "retrieving_memory", "message": "Retrieving high-quality scene memories..."}

data: {"step": 2, "status": "selecting_style", "message": "Selecting visual style pack..."}

data: {"step": 3, "status": "generating", "message": "Generating Manim code from scene plan..."}

data: {"step": 3, "status": "candidate_generating", "message": "Generating 3 code candidate(s)..."}

data: {"step": 4, "status": "candidate_scoring", "message": "Scoring candidates with reward model..."}

data: {"step": 4, "status": "validating", "message": "Validating generated code..."}

data: {"step": 4, "status": "repairing", "message": "Repairing invalid code (attempt 1/2)..."}

data: {"step": 4, "status": "quality_checking", "message": "Running visual quality checks..."}

data: {"step": 4, "status": "quality_repairing", "message": "Repairing visual layout (attempt 1/1)..."}

data: {"step": 5, "status": "rendering", "message": "Rendering at 1080p..."}

data: {"step": 5, "status": "finalizing", "message": "Uploading to cloud storage..."}

data: {"step": 6, "status": "complete", "message": "Video ready!", "video_url": "...", "code": "...", "chat_id": "..."}
```

Additional advanced endpoints:

- `GET /style-packs`
- `POST /scene-editor/partial-render`
- `POST /export/interactive`
- `GET /scene-memory/search?prompt=...&top_k=3`
- `POST /feedback/quality`
- `POST /chats/{clerk_id}/{chat_id}/comments`
- `GET /chats/{clerk_id}/{chat_id}/comments`
- `POST /chats/{clerk_id}/{chat_id}/variants`
- `GET /chats/{clerk_id}/{chat_id}/variants`
- `GET /chats/{clerk_id}/{chat_id}/variants/{variant_id}/diff`

#### `GET /chats/{clerk_id}`

Get all chats for a specific user (requires Clerk user ID).

**Response:**
```json
{
  "chats": [
    {
      "id": "676...",
      "prompt": "Explain the Pythagorean theorem",
      "length": "Medium (15s)",
      "video_url": "https://cloudfront.../video.mp4",
      "code": "from manim import *...",
      "created_at": "2025-12-11T14:30:00Z"
    }
  ],
  "total": 1
}
```

#### `GET /chats/{clerk_id}/{chat_id}`

Get a specific chat by ID with a fresh signed URL.

**Response:** Single chat object (same schema as above)

#### `DELETE /chats/{clerk_id}/{chat_id}`

Delete a specific chat. Only the owner (matching clerk_id) can delete their chat.

**Response:**
```json
{"message": "Chat deleted successfully"}
```

#### `GET /job/{job_id}`

Get the current status of a video generation job.

**Response:**
```json
{
  "job_id": "abc123",
  "status": "finished",
  "result": {
    "video_url": "https://cloudfront.../video.mp4",
    "code": "from manim import *..."
  }
}
```

**Possible status values:** `queued`, `started`, `finished`, `failed`

#### `GET /health`

Health check endpoint for container orchestration.

**Response:**
```json
{"status": "healthy", "services": {"redis": "connected", "mongodb": "connected"}}
```

#### `GET /usage/{clerk_id}`

Get user's current usage and tier info.

**Response:**
```json
{
  "tier": "pro",
  "basic_credits": 100,
  "monthly_count": 5,
  "monthly_limit": 50,
  "can_generate": true
}
```

#### `POST /webhook/payment`

Handle payment webhook from Dodo Payments.

**Request Body:**
```json
{
  "event_type": "payment_succeeded",
  "clerk_id": "user_abc123",
  "product_id": "pdt_9pgk0uVBWpT13GL0Mfqbc"
}
```

**Response:**
```json
{"status": "success", "message": "Credits added"}
```

#### `GET /videos/{filename}`

Static file server for generated videos (fallback for local development).

---

## 🎛️ Configuration

### Video Quality Settings

Edit `backend/manim_service.py`:

```python
cmd = [
    sys.executable, "-m", "manim",
    "-qh",  # ◀ Change this flag
    ...
]
```

| Flag | Quality | Resolution | FPS | Render Time |
|:-----|:--------|:-----------|:----|:------------|
| `-ql` | Low | 480p | 15 | ~5s |
| `-qm` | Medium | 720p | 30 | ~15s |
| `-qh` | High | 1080p | 60 | ~45s **(default)** |
| `-qk` | 4K | 2160p | 60 | ~3min |

### LLM Model Settings

Edit `backend/llm_service.py`:

```python
llm = ChatGroq(
    model="moonshotai/kimi-k2-instruct-0905",  # Change model here
    api_key=api_key,
    temperature=0.2  # 0.0 = deterministic, 1.0 = creative (default: 0.2)
)
```

### Prompt Assets and Validation Gate

Runtime prompt behavior is versioned under `backend/prompts/`:

- `composer_system.md` - scene composition instructions (Pass 1)
- `codegen_system.md` - code generation instructions (Pass 2)
- `repair_system.md` - targeted repair instructions
- `runtime_repair_system.md` - runtime failure focused repair prompt
- `visual_repair_system.md` - visual-quality focused repair prompt
- `scene_editor_system.md` - targeted layout edit prompt for interactive scene editing
- `length_profiles.json` - duration and pacing constraints by length

The backend enforces a strict validation gate before rendering:

- Syntax validation (`ast.parse`)
- Required `from manim import *`
- Required `GenScene` scene class
- Duration-based pacing thresholds per selected length profile
- Anti-pattern checks (for example, raw mobjects in `self.play(...)`)
- Unicode math symbol checks inside `MathTex`/`Tex`
- Automatic repair retries (max 2) before hard failure
- Automatic timing rescale to fit target duration window

Visual quality gate (feature flagged):

- Optional low-quality QA render pass before final render
- Out-of-frame text detection
- Text overlap detection
- Crowding warnings and score-based pass/fail (`score >= 85`, zero visual errors)
- Optional one visual repair retry in `balanced` mode
- Optional VLM keyframe critic hook for additional visual feedback

Visual QA environment flags:

- `MANIM_VISUAL_QA_ENABLED=false`
- `MANIM_VISUAL_QA_MODE=balanced` (`balanced` or `max`)
- `MANIM_VISUAL_QA_MAX_REPAIRS=1`
- `MANIM_VISUAL_QA_LOG_ARTIFACTS=false`
- `MANIM_VLM_CRITIC_ENABLED=false`
- `MANIM_VLM_CRITIC_FRAME_COUNT=1`

Advanced generation flags:

- `MANIM_TIMELINE_PACING_ENABLED=true`
- `MANIM_PACING_TOLERANCE_SECONDS=12`
- `MANIM_AUTO_TIMESCALE_ENABLED=true`
- `MANIM_MULTI_CANDIDATE_ENABLED=true`
- `MANIM_MULTI_CANDIDATE_COUNT=3`
- `MANIM_MULTI_CANDIDATE_VISUAL_QA=true`
- `MANIM_SCENE_MEMORY_ENABLED=true`
- `MANIM_SCENE_MEMORY_TOP_K=3`
- `MANIM_REWARD_WEIGHTS_PATH=backend/benchmarks/reward_weights.json`

Render/runtime environment flags:

- `MANIM_RENDER_TIMEOUT_SECONDS=180` (base timeout floor)
- `MANIM_RENDER_TIMEOUT_MAX_SECONDS=3600` (hard cap)
- `MANIM_TEMP_DIR=<optional path>` (avoid writing temp render scripts under watched source dirs)

Benchmark harness:

- Prompt suite: `backend/benchmarks/prompt_suite.json` (30 prompts)
- Runner: `python -m backend.benchmarks.run_visual_quality_benchmark --qa-mode balanced`
- Report output: `backend/benchmarks/last_benchmark_report.json`

### Clerk Appearance

The `UserButton` in `Sidebar.tsx` can be customized:

```tsx
<UserButton
  appearance={{
    elements: {
      avatarBox: "w-8 h-8",
      userButtonPopoverCard: "bg-zinc-900 border border-zinc-800",
      userButtonPopoverActionButton: "hover:bg-zinc-800",
    }
  }}
/>
```

---

## 🧪 Example Prompts

### Mathematics

| Prompt | Duration | Expected Output |
|:-------|:---------|:----------------|
| A circle with its radius and area formula appearing | Short (5s) | Circle with `A = πr²` |
| Visualize the Pythagorean theorem with colored squares | Medium (15s) | Right triangle + squares animation |
| Explain how derivatives work with a tangent line animation | Long (1m) | Full calculus lesson |

### Computer Science

| Prompt | Duration | Expected Output |
|:-------|:---------|:----------------|
| Show binary search finding a number in a sorted array | Medium (15s) | Array with highlight pointers |
| Animate how a stack data structure works (push/pop) | Medium (15s) | Stack visualization |
| Complete tutorial on how merge sort algorithm works | Deep Dive (2m) | Full sorting animation |

### Physics

| Prompt | Duration | Expected Output |
|:-------|:---------|:----------------|
| A pendulum swinging back and forth | Short (5s) | Simple pendulum motion |
| Visualize Newton's laws of motion with examples | Long (1m) | Three laws demonstrated |

---

## 🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|:------|:---------|
| "GROQ_API_KEY not found" | Ensure `.env` file exists in project root with valid key |
| "Manim command not found" | Run `pip install manim` in activated venv |
| "FFmpeg not found" | Install FFmpeg and add to system PATH |
| Video not generating | Check backend terminal for Manim error messages |
| Port 8000 already in use | Kill existing process or use `--port 8001` |
| Frontend can't connect | Ensure backend is running on port 8000 |
| Clerk "Invalid publishable key" | Check `frontend/.env.local` has correct keys |
| 404 after sign-up | Remove `NEXT_PUBLIC_CLERK_SIGN_IN_URL` and `NEXT_PUBLIC_CLERK_SIGN_UP_URL` from `.env.local` |
| S3 upload fails | Verify `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `S3_BUCKET_NAME` in `.env` |
| CloudFront 403 Forbidden | Ensure key group is attached to distribution behavior with \"Restrict viewer access: Yes\" |
| Signed URL not working | Verify `CLOUDFRONT_KEY_PAIR_ID` matches the public key ID in CloudFront |
| \"Missing Key\" error | Ensure `private_key.pem` exists at path specified in `CLOUDFRONT_PRIVATE_KEY_PATH` |
| Video plays locally but not CloudFront | Check S3 bucket policy allows CloudFront access (OAC) |
| ❌ MongoDB connection failed | Check `MONGODB_URI` has no trailing whitespace, verify credentials are correct |
| "ModuleNotFoundError: bson" | Run `pip install pymongo` (bson comes with pymongo, not standalone) |
| Chat history not saving | Ensure `MONGODB_URI` and `MONGODB_DATABASE` are set in `.env` |
| History sidebar empty | Verify user is signed in (chats are linked to Clerk user ID) |

### Debug Commands

```bash
# Check if Manim is installed correctly
manim --version

# Test Manim rendering
manim -pql -o test test_scene.py

# Check Python environment
pip list | grep manim
pip list | grep langchain

# Verify API key is set (Linux/Mac)
echo $GROQ_API_KEY

# Verify API key is set (Windows)
echo %GROQ_API_KEY%

# Check frontend environment
cat frontend/.env.local
```

---

## 🔐 Authentication

Manimancer uses [Clerk](https://clerk.com) for authentication with a **modal-based** flow (no separate pages).

### Components Used

| Component | Location | Purpose |
|:----------|:---------|:--------|
| `ClerkProvider` | `app/layout.tsx` | Wraps app with auth context |
| `clerkMiddleware` | `middleware.ts` | Route protection |
| `SignInButton` | `Sidebar.tsx` | Opens sign-in modal |
| `SignUpButton` | `Sidebar.tsx` | Opens sign-up modal |
| `UserButton` | `Sidebar.tsx` | User avatar + menu |
| `SignedIn` / `SignedOut` | `Sidebar.tsx` | Conditional rendering |

### Authentication Flow

1. **Signed Out:** Sidebar footer shows "Sign In" (orange) and "Sign Up" buttons
2. **Click Sign In/Up:** Clerk modal appears (no page redirect)
3. **After Auth:** Modal closes, user redirected to `/`
4. **Signed In:** Sidebar footer shows Upgrade button + user avatar

---

## 💎 Pricing Plans

Manimancer offers three pricing tiers with usage-based limits stored in MongoDB.

### Tier Comparison

| Feature | Free ($0) | Basic ($3) | Pro ($20/mo) |
|:--------|:----------|:-----------|:-------------|
| **Videos** | 5/month | 5 one-time credits | 50/month |
| **Reset** | 1st of each month | Never (one-time) | 30 days from purchase |
| **720p 30fps** | ✅ | ✅ (1 credit) | ✅ (1 credit) |
| **1080p 60fps** | 🔒 Locked | ✅ (1 credit) | ✅ (1 credit) |
| **4K 60fps** | 🔒 Locked | ✅ (2.5 credits) | ✅ (1 credit) |
| **Max Length** | 1 minute | 5 minutes | 5 minutes |

### Plan Details

#### Free Tier
- **5 videos per month** (resets on the 1st)
- **720p @ 30fps only** (1080p and 4K locked)
- Maximum 1 minute per video
- No credit card required

#### Basic Tier ($3 one-time)
- **5 video credits** (never expire)
- Access to **all resolutions** (720p, 1080p, 4K)
- **4K costs 2.5 credits** per video
- Credits are consumed before free monthly limit
- Up to 5 minutes per video
- One-time purchase, no subscription

#### Pro Tier ($20/month subscription)
- **50 videos per month**
- Resets **30 days from purchase date** (not 1st of month)
- **All resolutions at 1 credit each** (including 4K)
- Up to 5 minutes per video
- Priority rendering
- **Upgrade button hides** when Pro is active

### Usage Tracking System

All usage data is stored in MongoDB with the following schema:

```json
{
  "clerk_id": "user_abc123",
  "tier": "pro",
  "basic_credits": 0,
  "monthly_count": 3,
  "month_reset_date": "2026-01-12T00:00:00Z",
  "created_at": "2025-12-13T00:00:00Z",
  "updated_at": "2025-12-13T00:30:00Z"
}
```

### Credit Consumption Priority

When a user generates a video, credits are consumed in this order:

1. **Basic credits** (if available) → decremented first
2. **Monthly count** → only if no basic credits remain

### API Endpoints

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/usage/{clerk_id}` | GET | Get user's current tier and remaining credits |
| `/webhook/payment` | POST | Handle Dodo Payments webhook events |

### Webhook Events Handled

| Event | Action |
|:------|:-------|
| `payment_succeeded` | Add 5 Basic credits |
| `subscription_active` | Set tier to Pro, reset count to 0 |
| `subscription_cancelled` | Downgrade to Free tier |

### Frontend Visual Indicators

The sidebar shows different states based on user tier:

| Tier | Indicator | Upgrade Button |
|:-----|:----------|:---------------|
| Free | `✨ 2/5 used` | Visible |
| Basic | `⚡ 3 credits` | Visible |
| Pro | `👑 Pro: 5/50` | **Hidden** |

### Dodo Payments Integration

#### Product IDs (Live)

| Product | Product ID |
|:--------|:-----------|
| Manimancer Basic | `pdt_your_basic_product_id` |
| Manimancer Pro | `pdt_your_pro_product_id` |

#### Environment Variables

```env
# frontend/.env.local
DODO_PAYMENTS_API_KEY=your_live_api_key
DODO_PAYMENTS_WEBHOOK_KEY=whsec_your_webhook_secret
DODO_PAYMENTS_RETURN_URL=https://your-domain.com/
DODO_PAYMENTS_ENVIRONMENT=live_mode

NEXT_PUBLIC_DODO_BASIC_PRODUCT_ID=pdt_your_basic_product_id
NEXT_PUBLIC_DODO_PRO_PRODUCT_ID=pdt_your_pro_product_id
```

#### Webhook Endpoint

Set this URL in your Dodo Payments dashboard:

```
https://your-domain.com/api/webhook/dodo
```

The webhook handler:
1. Receives events from Dodo Payments
2. Extracts `clerk_id` from payment metadata
3. Calls backend `/webhook/payment` to update user credits/tier
4. Returns 200 OK to confirm receipt

---

## 📝 License

This project is open-source and available under the [MIT License](LICENSE).

---

## 🚀 Recent Updates

### December 2024

| Update | Description |
|:-------|:------------|
| **🌊 DigitalOcean Deployment** | Production backend deployed on DigitalOcean App Platform (~$62/mo) |
| **🌐 Live at manimancer.fun** | Frontend deployed on Vercel with custom domain |
| **🖼️ OG Image** | Added Open Graph image for social media sharing |
| **🎬 Resolution Selector** | Choose 720p, 1080p, or 4K with tier-based restrictions and costs |
| **🐳 Docker Compose** | Full containerized deployment for local development |
| **💾 Data Persistence Docs** | Clear documentation on volume persistence and commands |
| **🧪 Testing Guide** | 8-step verification checklist for all components |
| **📊 Extended (5m)** | New 5-minute duration for university mini-lectures |
| **🔧 Cube.vertices Fix** | Fixed `Cube.vertices` error (use `get_vertices()` method) |
| **3Blue1Brown Style** | Enhanced prompt engineering for professional-quality animations |
| **Error Prevention** | Added 20+ API error prevention rules (Arrow3D, VGroup, Syntax errors) |
| **Off-Screen Prevention** | Stricter bounds checking (±5.5 x ±3.0) to keep all elements visible |
| **Overlap Prevention** | Rule: Never show text and diagrams simultaneously |
| **Suspense Boundary** | Fixed Vercel build error with `useSearchParams()` |

---

## 🙏 Acknowledgements

- [Manim Community](https://www.manim.community/) — The incredible animation engine
- [Groq](https://groq.com/) — Ultra-fast LLM inference
- [3Blue1Brown](https://www.3blue1brown.com/) — Inspiration for mathematical visualizations
- [Clerk](https://clerk.com/) — Developer-first authentication
- [Next.js](https://nextjs.org/) — React framework
- [TailwindCSS](https://tailwindcss.com/) — Styling framework

---

## 👤 Author

**Aafi Malek**

- GitHub: [@Aafimalek](https://github.com/Aafimalek)
- X/Twitter: [@aafimalek2032](https://x.com/aafimalek2032)

---

<p align="center">
  <strong>Made with ❤️ for the open-source community</strong>
</p>

<p align="center">
  <a href="https://github.com/Aafimalek/prompt_to_animate">⭐ Star this repo</a> •
  <a href="https://github.com/Aafimalek/prompt_to_animate/issues">🐛 Report Bug</a> •
  <a href="https://github.com/Aafimalek/prompt_to_animate/issues">✨ Request Feature</a>
</p>

