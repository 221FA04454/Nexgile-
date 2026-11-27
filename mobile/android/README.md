# Nexgile WealthAgent — Android

Native Android client for the existing FastAPI API.

## Run

1. Start the platform: `docker compose up` from the repository root.
2. Open `mobile/android` in Android Studio.
3. Run on an emulator. The debug API base URL is `http://10.0.2.2:8000`.

Do not use `http://localhost:8000` inside the Android emulator.

## Security

Authentication tokens are stored with EncryptedSharedPreferences.
The app never contains `GROQ_API_KEY`, database passwords, or JWT signing secrets.
