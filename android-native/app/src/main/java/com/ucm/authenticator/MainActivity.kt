package com.ucm.authenticator

import android.os.Bundle
import android.view.WindowManager
import androidx.activity.compose.setContent
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import com.ucm.authenticator.network.UcmApi
import com.ucm.authenticator.security.BiometricKeyManager
import com.ucm.authenticator.security.ResetMessage
import com.ucm.authenticator.security.LoginTrustMessage
import com.ucm.authenticator.security.WorkplaceBleServer
import com.ucm.authenticator.security.WorkplaceNodeKeyManager
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import org.json.JSONObject
import java.net.URLEncoder
import java.util.Base64
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class MainActivity : FragmentActivity() {
    private var workplaceServer: WorkplaceBleServer? = null

    fun startWorkplaceNode(api: UcmApi, username: String, slot: String, nodeId: String,
                           onStatus: (String) -> Unit) {
        workplaceServer?.stop()
        workplaceServer = WorkplaceBleServer(this, api, username, slot, nodeId,
            WorkplaceNodeKeyManager(api.baseUrl + "|node|" + username + "|" + slot), onStatus)
        workplaceServer?.start()
    }

    fun stopWorkplaceNode() { workplaceServer?.stop(); workplaceServer = null }

    override fun onDestroy() { stopWorkplaceNode(); super.onDestroy() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        setContent {
            MaterialTheme(colorScheme = lightColorScheme(primary = Color(0xFF315DE5))) {
                Surface(modifier = Modifier.fillMaxSize()) { AuthenticatorScreen(this) }
            }
        }
    }

    suspend fun signWithBiometric(keys: BiometricKeyManager, message: ByteArray,
                                  title: String = "Approve your password reset"): ByteArray {
        check(BiometricManager.from(this).canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG) ==
            BiometricManager.BIOMETRIC_SUCCESS) { "Enroll a strong fingerprint or face in Android settings first." }
        return suspendCancellableCoroutine { continuation ->
            val prompt = BiometricPrompt(this, ContextCompat.getMainExecutor(this),
                object : BiometricPrompt.AuthenticationCallback() {
                    override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                        if (!continuation.isActive) return
                        try {
                            val signer = result.cryptoObject?.signature ?: error("Biometric signing was not authorized.")
                            signer.update(message)
                            continuation.resume(signer.sign())
                        } catch (error: Exception) { continuation.resumeWithException(error) }
                    }
                    override fun onAuthenticationError(code: Int, message: CharSequence) {
                        if (continuation.isActive) continuation.resumeWithException(IllegalStateException(message.toString()))
                    }
                })
            continuation.invokeOnCancellation { prompt.cancelAuthentication() }
            prompt.authenticate(
                BiometricPrompt.PromptInfo.Builder()
                    .setTitle(title)
                    .setSubtitle("Use your biometric to sign this account change.")
                    .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG)
                    .setNegativeButtonText("Cancel").build(),
                BiometricPrompt.CryptoObject(keys.signatureForBiometricPrompt()),
            )
        }
    }
}

@Composable
private fun AuthenticatorScreen(activity: MainActivity) {
    var server by rememberSaveable { mutableStateOf(if (BuildConfig.DEBUG) "https://heterostyled-charitably-raelynn.ngrok-free.dev" else "") }
    var username by rememberSaveable { mutableStateOf(if (BuildConfig.DEBUG) "progress_demo" else "") }
    var password by remember { mutableStateOf("") }
    var newPassword by remember { mutableStateOf("") }
    var confirmation by remember { mutableStateOf("") }
    var recovery by rememberSaveable { mutableStateOf(false) }
    var approval by rememberSaveable { mutableStateOf(false) }
    var nodeMode by rememberSaveable { mutableStateOf(false) }
    var approvalId by rememberSaveable { mutableStateOf("") }
    var nodeTicket by rememberSaveable { mutableStateOf("") }
    var nodeSlot by rememberSaveable { mutableStateOf("A") }
    val nodePrefs = remember { activity.getSharedPreferences("ucm_workplace_node", 0) }
    var nodeId by rememberSaveable { mutableStateOf(nodePrefs.getString("node_id", "") ?: "") }
    var busy by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("") }
    var failed by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp)) {
        Spacer(Modifier.height(20.dp))
        Text("UCM Authenticator", style = MaterialTheme.typography.headlineLarge)
        Text("Your phone holds the key.", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
        Text("Enroll this phone while you know your password. You can then use biometric approval to reset it.", style = MaterialTheme.typography.bodyMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            FilterChip(selected = !recovery && !approval && !nodeMode, onClick = { if (!busy) { recovery = false; approval = false; nodeMode = false; status = "" } }, label = { Text("Enroll") })
            FilterChip(selected = recovery, onClick = { if (!busy) { recovery = true; approval = false; nodeMode = false; status = "" } }, label = { Text("Reset") })
            FilterChip(selected = approval, onClick = { if (!busy) { recovery = false; approval = true; nodeMode = false; status = "" } }, label = { Text("Approve") })
            FilterChip(selected = nodeMode, onClick = { if (!busy) { recovery = false; approval = false; nodeMode = true; status = "" } }, label = { Text("Node") })
        }
        OutlinedTextField(server, { server = it }, label = { Text("UCM server") }, singleLine = true, enabled = !busy, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(username, { username = it }, label = { Text("Username") }, singleLine = true, enabled = !busy, modifier = Modifier.fillMaxWidth())
        if (nodeMode) {
            Text("Keep this workplace phone at its registered position and connected to the UCM server.",
                style = MaterialTheme.typography.bodySmall)
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                FilterChip(selected = nodeSlot == "A", onClick = { nodeSlot = "A" }, label = { Text("Node A") })
                FilterChip(selected = nodeSlot == "B", onClick = { nodeSlot = "B" }, label = { Text("Node B") })
            }
            if (nodeId.isBlank()) {
                OutlinedTextField(nodeTicket, { nodeTicket = it }, label = { Text("One-time enrollment code") },
                    singleLine = true, enabled = !busy, modifier = Modifier.fillMaxWidth())
            } else {
                Text("Registered node: $nodeId", style = MaterialTheme.typography.bodySmall)
                TextButton(onClick = {
                    activity.stopWorkplaceNode(); nodePrefs.edit().clear().apply(); nodeId = ""
                    status = "Local node registration cleared. Revoke this key on the website too."
                }) { Text("Clear local node") }
            }
        } else if (approval) {
            OutlinedTextField(approvalId, { approvalId = it }, label = { Text("Login request ID from website") },
                singleLine = true, enabled = !busy, modifier = Modifier.fillMaxWidth())
            Text("Approve only a request you started on the UCM website.", style = MaterialTheme.typography.bodySmall)
        } else if (!recovery) {
            OutlinedTextField(password, { password = it }, label = { Text("Current password") }, visualTransformation = PasswordVisualTransformation(),
                enabled = !busy, singleLine = true, modifier = Modifier.fillMaxWidth())
        } else {
            OutlinedTextField(newPassword, { newPassword = it }, label = { Text("New password") }, visualTransformation = PasswordVisualTransformation(),
                enabled = !busy, singleLine = true, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(confirmation, { confirmation = it }, label = { Text("Confirm new password") }, visualTransformation = PasswordVisualTransformation(),
                enabled = !busy, singleLine = true, modifier = Modifier.fillMaxWidth())
            Text("Use 15–128 characters. All active sessions will be signed out.", style = MaterialTheme.typography.bodySmall)
        }
        Button(enabled = !busy && username.isNotBlank() && server.isNotBlank(), modifier = Modifier.fillMaxWidth(),
            onClick = {
                scope.launch {
                    busy = true; status = ""; failed = false
                    try {
                        val api = UcmApi(server)
                        val account = username.trim()
                        val keys = BiometricKeyManager(api.baseUrl + "|" + account)
                        if (nodeMode) {
                            if (nodeId.isBlank()) {
                                require(nodeTicket.isNotBlank()) { "Enter the one-time code from the website." }
                                val nodeKeys = WorkplaceNodeKeyManager(api.baseUrl + "|node|" + account + "|" + nodeSlot)
                                val enrolled = api.request("/api/trust/nodes/claim", JSONObject()
                                    .put("ticket", nodeTicket.trim()).put("public_key_pem", nodeKeys.publicKeyPem()))
                                require(enrolled.getString("username") == account && enrolled.getString("slot") == nodeSlot) {
                                    "The code belongs to a different account or slot."
                                }
                                nodeId = enrolled.getString("id")
                                nodePrefs.edit().putString("node_id", nodeId).putString("server", api.baseUrl)
                                    .putString("username", account).putString("slot", nodeSlot).apply()
                                nodeTicket = ""
                                status = "Node enrolled. Press Start Bluetooth witness."
                            } else {
                                require(nodePrefs.getString("server", "") == api.baseUrl &&
                                    nodePrefs.getString("username", "") == account &&
                                    nodePrefs.getString("slot", "") == nodeSlot) {
                                    "Use the same server, account and slot used during node enrollment."
                                }
                                activity.startWorkplaceNode(api, account, nodeSlot, nodeId) { status = it }
                            }
                        } else if (approval) {
                            val id = approvalId.trim()
                            require(id.isNotEmpty()) { "Enter the request ID shown on the website." }
                            val challenge = api.request("/api/trust/challenge/" + URLEncoder.encode(id, "UTF-8"))
                            require(challenge.getString("username") == account) { "This request belongs to another account." }
                            val signature = activity.signWithBiometric(keys,
                                LoginTrustMessage.bytes("phone", id, challenge.getString("nonce")),
                                "Approve remote access")
                            val result = api.request("/api/trust/phone-approve", JSONObject()
                                .put("challenge_id", id)
                                .put("signature_b64", Base64.getEncoder().encodeToString(signature)))
                            status = "Approved. Access level: " + result.getString("level") + ". Refresh the website."
                            approvalId = ""
                        } else if (recovery) {
                            require(newPassword == confirmation) { "The new passwords do not match." }
                            val count = newPassword.codePointCount(0, newPassword.length)
                            require(count in 15..128) { "Use 15–128 characters for the new password." }
                            val intendedPassword = newPassword
                            val challenge = api.request("/api/app/get-reset-challenge?username=" + URLEncoder.encode(account, "UTF-8")).getString("challenge")
                            val signature = activity.signWithBiometric(keys, ResetMessage.bytes(challenge, intendedPassword))
                            val result = api.request("/api/app/verify-reset", JSONObject()
                                .put("username", account).put("challenge_b64", challenge)
                                .put("signed_challenge_b64", Base64.getEncoder().encodeToString(signature))
                                .put("new_password", intendedPassword))
                            status = result.getString("message")
                            newPassword = ""; confirmation = ""
                        } else {
                            check(BiometricManager.from(activity).canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG) ==
                                BiometricManager.BIOMETRIC_SUCCESS) { "Enroll a strong fingerprint or face in Android settings first." }
                            val credentials = password
                            require(credentials.isNotEmpty()) { "Enter your current password to enroll." }
                            val loggedIn = api.request("/api/app/login", JSONObject().put("username", account).put("password", credentials))
                            val token = loggedIn.getString("token")
                            try {
                                val publicKey = keys.createKeyIfMissing()
                                api.request("/api/app/store-public-key", JSONObject().put("username", account)
                                    .put("public_key_pem", publicKey).put("current_password", credentials), token)
                                status = "Phone enrolled. You can approve recovery for this account."
                                password = ""
                            } finally { runCatching { api.request("/api/logout", JSONObject(), token) } }
                        }
                    } catch (error: Exception) {
                        failed = true
                        status = error.message ?: "Could not reach your server. Check the address and try again."
                    } finally { busy = false }
                }
            }) { Text(if (busy) "Working…" else if (nodeMode && nodeId.isBlank()) "Enroll node" else if (nodeMode) "Start Bluetooth witness" else if (approval) "Approve login" else if (recovery) "Approve password reset" else "Enroll this phone") }
        if (status.isNotEmpty()) {
            Card(colors = CardDefaults.cardColors(containerColor =
                if (failed) MaterialTheme.colorScheme.errorContainer else Color(0xFFEAF7F1))) {
                Text(status, modifier = Modifier.padding(16.dp))
            }
        }
        Text("Your private key and biometric data stay on your phone. Passwords and temporary session credentials are never saved by this app.",
            style = MaterialTheme.typography.bodySmall)
    }
}
