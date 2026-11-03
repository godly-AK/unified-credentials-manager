package com.ucm.authenticator.security

import org.junit.Assert.assertEquals
import org.junit.Test

class LoginTrustMessageTest {
    @Test fun matchesBackendProtocol() {
        val actual = LoginTrustMessage.bytes("phone", "request-123", "fresh-nonce").toString(Charsets.US_ASCII)
        assertEquals("UCM:login-trust:v1\nphone\nrequest-123\nfresh-nonce", actual)
    }

    @Test fun acceptsAssignedTrustedNodeRole() {
        val actual = LoginTrustMessage.bytes("node-n0123abcd", "request-123", "fresh-nonce").toString(Charsets.US_ASCII)
        assertEquals("UCM:login-trust:v1\nnode-n0123abcd\nrequest-123\nfresh-nonce", actual)
    }
}
