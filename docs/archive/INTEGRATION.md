# Integrating a website with UCM

UCM currently provides a shared authentication API for websites under a trusted, same-site deployment. It is not an OAuth/OIDC provider. The included static sample shows browser access to UCM-protected data. The separate [FastAPI website example](../../examples/python-website/README.md) protects **its own backend route** by checking UCM's session on each request; neither example maintains a password store.

## Run the sample

1. Start UCM's backend on port 8000 and portal on port 3000.
2. From the repository root run `python -m http.server 3100 --directory examples/sample-site --bind 127.0.0.1`.
3. Open `http://localhost:3100` and click **Check access** while signed out. Access is denied.
4. Sign in through the UCM portal and click **Check access** again. Account notes open; remote and office notes remain locked.
5. Complete main-phone approval on the portal's **Login pipeline** page. Check the sample again: remote notes open. Once two workplace nodes have approved a fresh request in a verified office setup, office notes open too.
6. Sign out of UCM and verify that the sample loses access.

Use `localhost` consistently; `127.0.0.1` and `localhost` are different cookie hosts.

## API contract

| Action | Request | Authorization |
|---|---|---|
| Register | POST `/api/register` | JSON username, email, password |
| Sign in | POST `/api/login` | JSON username, password; sets HttpOnly cookie |
| Get account / CSRF token | GET `/api/me` | Session cookie |
| Password change | POST `/api/password-change` | Session cookie + `X-UCM-CSRF` + current password |
| List sessions | GET `/api/sessions` | Session cookie |
| Revoke session | DELETE `/api/sessions/{id}` | Session cookie + CSRF token; ownership enforced |
| Sign out | POST `/api/logout` | Session cookie + CSRF token |
| Android sign in | POST `/api/app/login` | Returns temporary opaque bearer token |
| Enroll recovery device | POST `/api/app/store-public-key` | Bearer token + current password |
| Request recovery challenge | GET `/api/app/get-reset-challenge?username=...` | No login required |
| Approve reset | POST `/api/app/verify-reset` | Device signature over challenge and new password digest |
| Start tiered request | POST `/api/trust/start` | Session cookie + CSRF token; returns fresh request ID |
| Check tier status | GET `/api/trust/status` | Session cookie |
| Remote resource | GET `/api/data/remote` | Session plus fresh main-phone approval |
| Office resource | GET `/api/data/office` | Remote approval plus two distinct workplace-node approvals; office flag enabled |

Browser requests use `credentials: 'include'`. For a state-changing cookie request, first obtain `data.csrf_token` from `/api/me`, then send it as `X-UCM-CSRF`. It is safe for JavaScript to read this CSRF token; the session credential remains HttpOnly.

The backend accepts only configured browser origins, checks Origin on writes, and refuses form-encoded credential requests. Add only trusted websites to `CORS_ALLOW_ORIGINS`; never use a wildcard with credentials. A CORS allowlist does not authenticate a user.

## Protecting real application data

The sample calls three backend routes with different authorization dependencies. Your own backend must apply the appropriate session and trust-level dependency before returning private data. Hiding a frontend page alone is not protection. The example proves shared authentication and tiered resource checks, not multitenancy or arbitrary third-party OAuth integration.

The Python website adapter forwards the same-host session cookie server-to-server to `/api/me`, then uses the authenticated username for its own route. It fails closed if UCM rejects the session or is unavailable. Its read-only example does not implement a general authorization model for another website's data or CSRF protection for that website's writes; those remain integration responsibilities.

## Production boundary

Host the portal, API, and integrating websites on trusted HTTPS origins with a compatible same-site cookie deployment. Set secure cookies and explicit origin allowlists. Unrelated domains require an additional protocol or backend-for-frontend design; do not copy session credentials into localStorage to bypass this boundary.
