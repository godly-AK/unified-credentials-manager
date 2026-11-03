package com.ucm.authenticator.security

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Test
import java.util.Base64

class ResetMessageTest {
    @Test fun matchesPythonProtocolFixture() {
        val nonce = Base64.getEncoder().encodeToString(ByteArray(32) { it.toByte() })
        val actual = ResetMessage.bytes(nonce, "violet telescope river 2026").joinToString("") { "%02x".format(it) }
        assertEquals("55434d3a70617373776f72642d72657365743a76310a000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f0a904a52a4c4bea63037ef07908f7e796b67d79d9314c438428c7a636bef522923", actual)
    }

    @Test fun canonicalUnicodeMatchesBackendNormalization() {
        val nonce = Base64.getEncoder().encodeToString(ByteArray(32))
        assertArrayEquals(ResetMessage.bytes(nonce, "café telescope river"), ResetMessage.bytes(nonce, "cafe\u0301 telescope river"))
    }
}
