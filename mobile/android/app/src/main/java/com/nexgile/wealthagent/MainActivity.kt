package com.nexgile.wealthagent

import android.graphics.Color
import android.os.Bundle
import android.text.InputType
import android.util.TypedValue
import android.view.Gravity
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.setPadding
import com.google.android.material.button.MaterialButton
import com.nexgile.wealthagent.auth.PasswordRules
import com.nexgile.wealthagent.data.ApiClient
import com.nexgile.wealthagent.data.ApiConfig
import com.nexgile.wealthagent.data.ApiException
import com.nexgile.wealthagent.data.AuthRepository
import com.nexgile.wealthagent.data.TokenStore
import kotlin.concurrent.thread

enum class Screen { Splash, Welcome, Login, Signup, Verify, Forgot, Reset, Dashboard, Profile, Settings }

class MainActivity : AppCompatActivity() {
    private lateinit var tokens: TokenStore
    private lateinit var repo: AuthRepository
    private lateinit var root: LinearLayout
    private var screen = Screen.Splash
    private var notice = ""
    private var pendingEmail = ""
    private var pendingToken = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tokens = TokenStore(this)
        repo = AuthRepository(ApiClient(tokens), tokens)
        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#F1EFE8"))
        }
        setContentView(ScrollView(this).apply { addView(root) })
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (screen == Screen.Dashboard || screen == Screen.Splash) return
                if (tokens.isLoggedIn && screen != Screen.Login) show(Screen.Dashboard) else show(Screen.Welcome)
            }
        })
        show(Screen.Splash)
        root.postDelayed({
            show(if (tokens.isLoggedIn) Screen.Dashboard else Screen.Welcome)
        }, 700)
    }

    private fun show(next: Screen) {
        screen = next
        root.removeAllViews()
        when (next) {
            Screen.Splash -> splash()
            Screen.Welcome -> welcome()
            Screen.Login -> login()
            Screen.Signup -> signup()
            Screen.Verify -> verify()
            Screen.Forgot -> forgot()
            Screen.Reset -> reset()
            Screen.Dashboard -> dashboard()
            Screen.Profile -> profile()
            Screen.Settings -> settings()
        }
    }

    private fun formatInr(value: Double): String {
        val n = kotlin.math.round(value).toLong()
        val sign = if (n < 0) "-" else ""
        val digits = kotlin.math.abs(n).toString()
        if (digits.length <= 3) return "₹$sign$digits"
        val parts = mutableListOf(digits.takeLast(3))
        var rest = digits.dropLast(3)
        while (rest.isNotEmpty()) {
            parts.add(rest.takeLast(2))
            rest = rest.dropLast(2)
        }
        return "₹$sign${parts.reversed().joinToString(",")}"
    }
    }

    private fun splash() {
        root.setBackgroundColor(Color.parseColor("#0C1B2A"))
        root.gravity = Gravity.CENTER
        root.addView(label("N", 28, Color.parseColor("#A6854D"), true))
        root.addView(label("Nexgile WealthAgent", 18, Color.WHITE, true))
        root.addView(label("Restoring session", 13, Color.parseColor("#9AADB8")))
    }

    private fun welcome() {
        brandHeader()
        root.addView(label("Institutional wealth, privately held.", 26, Color.parseColor("#14202C"), true))
        root.addView(label("Sign in to your authorized household. The book of record stays on the server.", 14, Color.parseColor("#5D6B78")))
        root.addView(primary("Sign in") { show(Screen.Login) })
        root.addView(ghost("Create account") { show(Screen.Signup) })
        root.addView(label(ApiConfig.emulatorHostHint, 12, Color.parseColor("#8A96A1")))
    }

    private fun login() {
        brandHeader()
        root.addView(label("Sign in", 24, Color.parseColor("#14202C"), true))
        val email = field("Email", InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS)
        val password = field("Password", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD)
        val remember = CheckBox(this).apply { text = "Remember this device"; isChecked = true }
        val err = errorView()
        root.addView(email.first); root.addView(email.second)
        root.addView(password.first); root.addView(password.second)
        root.addView(remember)
        root.addView(err)
        root.addView(primary("Sign in") {
            runIo {
                repo.login(email.second.text.toString(), password.second.text.toString(), remember.isChecked)
                runOnUiThread { show(Screen.Dashboard) }
            }
        })
        root.addView(ghost("Forgot password") { show(Screen.Forgot) })
        root.addView(ghost("Create account") { show(Screen.Signup) })
        attachError(err)
    }

    private fun signup() {
        brandHeader()
        root.addView(label("Create account", 24, Color.parseColor("#14202C"), true))
        val first = field("First name")
        val last = field("Last name")
        val email = field("Email", InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS)
        val phone = field("Phone (optional)", InputType.TYPE_CLASS_PHONE)
        val password = field("Password", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD)
        val confirm = field("Confirm password", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD)
        val terms = CheckBox(this).apply { text = "I accept the Terms and Privacy Policy" }
        val err = errorView()
        listOf(first, last, email, phone, password, confirm).forEach { root.addView(it.first); root.addView(it.second) }
        PasswordRules.rules.forEach { root.addView(label("• ${it.label}", 12, Color.parseColor("#8A96A1"))) }
        root.addView(terms); root.addView(err)
        root.addView(primary("Create account") {
            val fails = PasswordRules.failures(password.second.text.toString())
            if (fails.isNotEmpty()) { err.text = fails.joinToString("; "); return@primary }
            if (password.second.text.toString() != confirm.second.text.toString()) { err.text = "Passwords do not match."; return@primary }
            if (!terms.isChecked) { err.text = "You must accept the Terms and Privacy Policy."; return@primary }
            runIo {
                val res = repo.signup(
                    first.second.text.toString(), last.second.text.toString(), email.second.text.toString(),
                    password.second.text.toString(), confirm.second.text.toString(), phone.second.text.toString(), true
                )
                pendingEmail = email.second.text.toString()
                pendingToken = res.optJSONObject("development")?.optString("otp").orEmpty()
                notice = res.optString("message")
                runOnUiThread { show(Screen.Verify) }
            }
        })
        attachError(err)
    }

    private fun verify() {
        brandHeader()
        root.addView(label("Verify email", 24, Color.parseColor("#14202C"), true))
        root.addView(label(notice.ifBlank { "Enter the code from your verification message." }, 14, Color.parseColor("#5D6B78")))
        val otp = field("Verification code", InputType.TYPE_CLASS_NUMBER)
        if (pendingToken.isNotBlank()) otp.second.setText(pendingToken)
        val err = errorView()
        root.addView(otp.first); root.addView(otp.second); root.addView(err)
        root.addView(primary("Verify") {
            runIo {
                repo.verify(otp = otp.second.text.toString())
                notice = "Your email is verified. You can now sign in."
                runOnUiThread { show(Screen.Login) }
            }
        })
        root.addView(ghost("Resend") {
            runIo { repo.resend(pendingEmail); runOnUiThread { notice = "If an account needs verification, we sent instructions." } }
        })
        attachError(err)
    }

    private fun forgot() {
        brandHeader()
        root.addView(label("Forgot password", 24, Color.parseColor("#14202C"), true))
        val email = field("Email", InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS)
        val err = errorView()
        root.addView(email.first); root.addView(email.second); root.addView(err)
        root.addView(primary("Send instructions") {
            runIo {
                val res = repo.forgot(email.second.text.toString())
                pendingToken = res.optJSONObject("development")?.optString("reset_url").orEmpty()
                    .substringAfter("token=", "")
                notice = res.optString("message")
                runOnUiThread { show(Screen.Reset) }
            }
        })
        attachError(err)
    }

    private fun reset() {
        brandHeader()
        root.addView(label("New password", 24, Color.parseColor("#14202C"), true))
        val password = field("New password", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD)
        val confirm = field("Confirm password", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD)
        val err = errorView()
        root.addView(password.first); root.addView(password.second)
        root.addView(confirm.first); root.addView(confirm.second)
        root.addView(err)
        root.addView(primary("Update password") {
            if (password.second.text.toString() != confirm.second.text.toString()) {
                err.text = "Passwords do not match."; return@primary
            }
            runIo {
                repo.reset(pendingToken, password.second.text.toString(), confirm.second.text.toString())
                notice = "Your password was updated. Sign in with your new password."
                runOnUiThread { show(Screen.Login) }
            }
        })
        attachError(err)
    }

    private fun dashboard() {
        brandHeader()
        root.addView(label("Dashboard", 24, Color.parseColor("#14202C"), true))
        val body = label("Loading authorized book of record…", 14, Color.parseColor("#5D6B78"))
        val err = errorView()
        root.addView(body)
        root.addView(err)
        root.addView(ghost("Profile") { show(Screen.Profile) })
        root.addView(ghost("Settings") { show(Screen.Settings) })
        attachError(err)
        runIo {
            val data = repo.dashboard()
            val nw = data.optJSONObject("net_worth")?.optDouble("total") ?: 0.0
            runOnUiThread {
                body.text = "Net worth ${formatInr(nw)}\nHousehold-scoped FastAPI data. Currency remains INR."
            }
        }
    }

    private fun profile() {
        brandHeader()
        root.addView(label("Profile", 24, Color.parseColor("#14202C"), true))
        root.addView(label(tokens.userJson ?: "Session user", 13, Color.parseColor("#5D6B78")))
        root.addView(primary("Back") { show(Screen.Dashboard) })
    }

    private fun settings() {
        brandHeader()
        root.addView(label("Settings", 24, Color.parseColor("#14202C"), true))
        root.addView(label("API ${ApiConfig.baseUrl}", 12, Color.parseColor("#8A96A1")))
        val bio = BiometricGate(this)
        if (bio.canUse()) {
            root.addView(ghost("Unlock with biometrics") {
                bio.prompt({ show(Screen.Dashboard) }, { })
            })
        }
        root.addView(primary("Sign out") {
            runIo { repo.logout(); runOnUiThread { show(Screen.Login) } }
        })
    }

    private fun brandHeader() {
        root.setBackgroundColor(Color.parseColor("#F1EFE8"))
        root.setPadding(dp(20))
        root.gravity = Gravity.TOP
        root.addView(label("NEXGILE WEALTHAGENT", 12, Color.parseColor("#A6854D"), true))
        if (notice.isNotBlank() && screen != Screen.Verify) {
            root.addView(label(notice, 13, Color.parseColor("#1B6B58")))
            notice = ""
        }
    }

    private var lastErr: TextView? = null
    private fun attachError(view: TextView) { lastErr = view }
    private fun runIo(block: () -> Unit) {
        thread {
            try {
                block()
            } catch (ex: ApiException) {
                runOnUiThread { lastErr?.text = ex.message }
            } catch (ex: Exception) {
                runOnUiThread { lastErr?.text = "The wealth service is unavailable. Check your network connection." }
            }
        }
    }

    private fun label(text: String, size: Int, color: Int, serif: Boolean = false) = TextView(this).apply {
        this.text = text
        setTextColor(color)
        setTextSize(TypedValue.COMPLEX_UNIT_SP, size.toFloat())
        setPadding(0, dp(8), 0, dp(8))
    }

    private fun field(hint: String, type: Int = InputType.TYPE_CLASS_TEXT): Pair<TextView, EditText> {
        val label = label(hint, 12, Color.parseColor("#5D6B78"))
        val input = EditText(this).apply {
            inputType = type
            setPadding(dp(12), dp(12), dp(12), dp(12))
            setBackgroundColor(Color.WHITE)
        }
        return label to input
    }

    private fun errorView() = TextView(this).apply { setTextColor(Color.parseColor("#A33B32")); textSize = 13f }
    private fun primary(text: String, onClick: () -> Unit) = MaterialButton(this).apply {
        this.text = text
        setOnClickListener { onClick() }
        setPadding(0, dp(8), 0, dp(8))
    }
    private fun ghost(text: String, onClick: () -> Unit) = MaterialButton(this, null, com.google.android.material.R.attr.materialButtonOutlinedStyle).apply {
        this.text = text
        setOnClickListener { onClick() }
    }
    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()
}
