package com.nexgile.wealthagent

import androidx.appcompat.app.AppCompatActivity
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat

class BiometricGate(private val activity: AppCompatActivity) {
    fun canUse(): Boolean {
        val mgr = BiometricManager.from(activity)
        return mgr.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_WEAK) == BiometricManager.BIOMETRIC_SUCCESS
    }

    fun prompt(onSuccess: () -> Unit, onFail: (String) -> Unit) {
        if (!canUse()) {
            onFail("Biometric authentication is not available on this device.")
            return
        }
        val prompt = BiometricPrompt(
            activity,
            ContextCompat.getMainExecutor(activity),
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    onSuccess()
                }
                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    onFail(errString.toString())
                }
            }
        )
        prompt.authenticate(
            BiometricPrompt.PromptInfo.Builder()
                .setTitle("Unlock WealthAgent")
                .setSubtitle("Confirm it is you to reopen this session")
                .setNegativeButtonText("Use password")
                .build()
        )
    }
}
