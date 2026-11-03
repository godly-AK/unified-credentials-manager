package com.ucm.authenticator.network

import com.ucm.authenticator.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URI

class UcmApi(address: String) {
    val baseUrl: String = address.trim().trimEnd('/')

    init {
        val uri = URI(baseUrl)
        require(uri.host != null && uri.userInfo == null && uri.query == null && uri.fragment == null && uri.path.isNullOrEmpty()) {
            "Enter a server address such as https://ucm.example.com."
        }
        val localDebug = BuildConfig.DEBUG && uri.scheme == "http" && uri.host in setOf("10.0.2.2", "127.0.0.1", "localhost")
        require(uri.scheme == "https" || localDebug) { "Use HTTPS. Local HTTP is allowed only in a debug emulator build." }
    }

    suspend fun request(path: String, body: JSONObject? = null, token: String? = null): JSONObject = withContext(Dispatchers.IO) {
        val connection = URI(baseUrl + path).toURL().openConnection() as HttpURLConnection
        try {
            connection.requestMethod = if (body == null) "GET" else "POST"
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 10000
            connection.readTimeout = 15000
            connection.setRequestProperty("Accept", "application/json")
            if (token != null) connection.setRequestProperty("Authorization", "Bearer $token")
            if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            val successful = connection.responseCode in 200..299
            val stream = if (successful) connection.inputStream else connection.errorStream
            val data = stream?.bufferedReader()?.use { JSONObject(it.readText()) }
                ?: error("The server returned no response.")
            if (!successful) error(data.optString("detail", "The request could not be completed."))
            data
        } finally { connection.disconnect() }
    }
}
