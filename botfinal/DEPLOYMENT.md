# SALESBOT Training System - Deployment Guide

## Overview

This guide helps you deploy the SALESBOT Training System in various environments.

## Prerequisites

- Python 3.10 or higher
- pip package manager
- (Optional) Telegram account and bot token for Telegram integration

## Quick Start

### 1. Installation

```bash
cd botfinal
pip install -r requirements.txt
```

### 2. Start Backend

```bash
./start_backend.sh
```

Or directly:
```bash
python main.py
```

The backend will be available at `http://localhost:8080`

### 3. Access API Documentation

Open your browser and navigate to:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

### 4. (Optional) Start Telegram Bot

First, set your bot token:
```bash
export TELEGRAM_BOT_TOKEN="your-bot-token-here"
```

Then start the bot:
```bash
./start_bot.sh
```

Or directly:
```bash
python simple_telegram_bot.py
```

## Environment Variables

### Backend Configuration

- `BACKEND_BASE_URL` - Base URL for the backend (default: `http://127.0.0.1:8080`)
  - Used for internal API calls and URL generation
  - Example: `export BACKEND_BASE_URL="https://api.yourdomain.com"`

### Telegram Bot Configuration

- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token (required for bot)
  - Get from [@BotFather](https://t.me/botfather)
  - Example: `export TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"`

- `BACKEND_URL` - Backend URL for the bot to connect to (default: `http://127.0.0.1:8080`)
  - Example: `export BACKEND_URL="https://api.yourdomain.com"`

## Production Deployment

### Using systemd (Linux)

1. Create a systemd service file for the backend:

```ini
# /etc/systemd/system/salesbot-backend.service
[Unit]
Description=SALESBOT Training System Backend
After=network.target

[Service]
Type=simple
User=salesbot
WorkingDirectory=/opt/salesbot/botfinal
Environment="BACKEND_BASE_URL=https://api.yourdomain.com"
ExecStart=/usr/bin/python3 /opt/salesbot/botfinal/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Create a systemd service file for the Telegram bot:

```ini
# /etc/systemd/system/salesbot-bot.service
[Unit]
Description=SALESBOT Training System Telegram Bot
After=network.target salesbot-backend.service

[Service]
Type=simple
User=salesbot
WorkingDirectory=/opt/salesbot/botfinal
Environment="TELEGRAM_BOT_TOKEN=your-token"
Environment="BACKEND_URL=https://api.yourdomain.com"
ExecStart=/usr/bin/python3 /opt/salesbot/botfinal/simple_telegram_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Enable and start services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable salesbot-backend
sudo systemctl enable salesbot-bot
sudo systemctl start salesbot-backend
sudo systemctl start salesbot-bot
```

4. Check status:

```bash
sudo systemctl status salesbot-backend
sudo systemctl status salesbot-bot
```

### Using Docker

1. Create a Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "main.py"]
```

2. Build and run:

```bash
docker build -t salesbot-backend .
docker run -d \
  --name salesbot-backend \
  -p 8080:8080 \
  -e BACKEND_BASE_URL="http://localhost:8080" \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/academy_progress.db:/app/academy_progress.db \
  salesbot-backend
```

3. For the Telegram bot:

```bash
docker run -d \
  --name salesbot-bot \
  --link salesbot-backend \
  -e TELEGRAM_BOT_TOKEN="your-token" \
  -e BACKEND_URL="http://salesbot-backend:8080" \
  salesbot-backend \
  python simple_telegram_bot.py
```

### Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8080:8080"
    environment:
      - BACKEND_BASE_URL=http://localhost:8080
    volumes:
      - ./data:/app/data
      - ./academy_progress.db:/app/academy_progress.db
    restart: unless-stopped

  telegram-bot:
    build: .
    depends_on:
      - backend
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - BACKEND_URL=http://backend:8080
    command: python simple_telegram_bot.py
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

### Behind a Reverse Proxy (nginx)

Example nginx configuration:

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

For HTTPS (recommended):
```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Database Management

### SQLite Database

The system uses SQLite for progress tracking. The database file is created automatically at:
```
botfinal/academy_progress.db
```

### Backup

Regular backups are recommended:

```bash
# Create backup
cp academy_progress.db academy_progress.db.backup.$(date +%Y%m%d_%H%M%S)

# Restore from backup
cp academy_progress.db.backup.20251123_120000 academy_progress.db
```

### Migration to PostgreSQL (Optional)

For high-traffic deployments, consider migrating to PostgreSQL:

1. Install PostgreSQL adapter:
```bash
pip install psycopg2-binary
```

2. Update `progress_repository.py` to use PostgreSQL connection string
3. Migrate existing data using a migration tool

## Monitoring

### Logs

- Backend logs: Check stdout/stderr or systemd journal
- Bot logs: Check stdout/stderr or systemd journal

Example with systemd:
```bash
journalctl -u salesbot-backend -f
journalctl -u salesbot-bot -f
```

### Health Checks

- Backend: `curl http://localhost:8080/api/public/v1/health`
- Academy Module: `curl http://localhost:8080/academy/v1/health`

### Metrics

Consider adding monitoring tools like:
- Prometheus for metrics collection
- Grafana for visualization
- Sentry for error tracking

## Scaling Considerations

### Horizontal Scaling

To run multiple backend instances:

1. Use a load balancer (nginx, HAProxy, AWS ALB)
2. Share the database (use PostgreSQL instead of SQLite)
3. Use a shared file system for audio cache or object storage (S3, MinIO)

### Performance Optimization

- Enable caching for module data
- Use CDN for audio files
- Optimize database queries
- Enable gzip compression in reverse proxy

## Security Best Practices

1. **API Security**
   - Add authentication middleware
   - Use HTTPS in production
   - Implement rate limiting
   - Validate all inputs

2. **Database Security**
   - Restrict database file permissions
   - Regular backups
   - Use encrypted connections for PostgreSQL

3. **Bot Security**
   - Keep bot token secret
   - Validate user inputs
   - Implement user authentication
   - Monitor for abuse

4. **System Security**
   - Keep dependencies updated
   - Use security scanning tools
   - Implement proper logging
   - Regular security audits

## Troubleshooting

### Backend won't start

1. Check Python version: `python --version`
2. Verify dependencies: `pip install -r requirements.txt`
3. Check port availability: `lsof -i :8080`
4. Review logs for errors

### Bot can't connect to backend

1. Verify backend is running: `curl http://localhost:8080/api/public/v1/health`
2. Check `BACKEND_URL` environment variable
3. Verify network connectivity
4. Check firewall rules

### TTS not working

1. Verify internet connectivity (gTTS requires internet)
2. Check for network restrictions
3. Verify audio cache directory permissions
4. Consider alternative TTS solutions for offline use

### Database errors

1. Check file permissions
2. Verify disk space
3. Check for database locks
4. Review database logs

## Support

For issues or questions:
- Check the documentation: README.md, EXAMPLES.md
- Review logs for error messages
- Contact system administrator

## Updates

To update the system:

1. Pull latest changes
2. Update dependencies: `pip install -r requirements.txt --upgrade`
3. Restart services
4. Verify health checks

```bash
git pull
pip install -r requirements.txt --upgrade
sudo systemctl restart salesbot-backend
sudo systemctl restart salesbot-bot
```
