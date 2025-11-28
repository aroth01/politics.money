# Security Fixes - Implementation Guide

## Quick Start (5 Minutes)

### Step 1: Install python-decouple

```bash
pip install python-decouple
echo "python-decouple>=3.8" >> requirements.txt
```

### Step 2: Generate a New SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 3: Create .env File

```bash
cp .env.example .env
```

Then edit `.env` and add your new SECRET_KEY:
```
SECRET_KEY=<paste-the-key-from-step-2>
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Step 4: Update settings.py

Add at the top of `polstats_project/settings.py`:

```python
from decouple import config, Csv

# Replace this:
SECRET_KEY = 'django-insecure-change-this-in-production-12345'

# With this:
SECRET_KEY = config('SECRET_KEY')

# Replace this:
DEBUG = True

# With this:
DEBUG = config('DEBUG', default=False, cast=bool)

# Replace this:
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# With this:
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
```

### Step 5: Verify .gitignore

The `.gitignore` file has been created. Verify it exists:

```bash
cat .gitignore | grep ".env"
```

## Production Security Settings

Add these to the bottom of `polstats_project/settings.py`:

```python
# Security settings for production
if not DEBUG:
    # HTTPS/SSL
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # HSTS
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Additional security
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

    # Use PostgreSQL in production
    DATABASES = {
        'default': {
            'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }
```

## Logging Configuration

Add to `settings.py`:

```python
# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Create logs directory
import os
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
```

## Rate Limiting Enhancement

Update `.env`:
```
RATELIMIT_ENABLE=True
RATELIMIT_RATE=100/h
```

Add to `settings.py`:
```python
RATELIMIT_ENABLE = config('RATELIMIT_ENABLE', default=True, cast=bool)
```

## Admin Security

### 1. Change Admin URL

In `polstats_project/urls.py`, change:
```python
path('admin/', admin.site.urls),
```

To:
```python
path(config('ADMIN_URL', default='admin') + '/', admin.site.urls),
```

Then in `.env`:
```
ADMIN_URL=secret-admin-path-xyz123
```

### 2. Strong Admin Password

```bash
python manage.py changepassword admin
```

Use a password with:
- At least 12 characters
- Mix of uppercase, lowercase, numbers, symbols

## Database Backups (Production)

Create a backup script `scripts/backup_db.sh`:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/polstats"
mkdir -p $BACKUP_DIR

# PostgreSQL backup
pg_dump -U $DB_USER -h $DB_HOST $DB_NAME | gzip > $BACKUP_DIR/polstats_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: polstats_$DATE.sql.gz"
```

Add to crontab (daily at 2 AM):
```bash
0 2 * * * /path/to/scripts/backup_db.sh
```

## Content Security Policy

Install django-csp:
```bash
pip install django-csp
echo "django-csp>=3.7" >> requirements.txt
```

Add to `MIDDLEWARE` in settings.py:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'csp.middleware.CSPMiddleware',  # Add this
    # ... rest of middleware
]
```

Add CSP settings:
```python
# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "https://d3js.org", "https://cdn.jsdelivr.net")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")  # DaisyUI needs inline styles
CSP_IMG_SRC = ("'self'", "data:")
CSP_FONT_SRC = ("'self'",)
```

## Error Monitoring (Optional)

Install Sentry:
```bash
pip install sentry-sdk
echo "sentry-sdk>=1.38.0" >> requirements.txt
```

Add to settings.py:
```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

if not DEBUG:
    sentry_sdk.init(
        dsn=config('SENTRY_DSN', default=''),
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
```

## Pre-Deployment Checklist

Run Django's security check:
```bash
python manage.py check --deploy
```

This will identify any remaining security issues.

## Testing

### Test Environment Variables

```bash
python manage.py shell
>>> from django.conf import settings
>>> print(settings.SECRET_KEY[:10])  # Should not be 'django-ins'
>>> print(settings.DEBUG)  # Should be False in production
```

### Test HTTPS Redirect

In production with HTTPS:
```bash
curl -I http://yourdomain.com
# Should return 301 or 302 redirect to https://
```

### Test Admin URL

```bash
# Old URL should return 404
curl http://yourdomain.com/admin/
# New URL should return login page
curl http://yourdomain.com/secret-admin-path-xyz123/
```

## Regular Maintenance

### Monthly Tasks
- [ ] Update Django: `pip install --upgrade Django`
- [ ] Update all dependencies: `pip list --outdated`
- [ ] Review security logs
- [ ] Test backups

### Quarterly Tasks
- [ ] Review ALLOWED_HOSTS
- [ ] Audit admin users
- [ ] Review rate limiting effectiveness
- [ ] Security audit

## Emergency Response

If you suspect a security breach:

1. **Immediately**:
   - Change SECRET_KEY
   - Rotate database passwords
   - Review access logs
   - Disable compromised accounts

2. **Investigation**:
   - Check logs for suspicious activity
   - Review recent database changes
   - Identify attack vector

3. **Recovery**:
   - Restore from backup if needed
   - Patch vulnerability
   - Update documentation
   - Notify users if data was exposed

## Resources

- Django Security: https://docs.djangoproject.com/en/stable/topics/security/
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Mozilla Security Headers: https://infosec.mozilla.org/guidelines/web_security
