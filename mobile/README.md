# Native Android client

This module is a native Android application. It consumes the existing FastAPI backend.

- Emulator API host: `http://10.0.2.2:8000` (maps to the host machine, not `localhost`)
- Tokens are stored with EncryptedSharedPreferences / Android Keystore
- No Groq keys, JWT secrets, or database credentials are bundled
- Biometrics unlock an existing session; they do not replace server authentication

Open `mobile/android` in Android Studio and run the `devDebug` build against local Docker (`docker compose up`).
