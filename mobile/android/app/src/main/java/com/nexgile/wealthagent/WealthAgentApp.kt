package com.nexgile.wealthagent

import android.app.Application

class WealthAgentApp : Application() {
    override fun onCreate() {
        super.onCreate()
        instance = this
    }

    companion object {
        lateinit var instance: WealthAgentApp
            private set
    }
}
