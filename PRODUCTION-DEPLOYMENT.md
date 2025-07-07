# SelfDB Production Deployment Guide

## Overview

This guide walks you through deploying SelfDB in a production environment with enterprise-grade security and automated CI/CD deployment. The process ensures your self-hosted Firebase alternative runs reliably and securely on your own infrastructure.

## Prerequisites

- **Purchased SelfDB license** with the source code zip file
- **Linux server** (we recommend Ubuntu 20.04/22.04 LTS)
- **Domain name** pointing to your server
- **GitHub account** for private repository and CI/CD
- **Basic Linux/Docker knowledge**

## Recommended Infrastructure

- **Hosting Provider**: [Hetzner Cloud](https://www.hetzner.com/cloud) (excellent price/performance)
- **Server Specs**: Minimum 2 vCPU, 4GB RAM, 40GB SSD
- **OS**: Ubuntu 22.04 LTS
- **Region**: Choose based on your primary user base

## Step 1: Create Private Git Repository

1. **Extract your SelfDB purchase**:
   ```bash
   unzip selfdb-purchase.zip
   cd selfdb
   ```

2. **Create a new private GitHub repository**:
   - Go to https://github.com/new
   - Name: `selfdb-production` (or your preference)
   - Visibility: **Private** (important!)
   - Do NOT initialize with README

3. **Push SelfDB to your private repo**:
   ```bash
   git init
   git add .
   git commit -m "Initial SelfDB deployment"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/selfdb-production.git
   git push -u origin main
   ```

## Step 2: Prepare Your Server

### 2.1 Provision Your Server

1. **Create a new VPS on Hetzner** (or your provider):
   - Choose Ubuntu 22.04 LTS
   - Select appropriate resources
   - Note your server's IP address

2. **Initial SSH connection**:
   ```bash
   ssh root@YOUR_SERVER_IP
   ```

### 2.2 Security Hardening with prepare-vps Script

⚠️ **IMPORTANT**: Never deploy production applications as root user!

We've created an automated script that:
- Creates a secure non-root user
- Hardens SSH configuration
- Installs Docker and Docker Compose
- Sets up Portainer and Nginx Proxy Manager

1. **Clone and run the preparation script**:
   ```bash
   # On your server as root
   git clone https://github.com/Selfdb-io/prepare-vps.git
   cd prepare-vps
   chmod +x preparevps.sh
   ./preparevps.sh
   ```

2. **Follow the prompts**:
   - Enter your desired username (e.g., `selfdb`)
   - Set a strong password
   - **SAVE THE SSH PRIVATE KEY** displayed - this is your only access!

3. **Save your SSH key locally**:
   ```bash
   # On your local machine
   nano ~/.ssh/selfdb-server-key
   # Paste the private key
   chmod 600 ~/.ssh/selfdb-server-key
   ```

4. **Test new secure connection**:
   ```bash
   ssh -i ~/.ssh/selfdb-server-key YOUR_USERNAME@YOUR_SERVER_IP
   ```

5. **Start Docker services**:
   ```bash
   cd ~/docker-services
   docker-compose up -d
   ```

## Step 2.5: Configure Docker Network

The prepare-vps script creates an external Docker network called `selfdb_selfdb` that connects your SelfDB services to Nginx Proxy Manager. This is essential for the proxy to route traffic to your containers.

### Verify the Network Exists

```bash
# Check if the external network was created
docker network ls | grep selfdb_selfdb
```

You should see output like:
```
abc123def456   selfdb_selfdb   bridge    local
```

### If the Network is Missing

If the network doesn't exist (rare case), create it manually:

```bash
docker network create selfdb_selfdb
```

### Why This Network is Important

- **Isolation**: Keeps your SelfDB services on a separate network
- **Security**: Only exposes services through the proxy
- **Communication**: Allows Nginx Proxy Manager to reach your containers
- **Flexibility**: Easy to add more services to the same network

**Note**: Your SelfDB `docker-compose.yml` file already includes this external network configuration for all services that need public access (Frontend, Backend API, and Storage Service).

## Step 3: Configure Domain and SSL

### 3.1 Access Nginx Proxy Manager

1. **Open Nginx Proxy Manager**:
   - Navigate to: `http://YOUR_SERVER_IP:81`
   - Default login: `admin@example.com` / `changeme`
   - **Change these credentials immediately!**

### 3.2 Configure SSL Certificates

1. **Add SSL Certificates for all domains**:
   - Go to "SSL Certificates" → "Add SSL Certificate"
   - Choose "Let's Encrypt"
   - Add all your domains:
     - `selfdb.yourdomain.com` (Frontend)
     - `api.yourdomain.com` (Backend API)
     - `storage.yourdomain.com` (Storage Service)
   - Email: your-email@example.com
   - Enable "Force SSL"
   - Agree to Let's Encrypt Terms
   - Test with staging first, then request real certificate

### 3.3 Configure Proxy Hosts

You need to create three proxy hosts for the different SelfDB services:

#### 3.3.1 Frontend Proxy Host

1. Go to "Proxy Hosts" → "Add Proxy Host"
2. Configure as follows:
   - **Domain Names**: `selfdb.yourdomain.com`
   - **Scheme**: `http`
   - **Forward Hostname/IP**: `YOUR_SERVER_IP`
   - **Forward Port**: `3000`
   - **Cache Assets**: ✓
   - **Block Common Exploits**: ✓
   - **Websockets Support**: ✓ (Important for real-time updates)

3. SSL Tab:
   - **SSL Certificate**: Select your Let's Encrypt certificate
   - **Force SSL**: ✓
   - **HTTP/2 Support**: ✓
   - **HSTS Enabled**: ✓
   - **HSTS Subdomains**: ✓

#### 3.3.2 Backend API Proxy Host

1. Go to "Proxy Hosts" → "Add Proxy Host"
2. Configure as follows:
   - **Domain Names**: `api.yourdomain.com`
   - **Scheme**: `http`
   - **Forward Hostname/IP**: `YOUR_SERVER_IP`
   - **Forward Port**: `8000`
   - **Block Common Exploits**: ✓
   - **Websockets Support**: ✓ (Critical for real-time features)

3. SSL Tab:
   - **SSL Certificate**: Select your Let's Encrypt certificate
   - **Force SSL**: ✓
   - **HTTP/2 Support**: ✓

4. Advanced Tab (for WebSocket support):
   ```nginx
   # WebSocket support
   proxy_set_header Upgrade $http_upgrade;
   proxy_set_header Connection "upgrade";
   
   # Increase timeouts for long-running connections
   proxy_read_timeout 86400;
   proxy_send_timeout 86400;
   
   # Required headers
   proxy_set_header Host $host;
   proxy_set_header X-Real-IP $remote_addr;
   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   proxy_set_header X-Forwarded-Proto $scheme;
   ```

#### 3.3.3 Storage Service Proxy Host

1. Go to "Proxy Hosts" → "Add Proxy Host"
2. Configure as follows:
   - **Domain Names**: `storage.yourdomain.com`
   - **Scheme**: `http`
   - **Forward Hostname/IP**: `YOUR_SERVER_IP`
   - **Forward Port**: `8001`
   - **Block Common Exploits**: ✓

3. SSL Tab:
   - **SSL Certificate**: Select your Let's Encrypt certificate
   - **Force SSL**: ✓
   - **HTTP/2 Support**: ✓

4. Advanced Tab (for large file uploads):
   ```nginx
   # Increase client max body size for file uploads
   client_max_body_size 5000M;
   
   # Increase timeouts for large file transfers
   proxy_read_timeout 3600;
   proxy_send_timeout 3600;
   proxy_connect_timeout 3600;
   
   # Buffer settings for large files
   proxy_buffering off;
   proxy_request_buffering off;
   ```

## Step 3.5: Configure Environment Variables

Before starting SelfDB, you need to properly configure your environment variables for production use.

### Create Production Environment File

1. **SSH into your server**:
   ```bash
   ssh -i ~/.ssh/selfdb-server-key YOUR_USERNAME@YOUR_SERVER_IP
   ```

2. **Navigate to SelfDB directory** (after initial deployment):
   ```bash
   cd /home/selfdb
   ```

3. **Copy the example environment file**:
   ```bash
   cp .env.example .env
   ```

4. **Edit the .env file**:
   ```bash
   nano .env
   ```

### Essential Environment Variables to Configure

Update the following variables with your production values:

```env
# PostgreSQL Configuration
POSTGRES_DB=selfdb_production
POSTGRES_USER=selfdb_prod_user
POSTGRES_PASSWORD=your_strong_postgres_password_here
DATABASE_URL=postgresql+asyncpg://selfdb_prod_user:your_strong_postgres_password_here@postgres:5432/selfdb_production

# Storage Service Configuration
STORAGE_SERVICE_URL=http://storage_service:8001
STORAGE_SERVICE_EXTERNAL_URL=https://storage.yourdomain.com
STORAGE_PATH=/data/storage

# Backend API Configuration
SECRET_KEY=your_super_secret_jwt_key_at_least_32_bytes_long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
API_PORT=8000

# Frontend Configuration
FRONTEND_PORT=3000

# Public API URL (used by frontend)
REACT_APP_API_URL=https://api.yourdomain.com/api/v1

# Default Admin Credentials (CHANGE THESE!)
DEFAULT_ADMIN_EMAIL=admin@yourdomain.com
DEFAULT_ADMIN_PASSWORD=your_very_strong_admin_password

# Cloud Functions Configuration
FUNCTIONS_DIR=/functions

# Anonymous API Key (auto-generated by start.sh)
ANON_KEY=

# CORS Configuration
CORS_ALLOWED_ORIGINS=https://selfdb.yourdomain.com,https://api.yourdomain.com,https://storage.yourdomain.com

# Storage Service API Key (auto-generated by start.sh)
STORAGE_SERVICE_API_KEY=
```

### Important Security Notes

1. **Generate Strong Secrets**:
   ```bash
   # Generate a secure SECRET_KEY
   openssl rand -hex 32
   
   # Generate strong passwords
   openssl rand -base64 32
   ```

2. **Never commit .env to Git**:
   - Ensure `.env` is in your `.gitignore`
   - Store production secrets securely (e.g., password manager)

3. **After First Start**:
   - The `start.sh` script will auto-generate `ANON_KEY` and `STORAGE_SERVICE_API_KEY`
   - Note these values for client applications

### Verify Configuration

After configuring, verify your setup:

```bash
# Check environment file syntax
cat .env | grep -E "^[A-Z_]+=.*"

# Ensure no example values remain
grep -E "(example\.com|changeme|adminpassword)" .env
```

If the second command returns any results, update those values!

## Step 4: Setup GitHub Actions CI/CD

### 4.1 Configure Repository Secrets

In your GitHub repository, go to Settings → Secrets → Actions and add:

- `IP`: Your server's IP address
- `USER`: Your non-root username (from Step 2)
- `PRIVATEKEY`: Your SSH private key content
- `PASSWORD`: Your user's sudo password

### 4.2 Create GitHub Actions Workflow

Create `.github/workflows/deploy.yml` in your repository:

```yaml
name: Deploy SelfDB to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Prepare target directory on server
        uses: appleboy/ssh-action@v1.2.2
        with:
          host: ${{ secrets.IP }}
          username: ${{ secrets.USER }}
          key: ${{ secrets.PRIVATEKEY }}
          password: ${{ secrets.PASSWORD }}
          script: |
            # Create selfdb directory if it doesn't exist
            echo "${{ secrets.PASSWORD }}" | sudo -S mkdir -p /home/selfdb
            
            # Set proper ownership and permissions
            echo "${{ secrets.PASSWORD }}" | sudo -S chown -R $USER:$USER /home/selfdb
            echo "${{ secrets.PASSWORD }}" | sudo -S chmod -R 755 /home/selfdb

      - name: Copy source code to server
        uses: appleboy/scp-action@v0.1.7
        with:
          host: ${{ secrets.IP }}
          username: ${{ secrets.USER }}
          key: ${{ secrets.PRIVATEKEY }}
          password: ${{ secrets.PASSWORD }}
          source: "."
          target: "/home/selfdb/"
          overwrite: true

      - name: Build and deploy SelfDB
        uses: appleboy/ssh-action@v1.2.2
        with:
          host: ${{ secrets.IP }}
          username: ${{ secrets.USER }}
          key: ${{ secrets.PRIVATEKEY }}
          password: ${{ secrets.PASSWORD }}
          script: |
            # Navigate to project directory
            cd /home/selfdb/
            
            # Make start script executable
            chmod +x start.sh
            
            # Run startup script
            ./start.sh
```

### 4.3 Benefits of CI/CD Pipeline

- **Automated deployments** on every push to main
- **Version control** for all configuration changes
- **Rollback capability** through Git history
- **Team collaboration** with proper code review
- **Audit trail** of all deployments

## Step 5: Deploy and Start SelfDB

### 5.1 Initial Deployment

After configuring your environment variables, perform the initial deployment:

1. **Push your configured repository**:
   ```bash
   git add .
   git commit -m "Configure production environment"
   git push origin main
   ```

2. **GitHub Actions will automatically**:
   - Copy files to your server
   - Run the `start.sh` script
   - Start all SelfDB services

3. **Monitor the deployment**:
   - Check GitHub Actions tab in your repository
   - View real-time logs of the deployment process

### 5.2 Verify Services are Running

SSH into your server and check service status:

```bash
# Check all containers are running
docker ps

# You should see:
# - selfdb_postgres
# - selfdb_storage_service
# - selfdb_backend
# - selfdb_frontend
# - selfdb_deno

# Check logs if needed
docker logs selfdb_backend
docker logs selfdb_frontend
```

### 5.3 Access Your SelfDB Instance

1. **Admin Dashboard**: https://selfdb.yourdomain.com
   - Login with the credentials from your .env file
   - Change the default admin password immediately

2. **API Documentation**: https://api.yourdomain.com/docs
   - Interactive API documentation (FastAPI)
   - Test endpoints directly

3. **Storage Service Health**: https://storage.yourdomain.com/health
   - Should return `{"status":"healthy"}`

## Step 6: Post-Deployment Configuration

### 6.1 Anonymous API Key

After first deployment, retrieve your generated keys:

```bash
# On your server
cd /home/selfdb
grep "ANON_KEY\|STORAGE_SERVICE_API_KEY" .env
```

Save these values - you'll need the `ANON_KEY` for client applications.

### 6.2 Security Hardening

1. **Configure Firewall**:
   ```bash
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw allow 81/tcp    # Nginx Proxy Manager
   sudo ufw allow 9000/tcp  # Portainer
   sudo ufw enable
   ```

2. **Set up Fail2ban** (optional but recommended):
   ```bash
   sudo apt install fail2ban
   sudo systemctl enable fail2ban
   sudo systemctl start fail2ban
   ```

### 6.3 Data Persistence and Backups

SelfDB uses Docker named volumes for data persistence:

- `postgres_data`: Database files
- `selfdb_files`: Storage service files
- `functions_data`: Cloud function code

**Backup Strategy**:

```bash
# Create backup script
nano ~/backup-selfdb.sh
```

Add the following:

```bash
#!/bin/bash
BACKUP_DIR="/home/$USER/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec selfdb_postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# Backup storage files
docker run --rm -v selfdb_files:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/storage_$DATE.tar.gz /data

# Backup functions
docker run --rm -v functions_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/functions_$DATE.tar.gz /data

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

Make it executable and add to cron:

```bash
chmod +x ~/backup-selfdb.sh
crontab -e
# Add: 0 2 * * * /home/YOUR_USER/backup-selfdb.sh
```

## Monitoring and Maintenance

### Using Portainer

Access at `http://YOUR_SERVER_IP:9000` to:
- Monitor container health
- View logs in real-time
- Manage Docker resources
- Update container images

### Recommended Monitoring Stack

```yaml
# Add to your docker-compose.yml
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus:/etc/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=secure_password
```

## Troubleshooting

### Common Issues

1. **SSH Connection Refused**
   ```bash
   # Check if SSH service is running
   sudo systemctl status ssh
   # Check firewall rules
   sudo ufw status
   ```

2. **Docker Permission Denied**
   ```bash
   # Ensure user is in docker group
   sudo usermod -aG docker $USER
   # Logout and login again
   ```

3. **SSL Certificate Issues**
   - Verify DNS is pointing to your server
   - Check Nginx Proxy Manager logs
   - Try Let's Encrypt staging first

4. **Deployment Failures**
   - Check GitHub Actions logs
   - Verify all secrets are set correctly
   - Test SSH connection manually

5. **External Network Issues**
   ```bash
   # Check if selfdb_selfdb network exists
   docker network ls | grep selfdb_selfdb
   
   # If missing, create it
   docker network create selfdb_selfdb
   
   # Restart SelfDB services
   cd /home/selfdb
   docker-compose down
   docker-compose up -d
   ```

6. **Services Not Accessible**
   - Verify proxy hosts are configured correctly
   - Check container logs: `docker logs <container_name>`
   - Ensure firewall allows required ports
   - Test internal connectivity: `curl http://localhost:3000`

7. **WebSocket Connection Issues**
   - Ensure "Websockets Support" is enabled in proxy hosts
   - Check Advanced configuration for proper headers
   - Verify CORS_ALLOWED_ORIGINS includes all your domains

8. **Database Connection Errors**
   ```bash
   # Check PostgreSQL is running
   docker exec selfdb_postgres pg_isready
   
   # Verify DATABASE_URL matches your PostgreSQL credentials
   grep DATABASE_URL /home/selfdb/.env
   ```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        User Access (HTTPS/SSL)                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │
│  │ selfdb.domain   │  │ api.domain      │  │ storage.domain  │       │
│  │ (Frontend)      │  │ (Backend API)   │  │ (Storage API)   │       │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘       │
└───────────┼────────────────────┼────────────────────┼─────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Nginx Proxy Manager (Docker Network)                  │
│                         External Network: selfdb_selfdb                  │
└─────────────────────────────────────────────────────────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        SelfDB Services (Dockerized)                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │
│  │ Frontend        │  │ Backend API     │  │ Storage Service │       │
│  │ (React)         │  │ (FastAPI)       │  │ (File Storage)  │       │
│  │ Port: 3000      │  │ Port: 8000      │  │ Port: 8001      │       │
│  └─────────────────┘  └────────┬────────┘  └────────┬────────┘       │
│                               │                      │                  │
│                               ▼                      ▼                  │
│  ┌─────────────────────────────────────────────────────────────┐      │
│  │               Internal Services (Not Exposed)                │      │
│  │  ┌─────────────────┐        ┌─────────────────┐            │      │
│  │  │ PostgreSQL      │        │ Deno Runtime    │            │      │
│  │  │ (Database)      │        │ (Cloud Functions)│            │      │
│  │  │ Port: 5432      │        │ Port: 8090      │            │      │
│  │  └─────────────────┘        └─────────────────┘            │      │
│  └─────────────────────────────────────────────────────────────┘      │
│                                                                         │
│  ┌─────────────────┐                                                  │
│  │ Portainer       │  Docker Management UI (Port: 9000)               │
│  └─────────────────┘                                                  │
└─────────────────────────────────────────────────────────────────────────┘

Data Persistence: Docker Named Volumes
- postgres_data: PostgreSQL database files
- selfdb_files: Storage service files
- functions_data: Cloud functions code
```

## Next Steps

1. **Performance Tuning**: Optimize based on your workload
2. **Backup Strategy**: Implement automated backups
3. **Monitoring**: Set up alerts for critical metrics
4. **Scaling**: Consider horizontal scaling with Docker Swarm/K8s
5. **Security Audits**: Regular penetration testing

## Support

- **Documentation**: Check the SelfDB docs in your purchase
- **Community**: Join our Discord server
- **Issues**: Report bugs in your private repository
- **Updates**: Pull latest changes from upstream

---

Remember: With great power comes great responsibility. You now control your entire backend infrastructure - make sure to keep it secure and updated!