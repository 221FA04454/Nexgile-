package com.nexgile.wealthagent.data

import org.json.JSONObject

class AuthRepository(private val api: ApiClient, private val tokens: TokenStore) {
    fun login(email: String, password: String, remember: Boolean = true): JSONObject {
        val data = api.request(
            "/api/auth/login",
            "POST",
            JSONObject()
                .put("email", email)
                .put("password", password)
                .put("remember_me", remember)
        )
        tokens.accessToken = data.optString("access_token")
        tokens.refreshToken = data.optString("refresh_token")
        tokens.userJson = data.optJSONObject("user")?.toString()
        return data
    }

    fun signup(first: String, last: String, email: String, password: String, confirm: String, phone: String, terms: Boolean): JSONObject {
        return api.request(
            "/api/auth/signup",
            "POST",
            JSONObject()
                .put("first_name", first)
                .put("last_name", last)
                .put("email", email)
                .put("password", password)
                .put("confirm_password", confirm)
                .put("phone", phone)
                .put("accept_terms", terms)
        )
    }

    fun verify(token: String = "", otp: String = "") =
        api.request("/api/auth/verify-email", "POST", JSONObject().put("token", token).put("otp", otp))

    fun resend(email: String) =
        api.request("/api/auth/resend-verification", "POST", JSONObject().put("email", email))

    fun forgot(email: String) =
        api.request("/api/auth/forgot-password", "POST", JSONObject().put("email", email))

    fun reset(token: String, password: String, confirm: String) =
        api.request(
            "/api/auth/reset-password",
            "POST",
            JSONObject().put("token", token).put("password", password).put("confirm_password", confirm)
        )

    fun logout() {
        try {
            api.request("/api/auth/logout", "POST")
        } finally {
            tokens.clear()
        }
    }

    fun dashboard(): JSONObject = api.request("/api/dashboard")
    fun me(): JSONObject = api.request("/api/auth/me")
}
