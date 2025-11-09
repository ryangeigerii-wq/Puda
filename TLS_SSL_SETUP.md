# TLS/SSL Configuration Guide

This guide explains how to configure TLS/SSL encryption for the Dashboard API in production environments.

## Table of Contents

1. [Overview](#overview)
2. [Option 1: Flask with SSL Context (Development/Testing)](#option-1-flask-with-ssl-context-developmenttesting)
3. [Option 2: Nginx Reverse Proxy (Recommended for Production)](#option-2-nginx-reverse-proxy-recommended-for-production)
4. [Option 3: Docker with Let's Encrypt](#option-3-docker-with-lets-encrypt)
5. [Certificate Management](#certificate-management)
6. [Production Deployment Checklist](#production-deployment-checklist)

---

## Overview

**Why HTTPS is Critical:**
- **Authentication Security**: Session tokens transmitted over HTTP can be intercepted
- **Data Privacy**: User credentials, PII detection results, and document metadata need encryption
- **Compliance**: Many regulations (HIPAA, GDPR, PCI-DSS) require encrypted transmission
- **Browser Security**: Modern browsers flag HTTP sites as "Not Secure"

**Recommended Approach:**
- **Development**: Flask with self-signed certificates (Option 1)
- **Production**: Nginx reverse proxy with Let's Encrypt (Option 2)
- **Cloud/Container**: Docker with automated certificate renewal (Option 3)

---

## Option 1: Flask with SSL Context (Development/Testing)

**Use Case**: Local testing, development environments, internal networks

### Step 1: Generate Self-Signed Certificates

```bash
# Using OpenSSL (included with Git Bash on Windows)
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout key.pem -out cert.pem \
  -days 365 -subj "/CN=localhost"

# Move certificates to secure location
mkdir -p data/certs
mv key.pem cert.pem data/certs/
chmod 600 data/certs/key.pem
```

### Step 2: Update `dashboard_api.py`

```python
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Routing Dashboard API')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--audit-dir', default='data')
    parser.add_argument('--ssl-cert', default='data/certs/cert.pem', 
                        help='Path to SSL certificate')
    parser.add_argument('--ssl-key', default='data/certs/key.pem', 
                        help='Path to SSL private key')
    parser.add_argument('--enable-ssl', action='store_true',
                        help='Enable HTTPS with SSL context')
    args = parser.parse_args()
    
    # Initialize components
    global AUDIT_DIR
    AUDIT_DIR = Path(args.audit_dir)
    init_qc_modules()
    init_organization_modules()
    init_authorization_modules()
    
    # Start server
    if args.enable_ssl:
        import ssl
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(args.ssl_cert, args.ssl_key)
        app.run(host='0.0.0.0', port=args.port, ssl_context=context, debug=False)
    else:
        app.run(host='0.0.0.0', port=args.port, debug=False)
```

### Step 3: Run with HTTPS

```bash
# PowerShell
python dashboard_api.py --port 8443 --enable-ssl

# Access at: https://localhost:8443
```

**Note**: Browsers will show a security warning for self-signed certificates. This is expected for development.

---

## Option 2: Nginx Reverse Proxy (Recommended for Production)

**Use Case**: Production deployments, public-facing servers, multiple services

### Architecture

```
[Client Browser] 
    ↓ HTTPS (port 443)
[Nginx Reverse Proxy] 
    ↓ HTTP (localhost:8080)
[Flask Dashboard API]
```

### Step 1: Install Nginx

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx

# Windows
# Download from: https://nginx.org/en/download.html
```

### Step 2: Obtain SSL Certificate with Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate (replaces yourdomain.com with actual domain)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Certificates will be stored at:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

### Step 3: Configure Nginx

Create `/etc/nginx/sites-available/dashboard-api`:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL certificates from Let's Encrypt
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL configuration (Mozilla Intermediate - compatible with most browsers)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # HSTS (HTTP Strict Transport Security) - 1 year
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Logging
    access_log /var/log/nginx/dashboard-access.log;
    error_log /var/log/nginx/dashboard-error.log;
    
    # Static files
    location /static/ {
        alias /path/to/Puda/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # API proxy
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        
        # WebSocket support (if needed in future)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Rate limiting (additional layer)
        limit_req zone=api_limit burst=10 nodelay;
    }
    
    # Health check endpoint (no rate limit)
    location /api/health {
        proxy_pass http://127.0.0.1:8080/api/health;
        proxy_set_header Host $host;
        access_log off;
    }
}

# Rate limiting zones (add to /etc/nginx/nginx.conf http block)
# limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
```

### Step 4: Enable Configuration

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/dashboard-api /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Enable auto-start
sudo systemctl enable nginx
```

### Step 5: Start Flask API (HTTP only, behind Nginx)

```bash
# Flask runs on HTTP localhost:8080 (not exposed publicly)
python dashboard_api.py --port 8080 --audit-dir /path/to/data

# Or use systemd service (recommended)
sudo systemctl start dashboard-api
```

---

## Option 3: Docker with Let's Encrypt

**Use Case**: Containerized deployments, cloud environments, auto-scaling

### Step 1: Create Docker Compose with Certbot

Update `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # Flask Dashboard API
  dashboard-api:
    build: .
    container_name: puda-dashboard-api
    restart: unless-stopped
    volumes:
      - ./data:/app/data
    ports:
      - "127.0.0.1:8080:8080"  # Only exposed to localhost
    environment:
      - AUDIT_DIR=/app/data
    networks:
      - puda-network
  
  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: puda-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./static:/app/static:ro
      - certbot-etc:/etc/letsencrypt
      - certbot-var:/var/lib/letsencrypt
    depends_on:
      - dashboard-api
    networks:
      - puda-network
  
  # Certbot for SSL certificate management
  certbot:
    image: certbot/certbot
    container_name: puda-certbot
    volumes:
      - certbot-etc:/etc/letsencrypt
      - certbot-var:/var/lib/letsencrypt
      - ./certbot/www:/var/www/certbot
    command: >-
      certonly --webroot --webroot-path=/var/www/certbot
      --email admin@yourdomain.com --agree-tos --no-eff-email
      -d yourdomain.com -d www.yourdomain.com
    networks:
      - puda-network

volumes:
  certbot-etc:
  certbot-var:

networks:
  puda-network:
    driver: bridge
```

### Step 2: Create Nginx Configuration for Docker

Create `nginx/conf.d/dashboard.conf`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # ACME challenge for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL configuration (same as Option 2)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers off;
    
    location / {
        proxy_pass http://dashboard-api:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

### Step 3: Deploy with Docker Compose

```bash
# First run: obtain certificates
docker-compose up certbot

# Start all services
docker-compose up -d dashboard-api nginx

# Verify certificates
docker-compose exec certbot certbot certificates
```

### Step 4: Automate Certificate Renewal

Create `certbot-renew.sh`:

```bash
#!/bin/bash
docker-compose run --rm certbot renew
docker-compose exec nginx nginx -s reload
```

Add to crontab:

```bash
# Renew certificates every 12 hours
0 */12 * * * /path/to/certbot-renew.sh >> /var/log/certbot-renew.log 2>&1
```

---

## Certificate Management

### Certificate Renewal (Let's Encrypt)

Let's Encrypt certificates expire after 90 days. Automate renewal:

```bash
# Test renewal process (dry run)
sudo certbot renew --dry-run

# Manual renewal
sudo certbot renew

# Reload Nginx after renewal
sudo systemctl reload nginx

# Check expiration dates
sudo certbot certificates
```

### Certificate Monitoring

Set up monitoring to alert before expiration:

```bash
# Check expiration script
#!/bin/bash
DAYS_UNTIL_EXPIRY=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/yourdomain.com/cert.pem \
  | awk -F= '{print $2}' | xargs -I {} date -d "{}" +%s | \
  awk -v now=$(date +%s) '{print int(($1 - now) / 86400)}')

if [ $DAYS_UNTIL_EXPIRY -lt 30 ]; then
  echo "WARNING: SSL certificate expires in $DAYS_UNTIL_EXPIRY days"
  # Send alert (email, Slack, etc.)
fi
```

### Custom Certificates (Non-Let's Encrypt)

If using purchased certificates or internal CA:

```bash
# Update Nginx configuration
ssl_certificate /path/to/custom/fullchain.pem;
ssl_certificate_key /path/to/custom/privkey.pem;
ssl_trusted_certificate /path/to/custom/chain.pem;  # For OCSP stapling
```

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] **Domain Name**: DNS records point to server IP
- [ ] **Firewall Rules**: 
  - Allow ports 80 (HTTP) and 443 (HTTPS)
  - Block port 8080 (Flask) from public access
- [ ] **SSL Certificates**: Obtained and installed correctly
- [ ] **Nginx Configuration**: Tested with `nginx -t`
- [ ] **Rate Limiting**: Configured in Nginx and Flask-Limiter
- [ ] **Security Headers**: HSTS, X-Frame-Options, CSP configured

### Flask API Security

- [ ] **Debug Mode Off**: `debug=False` in production
- [ ] **Secret Key**: Set `app.secret_key` to random value
- [ ] **Environment Variables**: Store sensitive config in environment
- [ ] **Authorization**: UserManager and PolicyEngine initialized
- [ ] **Audit Logging**: AuditLogger enabled and writable
- [ ] **Database Permissions**: Restrict access to data/users.db, data/audit_log.db

### Post-Deployment

- [ ] **HTTPS Redirect**: Verify HTTP → HTTPS redirect works
- [ ] **SSL Labs Test**: Check at https://www.ssllabs.com/ssltest/
- [ ] **Security Headers Test**: https://securityheaders.com/
- [ ] **Authentication Test**: Login with admin:admin, verify token
- [ ] **Rate Limiting Test**: Attempt 6+ logins in 1 minute → 429 error
- [ ] **Session Expiration**: Verify 24-hour token expiration
- [ ] **Audit Logs**: Check data/audit_log.db for login records
- [ ] **Certificate Auto-Renewal**: Test certbot renewal process
- [ ] **Monitoring Setup**: SSL expiration alerts, uptime monitoring

### Hardening Recommendations

1. **Change Default Credentials**: Replace admin:admin immediately
2. **Restrict User Creation**: Disable self-registration in production
3. **Enable WAF**: Use Cloudflare, AWS WAF, or ModSecurity
4. **Log Monitoring**: Send logs to centralized system (ELK, Splunk)
5. **Backup Strategy**: Regular backups of data/ directory
6. **Intrusion Detection**: Install fail2ban to block brute force
7. **CORS Policy**: Restrict allowed origins in Flask
8. **Content Security Policy**: Add CSP headers to prevent XSS

---

## Troubleshooting

### Common Issues

**1. Certificate not found error:**
```bash
# Check certificate paths
ls -l /etc/letsencrypt/live/yourdomain.com/

# Verify Nginx user has read access
sudo chmod 755 /etc/letsencrypt/live/
sudo chmod 755 /etc/letsencrypt/archive/
```

**2. Mixed content warnings (HTTP resources on HTTPS page):**
```javascript
// Update dashboard.html to use relative URLs
const API_BASE = window.location.origin;  // Already done!
```

**3. Nginx can't connect to Flask:**
```bash
# Check Flask is running
curl http://localhost:8080/api/health

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Verify proxy_pass URL in Nginx config
```

**4. SSL certificate expired:**
```bash
# Force renewal
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

**5. Rate limiting not working:**
```python
# Check Flask-Limiter initialization
# Verify limiter is not None in dashboard_api.py
print(f"Rate limiter enabled: {limiter is not None}")
```

---

## References

- **Mozilla SSL Configuration Generator**: https://ssl-config.mozilla.org/
- **Let's Encrypt Documentation**: https://letsencrypt.org/docs/
- **Nginx HTTPS Guide**: https://nginx.org/en/docs/http/configuring_https_servers.html
- **Flask-Limiter**: https://flask-limiter.readthedocs.io/
- **OWASP TLS Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html

---

## Summary

**For Development:**
```bash
# Quick setup with self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/CN=localhost"
python dashboard_api.py --port 8443 --enable-ssl --ssl-cert cert.pem --ssl-key key.pem
```

**For Production:**
```bash
# Recommended: Nginx + Let's Encrypt
sudo certbot --nginx -d yourdomain.com
sudo systemctl restart nginx
python dashboard_api.py --port 8080  # Behind Nginx, HTTP only
```

**Security Priority:**
1. ✅ Enable HTTPS (this guide)
2. ✅ Rate limiting (Flask-Limiter installed)
3. ✅ Authentication (UserManager active)
4. ⚠️ Change default credentials (admin:admin → secure password)
5. ⚠️ Enable audit logging monitoring
6. ⚠️ Regular security updates

---

**Questions? Issues?**
- Check audit logs: `sqlite3 data/audit_log.db "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 10;"`
- Test SSL: `curl -I https://yourdomain.com/api/health`
- Verify rate limiting: `for i in {1..6}; do curl -X POST https://yourdomain.com/api/auth/login -d '{"username":"test","password":"test"}'; done`
