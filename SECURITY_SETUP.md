# Security Setup Guide

This guide explains how to configure sensitive credentials and API keys for the ValueScan project.

## Overview

All sensitive information (passwords, API keys, tokens) must be configured via environment variables. **Never commit credentials to version control.**

## Required Environment Variables

### 1. Admin Authentication (REQUIRED)

The admin panel requires authentication credentials. These MUST be set before starting the application.

```bash
# Admin credentials (REQUIRED - no defaults provided)
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_secure_password

# Alternative names (for compatibility)
NOFX_ADMIN_USERNAME=your_admin_username
NOFX_ADMIN_PASSWORD=your_secure_password
```

**Important**: The application will fail to start if `ADMIN_PASSWORD` is not set.

### 2. JWT and Encryption Keys (REQUIRED)

```bash
# JWT signing secret (minimum 32 characters)
# Generate with: openssl rand -base64 32
JWT_SECRET=your-jwt-secret-here

# AES-256 data encryption key (Base64 encoded, 32 bytes)
# Used for encrypting sensitive data in database
# Generate with: openssl rand -base64 32
DATA_ENCRYPTION_KEY=your-base64-encoded-32-byte-key

# RSA private key for client-server encryption (PEM format)
# Generate with: openssl genrsa 2048
# Note: Replace newlines with \n for single-line format
RSA_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\nYOUR_KEY_HERE\n-----END RSA PRIVATE KEY-----
```

### 3. External API Keys (Optional)

Configure these based on which data sources you want to use:

```bash
# CoinMarketCap API Key
# Get from: https://coinmarketcap.com/api/
COINMARKETCAP_API_KEY=

# CryptoCompare API Key
# Get from: https://www.cryptocompare.com/cryptopian/api-keys
CRYPTOCOMPARE_API_KEY=

# CoinGecko API Key
# Get from: https://www.coingecko.com/en/api/pricing
COINGECKO_API_KEY=

# Etherscan API Key
# Get from: https://etherscan.io/myapikey
ETHERSCAN_API_KEY=

# FRED API Key (for macro data)
# Get from: https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY=

# GitHub Token (for project fundamentals)
# Get from: https://github.com/settings/tokens
GITHUB_TOKEN=
```

### 4. VPS Deployment (Optional)

If you're using the VPS deployment scripts:

```bash
# VPS SSH password
VPS_PASSWORD=your_vps_password
```

### 5. Telegram Notifications (Optional)

```bash
# Telegram Bot Token
# Get from: @BotFather on Telegram
TELEGRAM_BOT_TOKEN=

# Telegram Chat ID
# Get from: @userinfobot on Telegram
TELEGRAM_CHAT_ID=
```

## Setup Instructions

### Step 1: Copy Environment Template

```bash
cp .env.example .env
```

### Step 2: Generate Secure Keys

```bash
# Generate JWT secret
openssl rand -base64 32

# Generate data encryption key
openssl rand -base64 32

# Generate RSA private key
openssl genrsa 2048
```

### Step 3: Edit .env File

Open `.env` in a text editor and fill in the required values:

```bash
nano .env
# or
vim .env
# or use your preferred editor
```

### Step 4: Set Strong Admin Credentials

Choose a strong admin password:
- Minimum 12 characters
- Mix of uppercase, lowercase, numbers, and symbols
- Avoid common words or patterns

Example:
```bash
ADMIN_USERNAME=admin
ADMIN_PASSWORD=MyS3cur3P@ssw0rd!2026
```

### Step 5: Configure API Keys

Add API keys for the services you want to use. Leave unused services blank.

### Step 6: Verify Configuration

```bash
# Test that the application can start
python -m api.server
```

If you see an error about missing `ADMIN_PASSWORD`, the environment variable is not set correctly.

## Security Best Practices

### 1. Environment Variables

- **Never commit `.env` files** to version control
- Use `.env.example` as a template (with no real values)
- Keep `.env` file permissions restricted: `chmod 600 .env`

### 2. Password Security

- Use unique, strong passwords for each service
- Consider using a password manager
- Rotate credentials regularly
- Never share credentials via insecure channels

### 3. API Key Management

- Use separate API keys for development and production
- Set appropriate rate limits and restrictions on API keys
- Revoke unused or compromised keys immediately
- Monitor API key usage for anomalies

### 4. Production Deployment

For production environments:

```bash
# Use environment-specific secrets
ADMIN_PASSWORD=$(cat /run/secrets/admin_password)
JWT_SECRET=$(cat /run/secrets/jwt_secret)

# Or use a secrets management service
# - AWS Secrets Manager
# - HashiCorp Vault
# - Azure Key Vault
```

### 5. Docker Deployment

When using Docker, pass secrets via environment variables or Docker secrets:

```yaml
# docker-compose.yml
services:
  valuescan:
    environment:
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - JWT_SECRET=${JWT_SECRET}
    secrets:
      - admin_password
      - jwt_secret

secrets:
  admin_password:
    external: true
  jwt_secret:
    external: true
```

## Troubleshooting

### Application Won't Start

**Error**: `ValueError: ADMIN_PASSWORD environment variable must be set`

**Solution**: Set the `ADMIN_PASSWORD` environment variable in your `.env` file.

### Admin Login Fails

**Issue**: Cannot log in to admin panel

**Checklist**:
1. Verify `ADMIN_USERNAME` and `ADMIN_PASSWORD` are set correctly
2. Check that `.env` file is in the project root directory
3. Restart the application after changing `.env`
4. Clear browser cache and cookies

### API Keys Not Working

**Issue**: External API calls fail

**Checklist**:
1. Verify API keys are valid and not expired
2. Check API key permissions and rate limits
3. Ensure API keys are set in `.env` file
4. Restart the application after adding keys

## Migration from Hardcoded Credentials

If you're upgrading from an older version with hardcoded credentials:

### 1. Remove Hardcoded Values

The following hardcoded values have been removed:
- Admin password: `Qq159741` → Now requires `ADMIN_PASSWORD` env var
- API keys in `signal_monitor/config.example.py` → Now empty by default
- VPS passwords in deployment scripts → Now use `VPS_PASSWORD` env var

### 2. Update Configuration

```bash
# Set your new credentials
export ADMIN_PASSWORD="your_new_secure_password"
export VPS_PASSWORD="your_vps_password"

# Or add to .env file
echo "ADMIN_PASSWORD=your_new_secure_password" >> .env
echo "VPS_PASSWORD=your_vps_password" >> .env
```

### 3. Update Deployment Scripts

If you have custom deployment scripts, update them to use environment variables:

```python
import os

# Old (insecure)
password = 'Qq159741'

# New (secure)
password = os.environ.get('VPS_PASSWORD', '')
if not password:
    raise ValueError("VPS_PASSWORD environment variable must be set")
```

## Additional Resources

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [12-Factor App: Config](https://12factor.net/config)
- [Docker Secrets Documentation](https://docs.docker.com/engine/swarm/secrets/)

## Support

If you encounter issues with security configuration:

1. Check this documentation first
2. Review the `.env.example` file for required variables
3. Check application logs for specific error messages
4. Open an issue on GitHub with details (never include actual credentials)

---

**Remember**: Security is everyone's responsibility. Keep your credentials safe!
