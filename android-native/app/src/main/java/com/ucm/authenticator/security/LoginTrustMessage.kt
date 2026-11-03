package com.ucm.authenticator.security

object LoginTrustMessage {
    fun bytes(role: String, challengeId: String, nonce: String): ByteArray {
        require(role == "phone" || role.matches(Regex("node-[A-Za-z0-9]{1,32}")))
        return "UCM:login-trust:v1\n$role\n$challengeId\n$nonce".toByteArray(Charsets.US_ASCII)
    }
}
