package com.nexgile.wealthagent.auth

object PasswordRules {
    data class Rule(val label: String, val test: (String) -> Boolean)

    val rules = listOf(
        Rule("At least 10 characters") { it.length >= 10 },
        Rule("One uppercase letter") { it.any { c -> c.isUpperCase() } },
        Rule("One lowercase letter") { it.any { c -> c.isLowerCase() } },
        Rule("One number") { it.any { c -> c.isDigit() } },
        Rule("One special character") { it.any { c -> !c.isLetterOrDigit() } }
    )

    fun failures(password: String): List<String> = rules.filter { !it.test(password) }.map { it.label }

    fun isValid(password: String) = failures(password).isEmpty()
}
