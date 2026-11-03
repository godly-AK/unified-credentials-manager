package com.ucm.authenticator.security

import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.PrivateKey
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import java.util.Base64

/** A stationary workplace node signs only challenges received through its BLE service. */
class WorkplaceNodeKeyManager(scope: String) {
    private val alias = "ucm_workplace_v1_" + MessageDigest.getInstance("SHA-256")
        .digest(scope.toByteArray()).joinToString("") { "%02x".format(it) }

    fun publicKeyPem(): String {
        val store = store()
        if (!store.containsAlias(alias)) {
            if (Build.VERSION.SDK_INT >= 35) {
                val spec = KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_SIGN)
                    .setKeySize(2048)
                    .setDigests(KeyProperties.DIGEST_SHA256)
                    .setMgf1Digests(KeyProperties.DIGEST_SHA256)
                    .setSignaturePaddings(KeyProperties.SIGNATURE_PADDING_RSA_PSS)
                    .build()
                KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_RSA, "AndroidKeyStore")
                    .apply { initialize(spec) }.generateKeyPair()
            } else {
                val spec = KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_SIGN)
                    .setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1"))
                    .setDigests(KeyProperties.DIGEST_SHA256)
                    .build()
                KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, "AndroidKeyStore")
                    .apply { initialize(spec) }.generateKeyPair()
            }
        }
        val bytes = store().getCertificate(alias).publicKey.encoded
        val encoded = Base64.getMimeEncoder(64, "\n".toByteArray()).encodeToString(bytes)
        return "-----BEGIN PUBLIC KEY-----\n$encoded\n-----END PUBLIC KEY-----"
    }

    fun sign(message: ByteArray): ByteArray {
        val privateKey = store().getKey(alias, null) as PrivateKey
        val algorithm = when (privateKey.algorithm) {
            "RSA" -> "SHA256withRSA/PSS"
            "EC" -> "SHA256withECDSA"
            else -> error("Unsupported workplace node key.")
        }
        val signer = Signature.getInstance(algorithm)
        signer.initSign(privateKey)
        signer.update(message)
        return signer.sign()
    }

    private fun store() = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
}
