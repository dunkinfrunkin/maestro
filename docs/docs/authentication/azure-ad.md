---
sidebar_position: 3
title: Azure AD
---

# Azure AD / Entra ID

## Setup

1. Go to [Azure Portal > App registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Click **New registration**
3. Set a name (e.g., "Maestro")
4. Under Redirect URI, select **Web** and enter:
   ```
   http://localhost:3000/auth/callback
   ```
   For production:
   ```
   https://maestro.yourcompany.com/auth/callback
   ```
5. After creation, go to **Certificates & secrets > New client secret** and note the value
6. Note the **Application (client) ID** from the Overview page
7. Note your **Directory (tenant) ID** from the Overview page

## Configuration

```yaml
# config.yaml
auth:
  secret: "your-jwt-secret"
  oidc_issuer: "https://login.microsoftonline.com/{tenant-id}/v2.0"
  oidc_client_id: "your-application-client-id"
  oidc_client_secret: "your-client-secret"
```

Replace `{tenant-id}` with your actual Azure AD tenant ID.

Or via environment variables:

```bash
MAESTRO_SECRET=your-jwt-secret
MAESTRO_OIDC_ISSUER=https://login.microsoftonline.com/{tenant-id}/v2.0
MAESTRO_OIDC_CLIENT_ID=your-application-client-id
MAESTRO_OIDC_CLIENT_SECRET=your-client-secret
```

## Notes

- The issuer URL must include `/v2.0` at the end
- Replace `{tenant-id}` with your actual tenant ID (a UUID)
- To restrict to your organization only, ensure the app registration is set to "Single tenant"
- Users are created on first login using the email from Azure AD's OIDC claims
