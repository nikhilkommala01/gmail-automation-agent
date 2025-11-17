import os
import json
from flask import Flask, redirect, request, session, url_for, jsonify

from gmail_client import GmailClient
try:
    # import OpenAIClient lazily to avoid requiring OPENAI_API_KEY at startup
    from openai_client import OpenAIClient
except Exception:
    OpenAIClient = None

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

CLIENT_SECRETS = os.getenv("GOOGLE_CLIENT_SECRETS", "credentials.json")
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "token.json")

gmail = GmailClient(client_secrets_file=CLIENT_SECRETS, token_file=TOKEN_FILE)
openai_client = None


@app.route("/")
def index():
    return (
        "<h3>Smart Gmail Assistant</h3>"
        "<p>Use <a href='/authorize'>/authorize</a> to connect your Gmail account.</p>"
    )


@app.route("/authorize")
def authorize():
    auth_url, state = gmail.get_authorization_url()
    session['state'] = state
    return redirect(auth_url)


@app.route('/authorize_debug')
def authorize_debug():
    """Return the authorization URL as JSON so you can copy/paste it into a browser."""
    auth_url, state = gmail.get_authorization_url()
    session['state'] = state
    return jsonify({'auth_url': auth_url})


@app.route("/oauth2callback")
def oauth2callback():
    state = session.get('state')
    full_url = request.url
    creds = gmail.fetch_and_store_token(full_url, state)
    if creds:
        return "Authorization successful. You can now visit /inbox to see summaries."
    return "Authorization failed", 400


@app.route("/inbox")
def inbox():
    try:
        emails = gmail.list_unread_emails(max_results=10)
        if not emails:
            return jsonify({'count': 0, 'summary': 'No unread messages'})
        global openai_client
        if openai_client is None:
            if OpenAIClient is None:
                return jsonify({'error': 'OpenAI client not available; set OPENAI_API_KEY'}), 500
            openai_client = OpenAIClient()

        summary = openai_client.summarize_emails(emails)
        return jsonify({'count': len(emails), 'summary': summary, 'emails': emails})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/send", methods=["POST"])
def send():
    data = request.get_json(force=True)
    to = data.get('to')
    subject = data.get('subject', '')
    body = data.get('body', '')
    if not to:
        return jsonify({'error': 'missing to address'}), 400
    try:
        sent = gmail.send_message(to_address=to, subject=subject, body=body)
        return jsonify({'sent': True, 'id': sent.get('id')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    host = os.getenv('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    app.run(host=host, port=port, debug=True)
