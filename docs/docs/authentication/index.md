---
sidebar_position: 8
title: Authentication
sidebar_label: Authentication
---

# Authentication

Maestro supports single sign-on via any OpenID Connect (OIDC) provider. Users authenticate through your existing identity provider - Maestro never stores passwords. Sessions are managed with JWT tokens in HTTP-only cookies.

## How it works

1. User visits the Maestro dashboard and clicks "Sign in"
2. Maestro redirects to your OIDC provider's authorization endpoint
3. User authenticates with the provider (Okta, Google, Azure AD, etc.)
4. Provider redirects back to Maestro with an authorization code
5. Maestro exchanges the code for tokens using PKCE (Proof Key for Code Exchange)
6. Maestro creates a local user record (on first login) and issues a JWT
7. JWT is stored in an HTTP-only cookie with a 30-day lifetime

No refresh tokens are used. After 30 days, users re-authenticate through the OIDC flow.

## Supported providers

Maestro works with any OIDC-compliant provider. The following have been tested:

| Provider | What you need |
|---|---|
| [Okta](okta) | Okta Admin access to create an App Integration |
| [Google](google) | Google Cloud Console access to create OAuth credentials |
| [Azure AD](azure-ad) | Azure portal access to register an application |
| [Disabled](disabled) | No auth (development only) |

## Required configuration

All auth configuration can be set via environment variables, config.yaml, or Docker:

| Setting | Required | Description |
|---|---|---|
| `MAESTRO_SECRET` | Yes | JWT signing secret. Generate with `openssl rand -hex 32` |
| `MAESTRO_OIDC_ISSUER` | For SSO | OIDC provider discovery URL |
| `MAESTRO_OIDC_CLIENT_ID` | For SSO | OAuth client ID from your provider |
| `MAESTRO_OIDC_CLIENT_SECRET` | For SSO | OAuth client secret from your provider |
| `MAESTRO_AUTH_DISABLED` | No | Set `true` to skip auth entirely |

## Security details

- JWTs are signed with HMAC-SHA256 using `MAESTRO_SECRET`
- Tokens are stored in HTTP-only cookies (not accessible to JavaScript)
- PKCE flow prevents authorization code interception
- User records are created on first login (email from OIDC claims)
- All API routes require authentication except `/auth/*` and `GET /`
