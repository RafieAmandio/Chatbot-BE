# Docker Deployment Guide

This guide explains how to deploy the Multi-Tenant RAG Chatbot Backend using Docker and Docker Compose.

## 📋 Prerequisites

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **OpenAI API Key**: Required for AI functionality
- **System Requirements**: 
  - Minimum 2GB RAM
  - 10GB free disk space
  - CPU with 2+ cores recommended

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd CS-Chatbot-BE

# Copy environment template
cp env.example .env

# Edit environment variables
nano .env  # or use your preferred editor
```

### 2. Configure Environment Variables

**Critical Configuration** (`.env` file):
```env
# REQUIRED: OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# REQUIRED: JWT Secret (generate with: openssl rand -hex 32)
SECRET_KEY=your_super_secure_secret_key_here_minimum_32_characters
```

### 3. Build and Run

```bash
# Build and start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Check health status
curl http://localhost:8000/health
```

### 4. Access the Application

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Admin Dashboard**: http://localhost:8000/admin (admin access required)

## 🐳 Docker Configuration Details

### Dockerfile Features

- **Multi-stage build** for optimized image size
- **Non-root user** for security
- **Health checks** for monitoring
- **Python 3.12** base image
- **Production-ready** configuration

### Docker Compose Services

#### Main Application (`chatbot-backend`)
- **Port**: 8000
- **Volumes**: Persistent data storage
- **Health checks**: Automatic monitoring
- **Resource limits**: Memory and CPU constraints

#### Nginx Reverse Proxy (`nginx`) - Optional
- **Ports**: 80 (HTTP), 443 (HTTPS)
- **Features**: SSL termination, rate limiting, compression
- **Usage**: `docker-compose --profile production up`

## 📁 Volume Management

### Persistent Volumes
```yaml
volumes:
  chatbot_data:/app/data          # ChromaDB vector storage
  chatbot_uploads:/app/uploads    # File uploads
  chatbot_logs:/app/logs          # Application logs
```

### Volume Commands
```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect cs-chatbot-be_chatbot_data

# Backup data
docker run --rm -v cs-chatbot-be_chatbot_data:/data -v $(pwd):/backup alpine tar czf /backup/chatbot_data_backup.tar.gz -C /data .

# Restore data
docker run --rm -v cs-chatbot-be_chatbot_data:/data -v $(pwd):/backup alpine tar xzf /backup/chatbot_data_backup.tar.gz -C /data
```

## 🔧 Deployment Scenarios

### Development Deployment
```bash
# Basic development setup
docker-compose up -d

# With hot reload (requires code mounting)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Production Deployment
```bash
# Production with nginx reverse proxy
docker-compose --profile production up -d

# Production with SSL (requires certificates)
# 1. Place SSL certificates in ./ssl/ directory
# 2. Update nginx.conf server_name
# 3. Enable HTTPS redirect in nginx.conf
docker-compose --profile production up -d
```

### Scaling Deployment
```bash
# Scale backend instances
docker-compose up -d --scale chatbot-backend=3

# Use with load balancer
docker-compose -f docker-compose.yml -f docker-compose.scale.yml up -d
```

## 🛠️ Configuration Options

### Environment Variables

#### Application Settings
```env
APP_NAME="Multi-Tenant RAG Chatbot"
APP_VERSION="1.0.0"
APP_ENV=production
DEBUG=false
PORT=8000
```

#### Database Configuration
```env
# SQLite (default)
DATABASE_URL=sqlite:///./chatbot.db

# PostgreSQL (for production)
DATABASE_URL=postgresql://username:password@db:5432/chatbot_db
```

#### File Upload Settings
```env
MAX_UPLOAD_SIZE=52428800  # 50MB
UPLOAD_DIR=./uploads
MAX_FILES_PER_UPLOAD=20
```

#### Rate Limiting
```env
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
RATE_LIMIT_ADMIN_REQUESTS=200
```

### Resource Limits

#### Memory and CPU (docker-compose.yml)
```yaml
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '1.0'
    reservations:
      memory: 512M
      cpus: '0.5'
```

## 🔒 Security Configuration

### SSL/TLS Setup

1. **Generate SSL certificates**:
```bash
# Self-signed (development only)
mkdir ssl
openssl req -x509 -newkey rsa:4096 -nodes -out ssl/cert.pem -keyout ssl/key.pem -days 365

# Let's Encrypt (production)
docker run --rm -it -v $(pwd)/ssl:/etc/letsencrypt certbot/certbot certonly --standalone -d yourdomain.com
```

2. **Update nginx configuration**:
```nginx
server_name yourdomain.com;
ssl_certificate /etc/nginx/ssl/cert.pem;
ssl_certificate_key /etc/nginx/ssl/key.pem;
```

### Security Headers

The nginx configuration includes:
- **HSTS**: HTTP Strict Transport Security
- **CSP**: Content Security Policy
- **XSS Protection**: Cross-site scripting prevention
- **Frame Options**: Clickjacking protection

## 📊 Monitoring and Maintenance

### Health Checks
```bash
# Application health
curl http://localhost:8000/health

# Detailed system health (admin required)
curl -H "Authorization: Bearer <admin_token>" http://localhost:8000/admin/health

# Container health
docker-compose ps
```

### Logs Management
```bash
# View all logs
docker-compose logs

# Follow specific service logs
docker-compose logs -f chatbot-backend

# View nginx logs
docker-compose logs nginx

# Container resource usage
docker stats
```

### Backup Procedures
```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker run --rm -v cs-chatbot-be_chatbot_data:/data -v $(pwd):/backup alpine tar czf /backup/backup_$DATE.tar.gz -C /data .
docker cp $(docker-compose ps -q chatbot-backend):/app/chatbot.db ./backup_db_$DATE.db
echo "Backup completed: backup_$DATE.tar.gz, backup_db_$DATE.db"
EOF

chmod +x backup.sh
```

## 🚨 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000
# or
netstat -tulpn | grep 8000

# Stop existing process
docker-compose down
```

#### Permission Issues
```bash
# Fix volume permissions
docker-compose exec chatbot-backend chown -R appuser:appuser /app/data /app/uploads
```

#### Memory Issues
```bash
# Increase memory limits in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G  # Increase from 2G
```

#### Database Connection Issues
```bash
# Check database file permissions
docker-compose exec chatbot-backend ls -la chatbot.db

# Recreate database
docker-compose exec chatbot-backend rm chatbot.db
docker-compose restart chatbot-backend
```

### Debug Mode

Enable debug logging:
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

Access container shell:
```bash
docker-compose exec chatbot-backend bash
```

## 🔄 Updates and Maintenance

### Update Application
```bash
# Pull latest changes
git pull origin main

# Rebuild containers
docker-compose build --no-cache

# Restart services
docker-compose up -d
```

### Database Migrations
```bash
# Run migrations (if implemented)
docker-compose exec chatbot-backend python -m alembic upgrade head
```

### Clean Up
```bash
# Remove unused images
docker image prune -f

# Remove unused volumes
docker volume prune -f

# Complete cleanup
docker system prune -af
```

## 📈 Performance Optimization

### Production Optimizations

1. **Use PostgreSQL** instead of SQLite
2. **Enable Redis caching** for session storage
3. **Configure CDN** for static file delivery
4. **Implement load balancing** with multiple instances
5. **Use external vector database** for large deployments

### Resource Monitoring
```bash
# Monitor container resources
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

# Monitor disk usage
docker system df
```

## 🌐 Production Deployment Checklist

- [ ] Set strong `SECRET_KEY`
- [ ] Configure production database (PostgreSQL)
- [ ] Set up SSL certificates
- [ ] Configure domain name in nginx
- [ ] Set up monitoring and alerting
- [ ] Configure backup procedures
- [ ] Set appropriate resource limits
- [ ] Enable logging to external service
- [ ] Configure firewall rules
- [ ] Set up health check monitoring

## 📞 Support

For deployment issues:
1. Check logs: `docker-compose logs`
2. Verify environment variables
3. Check port availability
4. Verify Docker/Docker Compose versions
5. Review resource usage

**Useful Commands Reference**:
```bash
# Quick status check
docker-compose ps && curl -s http://localhost:8000/health

# Complete restart
docker-compose down && docker-compose up -d

# View resource usage
docker stats --no-stream
```

---

*Last Updated: December 2024*  
*Docker Version: 20.10+*  
*Docker Compose Version: 2.0+* 