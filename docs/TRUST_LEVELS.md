# Login pipeline and trust levels

UCM now supports three access levels for the same account. The backend, not the page, decides which resource can be read.

| Level | Requirement | Example resource |
|---|---|---|
| Account | Password and an active session | Account settings |
| Remote | Account session plus a fresh approval signed by the enrolled main phone after a strong biometric prompt | `/api/data/remote` |
| Office | Remote approval plus fresh signatures from two distinct registered workplace phones, A and B, prompted by local Bluetooth contact from the browser | `/api/data/office` |

The [login pipeline page](../frontend/src/app/services/pipeline/page.tsx) shows each step and calls the protected API resources. A changed label or hidden page cannot change the API decision. A new request has a random nonce, a unique ID, a three-minute deadline, and a role-specific signed message. The short-lived trust grant expires after ten minutes or when the underlying session ends. Starting another request invalidates the old pending request.

## Setup and demonstration

1. Register and log in on the website. Enroll the main phone in the Android app using the **Enroll** tab.
2. Open **Login pipeline**. Press **Start fresh approval**. On the main phone, open **Approve**, enter the request ID, and approve the biometric prompt. The remote resource opens after refresh.
3. For workplace nodes, enter a label, choose slot A or B, and create a one-time enrollment code with the current account password. Enter the code in the Android app's **Node** tab on a separate phone. Repeat with the third phone for the other slot.
4. On each workplace phone, press **Start Bluetooth witness** and leave the app on screen. The website's **Grant a workplace phone** action asks for browser Bluetooth permission once per phone. Later requests use the previously granted devices when the browser supports `getDevices()`.
5. On a new request, the computer writes the request ID to each nearby phone over Bluetooth. Each phone retrieves the nonce from UCM, checks the account, signs a message with its own Android Keystore key, and reports directly to UCM. The office resource opens only after the main phone and both different node slots have approved the same request.
6. An account owner can revoke a lost workplace node on the page with the current password. A database operator can do the same without the owner's session using the emergency command below. Revocation clears office grants, pending requests, and unused node-enrollment codes. Re-enroll a replacement phone.

On the local demo, office access is **disabled by default** with `OFFICE_TRUST_ENABLED=false`. Enable it only after the computer and both real workplace phones have passed an end-to-end rehearsal. Remote access can still be exercised with the main phone. For physical phones, UCM must be reachable at a trusted HTTPS address; the debug HTTP exception is limited to an Android emulator using `10.0.2.2`. The local launcher listening on `localhost` is not a physical-phone deployment.

The isolated [phone-lab launcher and acceptance record](PHONE_LAB.md) prepares one HTTPS origin for an eventual ngrok rehearsal and enables office approval only within that separate lab database. The [self-hosted deployment](DEPLOYMENT.md) keeps office disabled until physical testing passes.

## Security boundary and limits

- The node private keys stay in Android Keystore. UCM stores public keys and validates RSA-PSS signatures. The website cannot invent node approvals.
- The backend checks that the three public keys differ. It cannot yet cryptographically prove that those keys were generated on three separate physical phones. Enroll the workplace phones under supervision; hardware-backed attestation is a future hardening step.
- Changing or removing an enrolled main-phone key now requires both the current password and a recent signed main-phone approval for that session. This prevents a stolen password alone from swapping in an attacker's phone. Losing the phone requires the operator procedure below; self-service password-only recovery is deliberately unavailable.
- Browser permission is granted through the browser's device picker once per node. Browser and device support for Web Bluetooth vary; reconnecting may fail when a phone is off, out of range, or its app is not active.
- This is a **Bluetooth presence signal**, not an exact indoor position. Signal strength does not locate a person reliably, and Bluetooth relay attacks can make a distant device appear nearby. Rotating challenge IDs stops straightforward replay but does not stop a live relay.
- The current policy grants office access for up to ten minutes after approval. It does not continuously check that both phones remain present. The account owner currently manages the node list; a separate organization administrator role has not been built.
- An API 36.1 emulator verified signed main-phone approval, signed reset, node enrollment, and Android Bluetooth advertising with a simulated fingerprint. It does not verify real biometric hardware, browser-to-phone Bluetooth contact, two-node quorum on separate devices, or the physical distance at which access stops. Those checks require the actual laptop and three phones.

## Device acceptance checklist

- A fresh password session cannot read either tiered resource.
- Main-phone approval opens remote data and leaves office data locked.
- A request approved by only node A, or only node B, leaves office data locked.
- The two nodes and main phone together open office data on the same fresh request.
- A stopped, distant, or revoked node prevents a new office approval. An old office grant remains valid until its short expiry unless revoked.
- A replayed signature, a signature for the wrong role or request, an expired request, and a copied old session cannot open a resource.
- Verify the exact server address, TLS certificate, Android permissions, and browser's saved Bluetooth grants before the demonstration.

## Operator recovery for a lost main phone

The operator must verify the account owner's identity outside UCM before running this command. The public API has no operator reset endpoint. Back up the database, use the same database connection settings as the API, and run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m app.admin.recover_phone --username ACCOUNT_NAME --reason "Identity verified by lab operator"
```

The command asks the operator to type the exact username again. It clears the old main-phone key and pending approvals, revokes all sessions, and records a high-risk audit event with the reason. The user must sign in with the existing password and enroll a new main phone. For the local SQLite demo, set `DATABASE_URL_OVERRIDE` to the same `.demo/ucm.sqlite3` path used by the launcher before running the command. A production organization should define who may act as operator and how identity checks are recorded.

The command mechanics were rehearsed with a synthetic account in the isolated phone-lab database. The proposed human verification and two-person approval steps are in the [operator policy](OPERATOR_POLICY.md); they have not yet been carried out with real people.

## Operator response to a lost workplace node

Use the same database connection settings as the API. First list the account's nodes from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m app.admin.manage_nodes list --username ACCOUNT_NAME
```

After verifying the report of loss and identifying the node ID, revoke that ID:

```powershell
..\.venv\Scripts\python.exe -m app.admin.manage_nodes revoke --username ACCOUNT_NAME --node-id NODE_ID --reason "Reported lost and verified by lab operator"
```

The command requires the operator to type the exact node ID. It does not expose an unauthenticated web endpoint. The action records a high-risk event containing the reason, invalidates active office grants, and clears pending login approvals and unused node-enrollment codes for that account. A remote grant also ends if it had been upgraded to office; the owner can request a fresh main-phone approval. For the local SQLite demo, use the launcher's `DATABASE_URL_OVERRIDE` before either command. Operator database access and identity-check policy remain deployment responsibilities.

The inventory and revoke commands were exercised end to end with a synthetic node. Use the [operator policy](OPERATOR_POLICY.md) when responding to an actual loss.
