# Three-device HTTPS lab rehearsal

This is the final physical acceptance test for the proposed office access feature. It needs a laptop with Bluetooth and Chrome or Edge, one main Android phone, and two separate Android phones or tablets acting as workplace nodes. A Pixel can be the main phone if it runs Android 15/API 35 or newer with a strong biometric. Two Samsung tablets can be nodes on Android 14/API 34 or newer if both support Bluetooth LE advertising. No physical three-device result has been claimed yet.

The temporary ngrok tunnel supplies one HTTPS address for the portal and API. UCM still performs registration, session checks, signature verification, and authorization on the local backend. The tunnel is a lab transport dependency, not an identity provider or part of the intended self-hosted deployment. ngrok terminates HTTPS at its edge and forwards traffic over an encrypted tunnel to the local agent; the final hop to the localhost portal is HTTP. Use synthetic lab accounts and do not call this a test of end-to-end TLS to UCM.

## Prepare

1. Install ngrok using its [official Windows instructions](https://ngrok.com/download/windows) and add your account's authtoken. Choose the HTTPS dev domain assigned to your account. Keep that exact address for every enrollment and test.
2. Install the backend and frontend dependencies from the [README](../README.md), and install the current [Android debug APK](../output/UCM-lab-debug-android14-2026-11-03.apk) on all three devices. Version 0.3.0 supports two Bluetooth write modes and pre-fills the current lab URL and `progress_demo` username in the debug build. **Update in place** to keep enrolled Keystore keys. Android 15/API 35 or newer and a strong enrolled biometric are required for the Pixel main phone. Android 14/API 34 or newer is sufficient for a workplace tablet if it supports BLE advertising; the app will report when advertising is unavailable. This is a debug-signed lab APK, not a store or production release. The older `UCM-lab-debug-2026-11-03.apk` requires Android 15 and will not install on Android 14.
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

## Demonstrate and record

Use a fresh synthetic account. Keep the two workplace phones apart from the main phone during enrollment so each role has a separate physical key.

| Step | Expected result | Actual result / evidence |
|---|---|---|
| Register and sign in on the HTTPS portal | Password session opens; remote and office data stay locked | To record |
| Enroll main phone; start a fresh request; approve with biometric | Remote opens; office stays locked | To record |
| Enroll node A and node B using separate one-time codes | Both slots appear with different node IDs | To record |
| Start BLE witness mode on both nodes and grant each browser permission | Browser sees both saved devices | To record |
| Start a new request and contact both nodes near the laptop | Both nodes report signed approvals; office data opens | To record |
| After an office grant, sign out and sign back in (or wait for its ten-minute expiry); switch off node B, start another request, and contact devices | Pixel approval and node A can open remote access, but the fresh session cannot reach office level | To record |
| Restore node B; start a fresh request and obtain Pixel plus both tablet approvals | Office level opens again | To record |
| Revoke node B through the website or operator command | Existing office grant ends immediately; a new request cannot use B | To record |
| Try a replayed or expired request | Rejected by the backend | To record |

Record the three Android versions, browser version, the approximate phone-to-laptop distances, request IDs, screenshots of status and denial, and corresponding audit events. Do not include passwords, session cookies, CSRF tokens, private keys, or one-time enrollment codes in screenshots. A stopped node prevents a **new** grant; an already issued grant lasts up to ten minutes unless that node is revoked. Bluetooth presence is not an exact indoor location and does not rule out a live relay attack.

For the first Bluetooth permission grant, keep only tablet A advertising, click **Select node A tablet** in the browser, and choose A. If the browser chooser does not clearly distinguish the tablets, close A's app temporarily, start advertising on B, click **Select node B tablet**, and choose B. Reopen A's app and press **Start Bluetooth witness** again. Both tablets should then remain on the app's **Node** screen with Bluetooth enabled. On the first Start press, Android may ask for Nearby devices permission and the app may ask you to press Start again. Selecting a slot again replaces its earlier browser choice, so extra or stale paired entries are not contacted. A fresh website approval automatically tries the two tablets selected in that tab; use **Contact both phones now** if a tablet was missed. Keep the pipeline tab open after selection; a reload requires selecting both again. Keep the main-phone password reset until the end because it revokes all web sessions.

If the chooser labels a tablet **Paired** but the website reports a **connect** or **find service** error, the browser has identified the tablet but has not finished the separate GATT connection. Use a regular desktop Chrome or Edge window, keep the node app visible with its **advertising** status, and select that tablet's slot again. The website now names the failed slot and connection stage; record the exact message. A successful Bluetooth write is still only the first step: wait for the tablet's **approved request** message and the corresponding node check on the website.

If an Android 15 tablet reports **GATT Error Unknown** on **send request** while the Android 14 tablet succeeds, update both tablets to version 0.3.0. The new APK exposes a second write mode, which the website uses when available. Its **received a Bluetooth request** status shows whether the request arrived even if later server approval fails. This is a physical workaround under test, not a completed acceptance result. If the tunnel URL changes, edit the pre-filled server field to the new HTTPS origin before enrolling or approving.

For operator emergency response, use the [node inventory and revocation commands](TRUST_LEVELS.md#operator-response-to-a-lost-workplace-node) against the phone-lab database. Verify the reported loss before revocation. On this laptop, the phone-lab database path is `.demo/phone-lab/ucm.sqlite3`; set `DATABASE_URL_OVERRIDE` to its absolute `sqlite:///` URL before running an operator command from `backend/`.

## Finish

Stop the tunnel in its terminal and run:

```powershell
.\scripts\Stop-Phone-Lab.ps1
.\scripts\Start-Demo.ps1
```

The isolated lab database and encryption key remain for a repeat rehearsal. The ordinary web demo returns to localhost ports 3000/8000/3100. Do not publish the phone-lab key or database; both are under ignored `.demo/`.

## Current evidence and limit

On November 3, 2026, the launcher was first smoke-tested with a placeholder HTTPS origin. Later the live ngrok origin passed all 19 HTTP security checks with a synthetic account, including Secure and HttpOnly cookie handling, CSRF rejection, foreign-origin rejection, and logout. The version 0.3.0 Android 14 compatible APK was served at `/downloads/ucm-android14.apk` with HTTP 200 and a streamed SHA-256 matching the local build.

A first physical rehearsal enrolled both Samsung workplace nodes. The Pixel and node A approved the same request, opening remote access, while office access stayed locked because node B did not approve. The Android 15 node B tablet advertised and could be paired from the laptop, but the browser reported **GATT Error Unknown** at the request write; the same error occurred when B was selected alone. The app remained on **advertising** and the backend received no node B approval. Version 0.3.0 adds a response-free write mode and a **received a Bluetooth request** status to investigate this failure. This path and the remaining physical result table are still unverified until the updated tablet is tested.
