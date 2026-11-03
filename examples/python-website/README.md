# A website that protects its own data with UCM

This independent FastAPI example uses the small [UCM authentication dependency](ucm_auth.py) to guard its own `/private` route. Its code has no password database, password comparison, or copy of UCM's session table. On every protected request, it forwards the host-scoped HttpOnly cookie to UCM's `/api/me` endpoint and trusts only a successful server response. Logout or session revocation at UCM takes effect on the next request here.

From the repository root, start the normal demo, then run this example in another terminal:

```powershell
.\scripts\Start-Demo.ps1
$env:UCM_API_URL = 'http://127.0.0.1:8000'
$env:UCM_SESSION_COOKIE_NAME = 'ucm_session'
cd examples/python-website
..\..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 3200
```

Visit `http://localhost:3200/private` while signed out: it returns 401. Sign in at `http://localhost:3000`, then revisit the private route: it returns the signed-in username and website-owned notes. Sign out in UCM and try again: it returns 401. Use `localhost` for both browser sites, because cookies are scoped by host, not port; `127.0.0.1` is a different browser cookie host. The adapter's internal UCM URL can use 127.0.0.1 because it forwards the cookie value server-to-server.

This is a **trusted same-host integration**, not arbitrary-domain single sign-on. A real website must route both applications under a compatible HTTPS host, keep the UCM API URL on a trusted internal network, and apply its own authorization rules to its data. The example has only a read-only protected route; an integrating site must also protect its own write routes against CSRF and validate any role or resource ownership. Never pass a username supplied by the browser as proof of login.
