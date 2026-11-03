package com.ucm.authenticator.security

object LoginTrustMessage {
    fun bytes(role: String, challengeId: String, nonce: String): ByteArray {
        require(role == "phone" || role == "node-A" || role == "node-B")
        return "UCM:login-trust:v1\n$role\n$challengeId\n$nonce".toByteArray(Charsets.US_ASCII)
    }
}
