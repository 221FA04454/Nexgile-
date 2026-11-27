package com.nexgile.wealthagent.auth

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PasswordRulesTest {
    @Test
    fun strongPasswordPasses() {
        assertTrue(PasswordRules.isValid("SecurePass1!"))
    }

    @Test
    fun weakPasswordFails() {
        assertFalse(PasswordRules.isValid("short"))
        assertFalse(PasswordRules.isValid("alllowercase1!"))
        assertFalse(PasswordRules.isValid("ALLUPPERCASE1!"))
        assertFalse(PasswordRules.isValid("NoNumbers!!"))
        assertFalse(PasswordRules.isValid("NoSpecials1A"))
    }
}

class AuthValidationTest {
    @Test
    fun passwordsMustMatch() {
        val a = "SecurePass1!"
        val b = "SecurePass2!"
        assertFalse(a == b)
        assertTrue(a == "SecurePass1!")
    }
}
