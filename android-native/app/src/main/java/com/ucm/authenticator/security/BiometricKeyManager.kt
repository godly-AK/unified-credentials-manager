package com.ucm.authenticator.security

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.Signature
import java.util.Base64

/** Android 15+; keys are separated by server and username. */
class BiometricKeyManager(private val accountScope: String) {
    private val alias = "ucm_recovery_v2_" + MessageDigest.getInstance("SHA-256")
        .digest(accountScope.toByteArray()).joinToString("") { "%02x".format(it) }

    fun createKeyIfMissing(): String {
        if (!keyStore().containsAlias(alias)) {
            val specification = KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_SIGN)
                .setKeySize(2048)
                .setDigests(KeyProperties.DIGEST_SHA256)
                .setMgf1Digests(KeyProperties.DIGEST_SHA256)
                .setSignaturePaddings(KeyProperties.SIGNATURE_PADDING_RSA_PSS)
                .setUserAuthenticationRequired(true)
                .setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG)
                .setInvalidatedByBiometricEnrollment(true)
                .build()
            KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_RSA, "AndroidKeyStore")
                .apply { initialize(specification) }.generateKeyPair()
        }
        val encoded = Base64.getMimeEncoder(64, "\n".toByteArray()).encodeToString(publicKey().encoded)
        return "-----BEGIN PUBLIC KEY-----\n$encoded\n-----END PUBLIC KEY-----"
    }

    fun signatureForBiometricPrompt(): Signature =
        Signature.getInstance("SHA256withRSA/PSS").apply {
            initSign(keyStore().getKey(alias, null) as java.security.PrivateKey)
        }

    fun publicKeyFingerprint(): String = MessageDigest.getInstance("SHA-256").digest(publicKey().encoded)
        .joinToString(":") { "%02X".format(it) }

    private fun publicKey() = keyStore().getCertificate(alias)?.publicKey
        ?: error("Enroll this phone for this account before resetting the password.")

    private fun keyStore() = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
}
