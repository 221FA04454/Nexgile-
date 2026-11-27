package com.nexgile.wealthagent.data

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class ApiException(val status: Int, val code: String, override val message: String) : Exception(message)

class ApiClient(private val tokens: TokenStore) {
    private val jsonType = "application/json; charset=utf-8".toMediaType()
    private val http = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    fun request(path: String, method: String = "GET", body: JSONObject? = null, retry: Boolean = true): JSONObject {
        val builder = Request.Builder()
            .url(ApiConfig.baseUrl + path)
            .addHeader("Accept", "application/json")
        tokens.accessToken?.let { builder.addHeader("Authorization", "Bearer $it") }
        tokens.refreshToken?.let { builder.addHeader("X-Refresh-Token", it) }
        val reqBody = body?.toString()?.toRequestBody(jsonType)
        when (method) {
            "POST" -> builder.post(reqBody ?: "".toRequestBody(jsonType))
            "PUT" -> builder.put(reqBody ?: "".toRequestBody(jsonType))
            else -> builder.get()
        }
        val res = http.newCall(builder.build()).execute()
        val text = res.body?.string().orEmpty()
        val parsed = try { JSONObject(if (text.isBlank()) "{}" else text) } catch (_: Exception) { JSONObject() }
        if (res.code == 401 && retry && !path.contains("/auth/login") && !path.contains("/auth/refresh")) {
            if (refresh()) return request(path, method, body, false)
        }
        if (!res.isSuccessful) {
            val err = parsed.optJSONObject("error")
            throw ApiException(
                res.code,
                err?.optString("code") ?: "HTTP_ERROR",
                friendly(res.code, err?.optString("message") ?: "Request failed")
            )
        }
        return parsed
    }

    fun refresh(): Boolean {
        return try {
            val data = request("/api/auth/refresh", "POST", retry = false)
            tokens.accessToken = data.optString("access_token")
            if (data.has("refresh_token")) tokens.refreshToken = data.optString("refresh_token")
            if (data.has("user")) tokens.userJson = data.getJSONObject("user").toString()
            true
        } catch (_: Exception) {
            false
        }
    }

    companion object {
        fun friendly(status: Int, message: String): String {
            return when (status) {
                401 -> if (message.contains("lock", true)) "Your account is temporarily locked. Please try again later." else "Invalid email or password."
                403 -> if (message.contains("verify", true)) "Please verify your email address before signing in." else "You do not have permission to perform this action."
                404 -> "The requested resource was not found."
                409 -> "An account with this email already exists."
                422 -> message.ifBlank { "Please check the form and try again." }
                429 -> "Too many attempts. Please wait before trying again."
                500, 503 -> "The wealth service is temporarily unavailable."
                else -> message.ifBlank { "Something went wrong. Please try again." }
            }
        }
    }
}
