package com.ucm.authenticator.security

import java.security.MessageDigest
import java.text.Normalizer
import java.util.Base64

object ResetMessage {
    fun bytes(challenge: String, password: String): ByteArray {
        val normalized = Normalizer.normalize(password, Normalizer.Form.NFC)
        return "UCM:password-reset:v1\n".toByteArray(Charsets.UTF_8) +
            Base64.getDecoder().decode(challenge) + "\n".toByteArray(Charsets.UTF_8) +
            MessageDigest.getInstance("SHA-256").digest(normalized.toByteArray(Charsets.UTF_8))
    }
}
