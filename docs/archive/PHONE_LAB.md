# Three-device HTTPS lab rehearsal

This is the physical acceptance test for office access. It needs a laptop with Bluetooth and Chrome or Edge, one main Android phone, and at least two separate Android devices acting as trusted nodes. The main phone needs Android 15/API 35 or newer and a strong biometric. Each node needs Android 14/API 34 or newer and Bluetooth LE advertising. No complete three-device result has been claimed yet.

The temporary ngrok tunnel supplies one HTTPS address for the portal and API. UCM still performs registration, session checks, signature verification, and authorization on the local backend. The tunnel is a lab transport dependency, not an identity provider or part of the intended self-hosted deployment. ngrok terminates HTTPS at its edge and forwards traffic over an encrypted tunnel to the local agent; the final hop to the localhost portal is HTTP. Use synthetic lab accounts and do not call this a test of end-to-end TLS to UCM.

## Prepare

1. Install ngrok using its [official Windows instructions](https://ngrok.com/download/windows) and add your account's authtoken. Choose the HTTPS dev domain assigned to your account. Keep that exact address for every enrollment and test.
2. Install the backend and frontend dependencies from the [README](../../README.md), and install the current [Android debug APK](../../output/UCM-lab-debug-v0.5.0-android14-2026-11-03.apk) on all devices. Version 0.5.0 accepts eight-digit request codes, supports both Bluetooth write modes, and assigns trusted-node roles automatically. The debug build pre-fills the current lab URL and `progress_demo` username. **Update in place** to keep enrolled Keystore keys. This is a debug-signed lab APK, not a store or production release.
3. Stop the normal SQLite demo with `scripts/Stop-Demo.ps1`. The phone lab uses ports 3000 and 8000 but a separate database and encryption key in ignored `.demo/phone-lab/`.
4. From the repository root, replace the example URL below with your assigned HTTPS address:

```powershell
.\scripts\Start-Phone-Lab.ps1 -PublicUrl 'https://YOUR-DOMAIN.ngrok-free.app'
```

The launcher builds the portal for same-origin `/api` requests, migrates the isolated database, enables secure cookies and the office feature in this lab only, and binds both local servers to `127.0.0.1`. It rejects a non-HTTPS address. In a second terminal, start the matching tunnel:

```powershell
ngrok http 3000 --url https://YOUR-DOMAIN.ngrok-free.app
```

Open the **HTTPS** address on the laptop. Enter this same HTTPS address as the server in all three Android apps. Do not use `localhost`, `10.0.2.2`, or a different tunnel name on the phones: Android keys are scoped to the entered server address and account. If ngrok assigns a different URL, stop the phone lab and restart it with that exact URL before enrolling devices.

The portal and API share the tunnel origin, so the browser can use an HttpOnly, Secure, SameSite=Lax session cookie without cross-site cookie workarounds. The backend accepts writes only from the configured HTTPS origin. The sample site at localhost:3100 is not part of this phone rehearsal.

For a live Kibana view of this phone lab's audit events, start the optional [secured monitoring bridge](SECURE_MONITORING.md#optional-live-phone-lab-events) after the separate monitoring stack is running. The built-in administrator page reads this SQLite lab database directly; Kibana reads a copy sent by the bridge. Filter Kibana with `source.keyword: "phone-lab"` and click **Refresh** after a new event.

## Demonstrate and record

Use a fresh synthetic account. Enroll the main phone and each trusted node on separate devices so every role has a separate physical key.

| Step | Expected result | Actual result / evidence |
|---|---|---|
| Register and enter the password on the HTTPS portal | Sign-in page shows the approval code and progress; account pages and remote/office data remain locked | To record |
| Enroll and approve on the main phone | Remote account access opens only after the phone signs. The eight-digit code identifies the request; it is not the security factor. | To record |
| Enroll at least two trusted nodes using separate one-time codes | The node list shows distinct IDs; no A/B choice is required | To record |
| Start BLE witness mode on the nodes and grant browser permission once for each | Browser restores selected devices where supported | To record |
| Keep two nodes advertising, then approve a fresh main-phone request | Browser contacts selected nodes automatically; two distinct signed reports reveal the Confidential header link and open its guarded sample page | To record |
| Start another request with only one node available | Main-phone approval opens remote access, but office stays locked | To record |
| Make a second trusted node available and start a fresh request | Office opens after two distinct node approvals | To record |
| Revoke one node through the website or operator command | Existing office grant ends immediately; another trusted node may be used in a fresh request | To record |
| Try a replayed or expired request | Rejected by the backend | To record |

Record the three Android versions, browser version, the approximate phone-to-laptop distances, request IDs, screenshots of status and denial, and corresponding audit events. Do not include passwords, session cookies, CSRF tokens, private keys, or one-time enrollment codes in screenshots. A stopped node prevents a **new** grant; an already issued grant lasts up to ten minutes unless that node is revoked. Bluetooth presence is not an exact indoor location and does not rule out a live relay attack.

For the first Bluetooth permission grant, keep only one node advertising, click **Choose a nearby node** on the sign-in page, and select it. Repeat with a different node. If the chooser does not distinguish devices clearly, advertise them one at a time. Keep both on the app's **Node** screen with Bluetooth enabled. Android may ask for Nearby devices permission and require another Start press. A fresh website approval automatically tries selected nodes. Chrome/Edge can restore previously permitted devices after reload when `getDevices()` is available; otherwise select them again. Websites cannot silently discover Bluetooth MAC addresses or bypass the first-time device chooser. Keep main-phone password reset until the end because it revokes all web sessions.

If the chooser labels a node **Paired** but the website reports a **connect** or **find service** error, the browser has identified the device but has not finished the separate GATT connection. Use desktop Chrome or Edge, keep the node app visible with its **advertising** status, and select the node again. Record the exact connection stage and error. A successful Bluetooth write is still only the first step: wait for the node's **approved request** message and the corresponding signature count on the website.

If a node reports **GATT Error Unknown** on **send request**, update it to the current APK. It supports a response-free write mode and shows whether it received a Bluetooth request. A browser message that the request was sent does not prove the node signed and reported an approval. Check the node status and the website's signature count. This path remains under physical test. If the tunnel URL changes, edit the pre-filled server field to the new HTTPS origin before enrolling or approving.

For operator emergency response, use the [node inventory and revocation commands](TRUST_LEVELS.md#operator-response-to-a-lost-workplace-node) against the phone-lab database. Verify the reported loss before revocation. On this laptop, the phone-lab database path is `.demo/phone-lab/ucm.sqlite3`; set `DATABASE_URL_OVERRIDE` to its absolute `sqlite:///` URL before running an operator command from `backend/`.

For the separate administrator account, register a new username on the portal and enroll its main phone before granting its monitoring role. Keep `progress_demo` an ordinary account. From the repository root in a new PowerShell terminal, run:

```powershell
$env:DATA_ENCRYPTION_KEY = (Get-Content -Raw .demo/phone-lab/data-encryption-key.txt).Trim()
$env:DATABASE_URL_OVERRIDE = 'sqlite:///' + (Join-Path (Resolve-Path .demo/phone-lab).Path 'ucm.sqlite3').Replace('\', '/')
Push-Location backend
..\.venv\Scripts\python.exe -m app.admin.roles grant --username YOUR_ADMIN_USERNAME --reason "Lab monitoring account approved for demonstration"
Pop-Location
```

The command asks you to type the username again and signs that account out. Sign back in, approve its new request on the phone, then open `/services/monitoring` from **Your account**. The role does not change `progress_demo`.

## Finish

Stop the tunnel in its terminal and run:

```powershell
.\scripts\Stop-Phone-Lab.ps1
.\scripts\Start-Demo.ps1
```

The isolated lab database and encryption key remain for a repeat rehearsal. The ordinary web demo returns to localhost ports 3000/8000/3100. Do not publish the phone-lab key or database; both are under ignored `.demo/`.

## Current evidence and limit

On November 3, 2026, the live HTTPS tunnel passed 19 HTTP security checks with a synthetic account, including Secure and HttpOnly cookie handling, CSRF rejection, foreign-origin rejection, and logout. The debug APK is served from `/downloads/ucm-android14.apk`.

Version 0.5.0 keeps the short request code and automatic Bluetooth contact, removes visible A/B roles, and supports any two distinct trusted nodes. Account pages now require main-phone approval. The APK SHA-256 is `6a1b5c0e6a8ac95c3e4527fda4e491539e78f3fe62ef3db6163ae46c7bacb01c`; its minimum Android API is 34. The new debug APK has the same signing certificate as version 0.4.0, so it can be installed in place. The physical two-node quorum still needs a fresh check.

An earlier physical rehearsal recorded main-phone approval and one trusted-node signature on the same request. Remote access opened, while office access stayed locked because the second node did not sign. The second node advertised and appeared in the browser chooser, but a GATT write error prevented a verified approval. The new response-free write mode has not yet produced a recorded two-node success on physical devices.
