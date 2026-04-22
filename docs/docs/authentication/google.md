---
sidebar_position: 2
title: Google
---

# Google

## Setup

1. Go to [Google Cloud Console > APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
2. Click **Create Credentials > OAuth client ID**
3. Select **Web application**
4. Add the redirect URI:
   ```
   http://localhost:3000/auth/callback
   ```
   For production:
   ```
   https://maestro.yourcompany.com/auth/callback
   ```
5. Note the **Client ID** and **Client Secret**

## Configuration

```yaml
# config.yaml
auth:
  secret: "your-jwt-secret"
  oidc_issuer: "https://accounts.google.com"
  oidc_client_id: "your-client-id.apps.googleusercontent.com"
  oidc_client_secret: "your-client-secret"
```

Or via environment variables:

```bash
MAESTRO_SECRET=your-jwt-secret
MAESTRO_OIDC_ISSUER=https://accounts.google.com
MAESTRO_OIDC_CLIENT_ID=your-client-id.apps.googleusercontent.com
MAESTRO_OIDC_CLIENT_SECRET=your-client-secret
```

## Notes

- The issuer is always `https://accounts.google.com` for Google Workspace and personal accounts
- Users are created on first login using the email from Google's OIDC claims
- To restrict access to your organization, configure the OAuth consent screen to "Internal" in Google Cloud Console
