Smart Gmail Assistant (Flask)

This project is a minimal Flask-based assistant that connects to Gmail (via OAuth2) and summarizes unread emails using OpenAI.

Features
- OAuth2 sign-in for Gmail
- List unread messages
- Summarize unread messages via OpenAI
- Send messages via Gmail API

Prerequisites
- Python 3.9+
- A Google Cloud project with Gmail API enabled and OAuth 2.0 Client credentials (downloaded as credentials.json).
- An OpenAI API key

Setup (PowerShell)

1) Create and activate a virtual environment

python -m venv .venv
.\.venv\Scripts\Activate.ps1

2) Install dependencies

pip install -r requirements.txt

3) Prepare credentials
- In Google Cloud Console, enable Gmail API and create OAuth 2.0 Client ID credentials (Web application).
- Set Authorized redirect URI to http://localhost:5000/oauth2callback.
- Download credentials.json and place it in the project root or set GOOGLE_CLIENT_SECRETS env var accordingly.

4) Environment variables
- Copy .env.example to .env and fill values, or set environment variables directly in PowerShell:

$env:OPENAI_API_KEY = 'sk-...'
$env:FLASK_SECRET_KEY = 'some-secret'
# optional:
$env:GOOGLE_CLIENT_SECRETS = 'credentials.json'
$env:GOOGLE_REDIRECT_URI = 'http://localhost:5000/oauth2callback'

Running the app

# from project root
$env:FLASK_APP = 'app.py'
python -m flask run --host=127.0.0.1 --port=5000

Usage
- Visit http://localhost:5000/authorize and complete Google sign-in.
- After successful authorization, call GET /inbox to retrieve and summarize unread emails.
- Send email by POSTing JSON to /send with { "to": "someone@example.com", "subject": "Hi", "body": "Hello" }.

Security & Notes
- This is a sample; in production use secure storage for tokens, HTTPS redirects, and granular permissions.
- The app stores tokens in token.json by default. Protect that file.

Next steps
- Add persistent database for message metadata and actions
- Add batch processing or scheduled jobs
- Add UI that shows message summaries and quick-reply flows
