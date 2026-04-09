# GhostProtocol Production Deployment Guide

This guide covers deploying GhostProtocol to production with all necessary security and operational considerations.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Database Setup](#database-setup)
4. [Backend Deployment](#backend-deployment)
5. [Frontend Deployment](#frontend-deployment)
6. [Security Configuration](#security-configuration)
7. [Monitoring & Logging](#monitoring--logging)
8. [Backup & Recovery](#backup--recovery)
9. [Scaling Considerations](#scaling-considerations)

---

## Prerequisites

### Required Services

- **AWS Account** with appropriate permissions
- **Supabase Project** (or PostgreSQL database)
- **LLM Provider**: Ollama (self-hosted) OR OpenAI/Anthropic API keys
- **Domain Name** (for HTTPS)
- **SSL Certificate** (Let's Encrypt recommended)

### Required Tools

```bash
# Terraform
terraform --version  # >= 1.0

# AWS CLI
aws --version  # >= 2.0

# Docker (for containerized deployment)
docker --version  # >= 20.10

# Node.js (for frontend)
node --version  # >= 20.0

# Python (for backend)
python --version  # >= 3.12
```

---

## Infrastructure Setup

### 1. Configure Terraform Variables

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
aws_region = "us-east-1"
project_name = "ghostprotocol"
environment = "prod"

# Use unique bucket names
cloudtrail_bucket_name = "ghostprotocol-cloudtrail-prod-YOUR-ORG"
athena_results_bucket_name = "ghostprotocol-athena-results-prod-YOUR-ORG"

enable_cloudtrail = true
cloudtrail_retention_days = 90

tags = {
  Project     = "GhostProtocol"
  Environment = "Production"
  ManagedBy   = "Terraform"
  Owner       = "SecurityTeam"
}
```

### 2. Deploy AWS Infrastructure

```bash
# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply configuration
terraform apply

# Save outputs
terraform output > ../outputs.txt
```

### 3. Verify Infrastructure

```bash
# Check CloudTrail is logging
aws cloudtrail get-trail-status --name ghostprotocol-trail-prod

# Verify Athena database
aws athena list-databases --catalog-name AwsDataCatalog

# Test IAM role
aws sts assume-role --role-arn <app_role_arn> --role-session-name test
```

---

## Database Setup

### 1. Create Supabase Project

1. Go to [https://supabase.com](https://supabase.com)
2. Create a new project
3. Note your project URL and service role key

### 2. Run Database Migrations

```bash
cd backend

# Option 1: Using Supabase Dashboard
# - Copy contents of migrations/001_initial_schema.sql
# - Paste into SQL Editor
# - Execute

# Option 2: Using migration script
python migrate.py
```

### 3. Verify Database

```sql
-- In Supabase SQL Editor
SELECT * FROM identities LIMIT 1;
SELECT * FROM schema_migrations;
```

---

## Backend Deployment

### Option A: Docker Deployment (Recommended)

#### 1. Build Docker Image

```bash
cd backend
docker build -t ghostprotocol-backend:latest .
```

#### 2. Configure Environment

Create `backend/.env.prod`:

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# AWS (use IAM role in production, not keys)
AWS_DEFAULT_REGION=us-east-1

# Athena (from Terraform outputs)
ATHENA_DATABASE=ghostprotocol_cloudtrail_prod
ATHENA_OUTPUT_BUCKET=s3://ghostprotocol-athena-results-prod-YOUR-ORG/results/

# LLM Provider
LLM_PROVIDER=ollama  # or openai, anthropic
OLLAMA_BASE_URL=http://ollama:11434
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

# Security
ENVIRONMENT=production
GHOSTPROTOCOL_API_KEY=$(python generate_api_key.py | grep "GHOSTPROTOCOL_API_KEY=" | cut -d= -f2)

# CORS
CORS_ORIGINS=https://your-domain.com

# Logging
LOG_LEVEL=INFO
```

#### 3. Run Container

```bash
docker run -d \
  --name ghostprotocol-backend \
  --env-file .env.prod \
  -p 8000:8000 \
  --restart unless-stopped \
  ghostprotocol-backend:latest
```

#### 4. Set Up Reverse Proxy (Nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/api.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Option B: EC2 Deployment

#### 1. Launch EC2 Instance

```bash
# Use the instance profile created by Terraform
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --iam-instance-profile Name=ghostprotocol-app-profile-prod \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxx \
  --subnet-id subnet-xxxxx \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ghostprotocol-backend-prod}]'
```

#### 2. Install Dependencies

```bash
ssh ec2-user@your-instance

# Install Python
sudo yum install python3.12 python3.12-pip -y

# Install application
git clone https://github.com/your-org/ghostprotocol.git
cd ghostprotocol/backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. Configure Systemd Service

```bash
sudo nano /etc/systemd/system/ghostprotocol.service
```

```ini
[Unit]
Description=GhostProtocol Backend
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/ghostprotocol/backend
Environment="PATH=/home/ec2-user/ghostprotocol/backend/venv/bin"
EnvironmentFile=/home/ec2-user/ghostprotocol/backend/.env.prod
ExecStart=/home/ec2-user/ghostprotocol/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ghostprotocol
sudo systemctl start ghostprotocol
```

---

## Frontend Deployment

### Option A: Vercel (Recommended)

#### 1. Connect Repository

1. Go to [https://vercel.com](https://vercel.com)
2. Import your GitHub repository
3. Select `frontend` as root directory

#### 2. Configure Environment Variables

In Vercel dashboard:

```
NEXT_PUBLIC_API_URL=https://api.your-domain.com
NEXT_PUBLIC_API_KEY=your-api-key
```

#### 3. Deploy

```bash
# Vercel will auto-deploy on git push
git push origin main
```

### Option B: Docker + Nginx

#### 1. Build Frontend

```bash
cd frontend
docker build -t ghostprotocol-frontend:latest .
```

#### 2. Run Container

```bash
docker run -d \
  --name ghostprotocol-frontend \
  -e NEXT_PUBLIC_API_URL=https://api.your-domain.com \
  -e NEXT_PUBLIC_API_KEY=your-api-key \
  -p 3000:3000 \
  --restart unless-stopped \
  ghostprotocol-frontend:latest
```

#### 3. Configure Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Security Configuration

### 1. Generate Strong API Key

```bash
cd backend
python generate_api_key.py
```

Add to `.env.prod` and frontend environment variables.

### 2. Configure HTTPS

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com -d api.your-domain.com
```

### 3. Set Up Firewall

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP (redirect to HTTPS)
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### 4. Enable AWS CloudTrail Encryption

```bash
aws cloudtrail update-trail \
  --name ghostprotocol-trail-prod \
  --kms-key-id alias/cloudtrail-key
```

---

## Monitoring & Logging

### 1. Health Check Monitoring

```bash
# Set up cron job for health checks
crontab -e
```

```cron
*/5 * * * * curl -f https://api.your-domain.com/health || echo "Health check failed" | mail -s "GhostProtocol Alert" admin@your-domain.com
```

### 2. Application Logs

```bash
# View backend logs
docker logs -f ghostprotocol-backend

# Or with systemd
sudo journalctl -u ghostprotocol -f
```

### 3. AWS CloudWatch (Optional)

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb
```

---

## Backup & Recovery

### 1. Database Backups

Supabase provides automatic backups. For additional safety:

```bash
# Manual backup
pg_dump -h db.your-project.supabase.co -U postgres -d postgres > backup.sql
```

### 2. Configuration Backups

```bash
# Backup Terraform state
aws s3 cp terraform.tfstate s3://your-backup-bucket/terraform/

# Backup environment files (encrypted)
gpg -c .env.prod
aws s3 cp .env.prod.gpg s3://your-backup-bucket/config/
```

---

## Scaling Considerations

### Horizontal Scaling

```bash
# Run multiple backend instances behind load balancer
docker-compose up --scale backend=3
```

### Database Scaling

- Enable Supabase connection pooling
- Consider read replicas for heavy read workloads

### Caching

```bash
# Add Redis for caching
docker run -d --name redis -p 6379:6379 redis:alpine
```

---

## Post-Deployment Checklist

- [ ] All infrastructure provisioned via Terraform
- [ ] Database migrations applied
- [ ] API key authentication enabled
- [ ] HTTPS configured with valid certificates
- [ ] Health checks passing
- [ ] Logs being collected
- [ ] Backups configured
- [ ] Monitoring alerts set up
- [ ] Documentation updated
- [ ] Team trained on operations

---

## Troubleshooting

### Backend Won't Start

```bash
# Check logs
docker logs ghostprotocol-backend

# Verify environment
docker exec ghostprotocol-backend env | grep SUPABASE

# Test health endpoint
curl https://api.your-domain.com/health/detailed
```

### Frontend Can't Connect to Backend

```bash
# Check CORS settings
curl -H "Origin: https://your-domain.com" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS https://api.your-domain.com/health

# Verify API key
curl -H "X-API-Key: your-key" https://api.your-domain.com/identities
```

### AWS Permissions Issues

```bash
# Test IAM permissions
aws iam list-roles --max-items 1
aws athena start-query-execution --query-string "SHOW DATABASES" \
  --result-configuration OutputLocation=s3://your-bucket/
```

---

## Support

For production issues:
1. Check logs first
2. Review health check endpoint: `/health/detailed`
3. Consult [README.md](../README.md) for configuration
4. Open GitHub issue with logs and error details
