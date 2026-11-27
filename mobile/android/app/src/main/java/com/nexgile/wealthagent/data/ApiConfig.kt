package com.nexgile.wealthagent.data

import com.nexgile.wealthagent.BuildConfig

object ApiConfig {
    val baseUrl: String = BuildConfig.API_BASE_URL.trimEnd('/')
    const val emulatorHostHint: String = "Android emulator traffic uses 10.0.2.2 to reach the host FastAPI server on port 8000."
}
