import os
import json
import uuid
from flask import Flask, redirect, request, session, url_for, jsonify
from datetime import datetime

from gmail_client import GmailClient
from openai_client import OpenAIClient
from agents_orchestrator import EmailAssistantOrchestrator
from memory_service import InMemorySessionService, MemoryBank, ConversationMessage
from logger_config import setup_logging, MetricsCollector, RequestTracer, initialize_observability
from agent_evaluator import SummarizerEvaluator, ActionEvaluator, OverallEvaluator

# Initialize observability
initialize_observability(level='INFO', use_json=True)
import logging
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

# Configuration
CLIENT_SECRETS = os.getenv("GOOGLE_CLIENT_SECRETS", "credentials.json")
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "token.json")

# Initialize clients
try:
    gmail = GmailClient(client_secrets_file=CLIENT_SECRETS, token_file=TOKEN_FILE)
    openai_client = OpenAIClient()
    orchestrator = EmailAssistantOrchestrator(gmail, openai_client)
except Exception as e:
    logger.error(f"Failed to initialize clients: {e}")
    orchestrator = None

# Initialize memory and session services
session_service = InMemorySessionService()
memory_bank = MemoryBank()

# Initialize evaluators
overall_evaluator = OverallEvaluator()

# Get metrics and tracer from logger_config
from logger_config import metrics_collector, request_tracer


@app.route("/")
def index():
    return (
        "<h3>Smart Gmail Assistant (Capstone)</h3>"
        "<p>Multi-agent system for email summarization and action suggestions.</p>"
        "<ul>"
        "<li><a href='/authorize'>/authorize</a> - OAuth setup</li>"
        "<li><a href='/process-inbox'>/process-inbox</a> - Process unread emails</li>"
        "<li><a href='/metrics'>/metrics</a> - View performance metrics</li>"
        "<li><a href='/evaluation'>/evaluation</a> - View agent evaluation</li>"
        "</ul>"
    )


@app.route("/authorize")
def authorize():
    auth_url, state = gmail.get_authorization_url()
    session['state'] = state
    return redirect(auth_url)


@app.route("/oauth2callback")
def oauth2callback():
    state = session.get('state')
    full_url = request.url
    creds = gmail.fetch_and_store_token(full_url, state)
    if creds:
        return "Authorization successful. You can now visit /process-inbox to process your inbox."
    return "Authorization failed", 400


@app.route("/process-inbox", methods=["GET", "POST"])
def process_inbox():
    """Process unread emails through the agent orchestrator."""
    trace_id = str(uuid.uuid4())
    request_tracer.start_trace(trace_id)
    
    try:
        if not orchestrator:
            return jsonify({'error': 'Orchestrator not initialized'}), 500

        max_emails = request.args.get('max_emails', default=10, type=int)
        require_approval = request.args.get('require_approval', default=True, type=lambda x: x.lower() == 'true')

        logger.info(f"Processing inbox with trace_id={trace_id}")
        request_tracer.add_span(trace_id, 'inbox_processing_start', {'max_emails': max_emails})

        # Process inbox
        result = orchestrator.process_inbox(max_emails=max_emails, require_approval=require_approval)

        # Record metrics
        metrics_collector.record_email_processed()
        for summary in result.get('summaries', []):
            metrics_collector.record_summary_generated()
        for action in result.get('actions', []):
            metrics_collector.record_action_executed(action.get('status', 'unknown'))

        request_tracer.add_span(trace_id, 'inbox_processing_complete', {
            'total_emails': result['total_emails'],
            'timestamp': result['timestamp']
        })

        logger.info(f"Inbox processing complete for trace_id={trace_id}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing inbox: {e}")
        request_tracer.add_span(trace_id, 'error', {'error': str(e)})
        return jsonify({'error': str(e)}), 500
    finally:
        request_tracer.end_trace(trace_id)


@app.route("/sessions/<session_id>", methods=["GET", "POST"])
def manage_session(session_id):
    """Manage user sessions and conversation state."""
    if request.method == 'POST':
        data = request.get_json()
        if not session_service.get_session(session_id):
            session_service.create_session(session_id)
        
        # Add a message to conversation
        message = ConversationMessage(
            role=data.get('role', 'user'),
            content=data.get('content', ''),
            timestamp=datetime.utcnow().isoformat()
        )
        session_service.add_message(session_id, message)
        
        return jsonify({'status': 'message added'})
    else:
        # GET session state
        sess = session_service.get_session(session_id)
        if sess:
            return jsonify(sess)
        return jsonify({'error': 'session not found'}), 404


@app.route("/memory", methods=["GET", "POST", "DELETE"])
def manage_memory():
    """Manage long-term memory."""
    if request.method == 'POST':
        data = request.get_json()
        key = data.get('key')
        value = data.get('value')
        ttl = data.get('ttl_seconds')
        if key and value:
            memory_bank.store(key, value, ttl_seconds=ttl)
            return jsonify({'status': 'stored'})
        return jsonify({'error': 'missing key or value'}), 400
    
    elif request.method == 'GET':
        key = request.args.get('key')
        if key:
            val = memory_bank.retrieve(key)
            if val is not None:
                return jsonify({'key': key, 'value': val})
            return jsonify({'error': 'key not found'}), 404
        else:
            keys = memory_bank.list_keys()
            return jsonify({'keys': keys})
    
    elif request.method == 'DELETE':
        key = request.args.get('key')
        if key:
            memory_bank.delete(key)
            return jsonify({'status': 'deleted'})
        return jsonify({'error': 'missing key'}), 400


@app.route("/metrics", methods=["GET"])
def get_metrics():
    """Get performance metrics."""
    metrics = metrics_collector.get_metrics()
    return jsonify(metrics)


@app.route("/evaluation/summarizer", methods=["POST", "GET"])
def evaluation_summarizer():
    """Manage summarizer evaluations."""
    if request.method == 'POST':
        data = request.get_json()
        action = data.get('action')  # 'add_prediction' or 'add_truth'
        
        if action == 'add_prediction':
            overall_evaluator.summarizer_evaluator.add_prediction(
                email_id=data.get('email_id'),
                summary=data.get('summary'),
                action=data.get('action'),
                confidence=data.get('confidence', 0.5)
            )
        elif action == 'add_truth':
            overall_evaluator.summarizer_evaluator.add_ground_truth(
                email_id=data.get('email_id'),
                true_action=data.get('true_action')
            )
        
        return jsonify({'status': 'recorded'})
    else:
        report = overall_evaluator.summarizer_evaluator.export_report()
        return jsonify(json.loads(report))


@app.route("/evaluation/action", methods=["POST", "GET"])
def evaluation_action():
    """Manage action evaluations."""
    if request.method == 'POST':
        data = request.get_json()
        overall_evaluator.action_evaluator.add_result(
            email_id=data.get('email_id'),
            action=data.get('action'),
            status=data.get('status'),
            human_approved=data.get('human_approved')
        )
        return jsonify({'status': 'recorded'})
    else:
        report = overall_evaluator.action_evaluator.export_report()
        return jsonify(json.loads(report))


@app.route("/evaluation", methods=["GET"])
def evaluation_overall():
    """Get overall evaluation report."""
    report = overall_evaluator.generate_evaluation_report()
    return jsonify(report)


@app.route("/traces/<trace_id>", methods=["GET"])
def get_trace(trace_id):
    """Retrieve a request trace."""
    trace = request_tracer.get_trace(trace_id)
    if trace:
        return jsonify({'trace_id': trace_id, 'spans': trace})
    return jsonify({'error': 'trace not found'}), 404


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'orchestrator_ready': orchestrator is not None
    })


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'not found'}), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'internal server error'}), 500


if __name__ == '__main__':
    host = os.getenv('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(host=host, port=port, debug=debug)
