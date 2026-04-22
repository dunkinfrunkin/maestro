---
sidebar_position: 1
title: Okta
---

# Okta

## Setup

1. In **Okta Admin**, go to Applications > Create App Integration
2. Select **OIDC - OpenID Connect** and **Web Application**
3. Set the redirect URI to your Maestro instance:
   ```
   http://localhost:3000/auth/callback
   ```
   For production, use your actual domain:
   ```
   https://maestro.yourcompany.com/auth/callback
   ```
4. Under Assignments, assign the users or groups who should have access

## Configuration

```yaml
# config.yaml
auth:
  secret: "your-jwt-secret"  # openssl rand -hex 32
  oidc_issuer: "https://yourcompany.okta.com/oauth2/default"
  oidc_client_id: "0oaxxxxxxxxxxxxxxxx"
  oidc_client_secret: "your-client-secret"
```

Or via environment variables:

```bash
MAESTRO_SECRET=your-jwt-secret
MAESTRO_OIDC_ISSUER=https://yourcompany.okta.com/oauth2/default
MAESTRO_OIDC_CLIENT_ID=0oaxxxxxxxxxxxxxxxx
MAESTRO_OIDC_CLIENT_SECRET=your-client-secret
```

Or via Docker:

```bash
docker run -d --name maestro \
  -p 3000:3000 \
  -e MAESTRO_SECRET=$(openssl rand -hex 32) \
  -e MAESTRO_OIDC_ISSUER=https://yourcompany.okta.com/oauth2/default \
  -e MAESTRO_OIDC_CLIENT_ID=0oaxxxxxxxxxxxxxxxx \
  -e MAESTRO_OIDC_CLIENT_SECRET=your-client-secret \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  ghcr.io/dunkinfrunkin/maestro:latest
```

## Finding your issuer URL

The issuer URL is your Okta domain plus the authorization server path. For the default authorization server:

```
https://yourcompany.okta.com/oauth2/default
```

If you're using a custom authorization server, replace `default` with your server ID.

You can verify by visiting `https://yourcompany.okta.com/oauth2/default/.well-known/openid-configuration` in a browser - it should return a JSON discovery document.
