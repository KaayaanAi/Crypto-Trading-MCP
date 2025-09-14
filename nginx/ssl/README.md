# SSL Certificate Setup

This directory should contain your SSL certificates for HTTPS termination.

## Required Files

- `cert.pem` - Your SSL certificate (or certificate chain)
- `key.pem` - Your private key

## For Development/Testing

You can create self-signed certificates for testing:

```bash
# Generate a private key
openssl genrsa -out key.pem 2048

# Generate a self-signed certificate (valid for 365 days)
openssl req -new -x509 -key key.pem -out cert.pem -days 365 \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

## For Production

Use certificates from a trusted Certificate Authority (CA) such as:
- Let's Encrypt (free)
- Commercial SSL providers
- Internal CA (for private networks)

## Security Notes

- Keep your private key (`key.pem`) secure and never commit it to version control
- Ensure proper file permissions:
  ```bash
  chmod 600 key.pem
  chmod 644 cert.pem
  ```
- Regularly rotate certificates before expiration