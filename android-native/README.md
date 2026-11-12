# UCM native Android authenticator
The Android Studio/Kotlin client includes enrollment, password reset, main-phone login approval, and workplace-node Bluetooth witness mode. Flutter remains a historical reference.

## Requirements
The **main phone** needs Android 15/API 35 or newer and an enrolled strong biometric. A **workplace node** can run Android 14/API 34 or newer if it supports Bluetooth LE advertising. Android SDK 36, Gradle 8.13, AGP 8.13.2, and Android Studio's bundled JDK are used for compilation. The main phone keeps the explicit SHA-256 MGF1 policy available from API 35; Android 14 nodes use a Keystore P-256 ECDSA/SHA-256 key instead. The debug build pre-fills the current phone-lab ngrok address and `progress_demo`; edit those fields if your test origin or account differs. Release builds leave both blank.

## Flows
**Enroll phone:** enter the UCM server, username, and current password. The app signs in, generates/reuses an account-and-server-specific 2048-bit Keystore key, stores its public key through the authenticated enrollment API, and signs out the temporary bearer session.

**Reset password:** no login is required. Enter a new password twice; obtain a nonce; approve a BiometricPrompt CryptoObject; sign the nonce plus new-password digest; send the approval to the backend. The backend verifies it and invalidates existing sessions.

**Approve remote access:** sign in on the website. Enter its eight-digit code on the main phone's **Approve** tab, review the account, and use the strong biometric prompt. UCM validates the signed role-specific nonce before opening any account page.

**Trusted node:** create a five-minute enrollment code on the website and claim it on a separate Android device's **Node** tab. The server assigns an internal role automatically. This generates a distinct Android Keystore key: RSA-PSS on Android 15+ or P-256 ECDSA on Android 14. Start Bluetooth witness mode and keep the app visible. The computer writes a fresh request ID to the node's BLE GATT service; the node fetches the request from UCM and sends a signed approval to UCM. Any two distinct registered nodes can open office access. See [trust-level limits](../docs/archive/TRUST_LEVELS.md).

Passwords and bearer credentials are kept in memory only. Private keys never leave Android Keystore. Screenshots are disabled for this credential UI. Changed biometric enrollment invalidates the signing key.

## Transport
The release configuration allows HTTPS only and keeps normal certificate validation. Debug permits HTTP solely to 10.0.2.2, localhost, and 127.0.0.1. Use http://10.0.2.2:8000 for an emulator connecting to the host's local demo. Physical phones need a trusted HTTPS address reachable from their network; the local `localhost` launcher alone does not provide one.

The URL host and username form the key's scope. Enroll and recover with the same normalized server address. A production deployment needs a valid/trusted HTTPS certificate; there is no trust-all workaround.

For the planned three-device demonstration, use the single HTTPS origin in the [phone-lab runbook](../docs/archive/PHONE_LAB.md). The ngrok URL must be identical in the portal and on all three Android devices. The tunnel is for the lab only; UCM still verifies every signature itself.

## Build and test
```powershell
$env:JAVA_HOME = 'C:\Program Files\Android\Android Studio\jbr'
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat assembleDebug testDebugUnitTest
```
APK: app/build/outputs/apk/debug/app-debug.apk.

On Windows, Gradle may otherwise pick a different system JDK. The November 3 command above passed with Android Studio's JDK 21; the system JDK 25 failed before compilation.

Three JVM tests validate the reset and login-signature message formats. The APK compiles. On October 30, the app ran on an Android API 36.1 emulator with an enrolled simulated fingerprint. It enrolled a synthetic main-phone key through the live API, signed a login request after BiometricPrompt, and unlocked remote data while office data remained locked. It also signed a password reset after BiometricPrompt; the old password was rejected and the new password worked. The same emulator claimed a trusted-node enrollment code and started Bluetooth GATT advertising. The Android 14 ECDSA node path passed backend protocol tests and APK compilation. Browser-to-node Bluetooth contact, two simultaneous physical nodes, proximity, and real-device biometrics still require a three-device rehearsal.

Changing or removing an enrolled main-phone key requires a recent signed approval from that phone plus the current password. A lost/inaccessible main phone uses the [operator recovery command](../docs/archive/TRUST_LEVELS.md#operator-recovery-for-a-lost-main-phone); self-service password-only replacement is intentionally blocked. The project currently allows one enrolled main-phone public key per account. Recovery from simultaneous loss of both password and phone still needs an organizational identity-verification policy.
