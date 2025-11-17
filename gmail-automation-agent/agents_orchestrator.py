import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from gmail_client import GmailClient
from openai_client import OpenAIClient

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Represents a fetched email."""
    id: str
    subject: str
    sender: str
    snippet: str
    body: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class SummaryResult:
    """Result of email summarization."""
    email_id: str
    summary: str
    suggested_action: str  # e.g. 'reply', 'archive', 'escalate'
    confidence: float
    timestamp: str

    def to_dict(self):
        return asdict(self)


@dataclass
class ActionResult:
    """Result of executing an action on an email."""
    email_id: str
    action: str
    status: str  # 'success', 'failed', 'pending_approval'
    message: Optional[str]
    timestamp: str

    def to_dict(self):
        return asdict(self)


class EmailFetcherAgent:
    """Agent responsible for fetching unread emails from Gmail."""

    def __init__(self, gmail_client: GmailClient):
        self.gmail_client = gmail_client

    def fetch_emails(self, max_results: int = 10) -> List[EmailMessage]:
        """Fetch unread emails and return as EmailMessage objects."""
        logger.info(f"EmailFetcherAgent: fetching up to {max_results} unread emails")
        try:
            emails = self.gmail_client.list_unread_emails(max_results=max_results)
            messages = [
                EmailMessage(
                    id=e.get('id', ''),
                    subject=e.get('subject', '(no subject)'),
                    sender=e.get('from', '(unknown)'),
                    snippet=e.get('snippet', ''),
                )
                for e in emails
            ]
            logger.info(f"EmailFetcherAgent: fetched {len(messages)} emails")
            return messages
        except Exception as e:
            logger.error(f"EmailFetcherAgent error: {e}")
            return []


class SummarizerAgent:
    """Agent responsible for summarizing emails and suggesting actions using LLM."""

    def __init__(self, openai_client: OpenAIClient):
        self.openai_client = openai_client

    def summarize_and_suggest(self, email: EmailMessage) -> SummaryResult:
        """Summarize an email and suggest an action (reply, archive, escalate)."""
        logger.info(f"SummarizerAgent: processing email {email.id}")
        try:
            prompt = (
                f"Summarize this email in 1-2 sentences and suggest an action (reply/archive/escalate).\n"
                f"From: {email.sender}\n"
                f"Subject: {email.subject}\n"
                f"Body: {email.snippet}\n\n"
                f"Format your response as JSON: {{"
                f'"summary": "...", "action": "reply|archive|escalate", "confidence": 0.0-1.0'
                f"}}"
            )
            response_text = self.openai_client.summarize_emails([asdict(email)])
            # Try to extract JSON from response
            try:
                result_json = json.loads(response_text)
                summary = result_json.get('summary', response_text)
                action = result_json.get('action', 'escalate')
                confidence = float(result_json.get('confidence', 0.5))
            except json.JSONDecodeError:
                summary = response_text
                action = 'escalate'
                confidence = 0.5

            result = SummaryResult(
                email_id=email.id,
                summary=summary,
                suggested_action=action,
                confidence=confidence,
                timestamp=datetime.utcnow().isoformat(),
            )
            logger.info(f"SummarizerAgent: completed for email {email.id}, action={action}")
            return result
        except Exception as e:
            logger.error(f"SummarizerAgent error: {e}")
            return SummaryResult(
                email_id=email.id,
                summary="(summarization failed)",
                suggested_action='escalate',
                confidence=0.0,
                timestamp=datetime.utcnow().isoformat(),
            )


class ActionAgent:
    """Agent responsible for executing actions on emails (send, archive, etc.)."""

    def __init__(self, gmail_client: GmailClient):
        self.gmail_client = gmail_client

    def execute_action(self, summary: SummaryResult, requires_approval: bool = True) -> ActionResult:
        """Execute an action on an email."""
        logger.info(f"ActionAgent: executing action '{summary.suggested_action}' for email {summary.email_id}")
        
        if requires_approval:
            # In production, this would queue for human approval
            return ActionResult(
                email_id=summary.email_id,
                action=summary.suggested_action,
                status='pending_approval',
                message='Awaiting human approval',
                timestamp=datetime.utcnow().isoformat(),
            )

        try:
            action = summary.suggested_action.lower()
            if action == 'archive':
                # TODO: implement archive via Gmail API
                status, msg = 'success', 'Archived'
            elif action == 'reply':
                # TODO: queue for human to compose reply
                status, msg = 'pending_approval', 'Ready for human reply'
            else:  # escalate
                status, msg = 'success', 'Escalated to human review'

            result = ActionResult(
                email_id=summary.email_id,
                action=action,
                status=status,
                message=msg,
                timestamp=datetime.utcnow().isoformat(),
            )
            logger.info(f"ActionAgent: completed action for email {summary.email_id}, status={status}")
            return result
        except Exception as e:
            logger.error(f"ActionAgent error: {e}")
            return ActionResult(
                email_id=summary.email_id,
                action=summary.suggested_action,
                status='failed',
                message=str(e),
                timestamp=datetime.utcnow().isoformat(),
            )


class EmailAssistantOrchestrator:
    """Orchestrator that coordinates all agents: fetcher, summarizer, action."""

    def __init__(self, gmail_client: GmailClient, openai_client: OpenAIClient):
        self.fetcher = EmailFetcherAgent(gmail_client)
        self.summarizer = SummarizerAgent(openai_client)
        self.action_agent = ActionAgent(gmail_client)

    def process_inbox(
        self, max_emails: int = 10, require_approval: bool = True
    ) -> Dict[str, Any]:
        """
        End-to-end pipeline: fetch emails -> summarize -> execute actions.
        Returns a summary report.
        """
        logger.info("Orchestrator: starting process_inbox")
        
        # Step 1: Fetch emails
        emails = self.fetcher.fetch_emails(max_results=max_emails)
        if not emails:
            logger.info("Orchestrator: no emails to process")
            return {
                'total_emails': 0,
                'summaries': [],
                'actions': [],
                'timestamp': datetime.utcnow().isoformat(),
            }

        # Step 2: Summarize each email (can be parallelized)
        summaries = []
        for email in emails:
            summary = self.summarizer.summarize_and_suggest(email)
            summaries.append(summary)

        # Step 3: Execute actions (can be parallelized)
        actions = []
        for summary in summaries:
            action = self.action_agent.execute_action(summary, requires_approval=require_approval)
            actions.append(action)

        result = {
            'total_emails': len(emails),
            'summaries': [s.to_dict() for s in summaries],
            'actions': [a.to_dict() for a in actions],
            'timestamp': datetime.utcnow().isoformat(),
        }
        logger.info(f"Orchestrator: completed process_inbox, processed {len(emails)} emails")
        return result
