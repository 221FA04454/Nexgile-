package com.nexgile.wealthagent.data

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class TokenStore(context: Context) {
    private val master = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()
    private val prefs = EncryptedSharedPreferences.create(
        context,
        "wa_secure_session",
        master,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    var accessToken: String?
        get() = prefs.getString("access", null)
        set(value) { prefs.edit().putString("access", value).apply() }

    var refreshToken: String?
        get() = prefs.getString("refresh", null)
        set(value) { prefs.edit().putString("refresh", value).apply() }

    var userJson: String?
        get() = prefs.getString("user", null)
        set(value) { prefs.edit().putString("user", value).apply() }

    fun clear() {
        prefs.edit().clear().apply()
    }

    val isLoggedIn: Boolean get() = !accessToken.isNullOrBlank() || !refreshToken.isNullOrBlank()
}
