import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AgentEvalMetrics:
    """Metrics for evaluating agent performance."""
    total_predictions: int = 0
    correct_predictions: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    accuracy: float = 0.0
    avg_confidence: float = 0.0

    def to_dict(self):
        return {
            'total_predictions': self.total_predictions,
            'correct_predictions': self.correct_predictions,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'accuracy': self.accuracy,
            'avg_confidence': self.avg_confidence,
        }


class SummarizerEvaluator:
    """Evaluates summarizer agent performance against ground truth."""

    def __init__(self):
        self.predictions: List[Dict[str, Any]] = []
        self.ground_truth: List[Dict[str, Any]] = []

    def add_prediction(self, email_id: str, summary: str, action: str, confidence: float) -> None:
        """Add a prediction from the summarizer."""
        self.predictions.append({
            'email_id': email_id,
            'summary': summary,
            'action': action,
            'confidence': confidence,
        })

    def add_ground_truth(self, email_id: str, true_action: str) -> None:
        """Add ground truth label for an email."""
        self.ground_truth.append({
            'email_id': email_id,
            'true_action': true_action,
        })

    def evaluate_actions(self) -> AgentEvalMetrics:
        """Evaluate action prediction accuracy."""
        metrics = AgentEvalMetrics()

        # Build lookup for ground truth
        truth_map = {gt['email_id']: gt['true_action'] for gt in self.ground_truth}

        metrics.total_predictions = len(self.predictions)
        correct = 0
        total_confidence = 0.0

        for pred in self.predictions:
            email_id = pred['email_id']
            if email_id in truth_map:
                if pred['action'].lower() == truth_map[email_id].lower():
                    correct += 1
                total_confidence += pred['confidence']

        metrics.correct_predictions = correct
        metrics.accuracy = correct / metrics.total_predictions if metrics.total_predictions > 0 else 0.0
        metrics.avg_confidence = total_confidence / metrics.total_predictions if metrics.total_predictions > 0 else 0.0

        logger.info(f"Summarizer evaluation: accuracy={metrics.accuracy:.2f}, avg_confidence={metrics.avg_confidence:.2f}")
        return metrics

    def export_report(self) -> str:
        """Export evaluation report as JSON."""
        metrics = self.evaluate_actions()
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': metrics.to_dict(),
            'total_samples': len(self.ground_truth),
        }
        return json.dumps(report, indent=2)

    def reset(self) -> None:
        """Reset evaluator state."""
        self.predictions.clear()
        self.ground_truth.clear()


class ActionEvaluator:
    """Evaluates action agent performance."""

    def __init__(self):
        self.action_results: List[Dict[str, Any]] = []

    def add_result(self, email_id: str, action: str, status: str, human_approved: Optional[bool] = None) -> None:
        """Record an action result."""
        self.action_results.append({
            'email_id': email_id,
            'action': action,
            'status': status,
            'human_approved': human_approved,
            'timestamp': datetime.utcnow().isoformat(),
        })

    def evaluate_success_rate(self) -> Dict[str, Any]:
        """Calculate success rate of executed actions."""
        if not self.action_results:
            return {'success_rate': 0.0, 'total_actions': 0}

        total = len(self.action_results)
        successful = sum(1 for r in self.action_results if r['status'] == 'success')
        pending = sum(1 for r in self.action_results if r['status'] == 'pending_approval')
        failed = sum(1 for r in self.action_results if r['status'] == 'failed')

        return {
            'total_actions': total,
            'successful': successful,
            'pending_approval': pending,
            'failed': failed,
            'success_rate': successful / total if total > 0 else 0.0,
        }

    def evaluate_human_approval_rate(self) -> Dict[str, Any]:
        """Evaluate human approval rates."""
        approved_count = sum(1 for r in self.action_results if r['human_approved'] is True)
        rejected_count = sum(1 for r in self.action_results if r['human_approved'] is False)
        pending_count = sum(1 for r in self.action_results if r['human_approved'] is None)

        total = len(self.action_results)
        return {
            'total': total,
            'approved': approved_count,
            'rejected': rejected_count,
            'pending': pending_count,
            'approval_rate': approved_count / total if total > 0 else 0.0,
        }

    def export_report(self) -> str:
        """Export evaluation report as JSON."""
        success_metrics = self.evaluate_success_rate()
        approval_metrics = self.evaluate_human_approval_rate()
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'success_metrics': success_metrics,
            'approval_metrics': approval_metrics,
        }
        return json.dumps(report, indent=2)

    def reset(self) -> None:
        """Reset evaluator state."""
        self.action_results.clear()


class OverallEvaluator:
    """Overall system evaluator combining all agent evaluators."""

    def __init__(self):
        self.summarizer_evaluator = SummarizerEvaluator()
        self.action_evaluator = ActionEvaluator()
        self.start_time = datetime.utcnow()

    def generate_evaluation_report(self) -> Dict[str, Any]:
        """Generate a comprehensive evaluation report."""
        summarizer_metrics = self.summarizer_evaluator.evaluate_actions()
        action_success = self.action_evaluator.evaluate_success_rate()
        action_approval = self.action_evaluator.evaluate_human_approval_rate()

        elapsed_time = (datetime.utcnow() - self.start_time).total_seconds()

        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'elapsed_time_seconds': elapsed_time,
            'summarizer_performance': summarizer_metrics.to_dict(),
            'action_performance': {
                'success_metrics': action_success,
                'approval_metrics': action_approval,
            },
        }
        return report

    def export_report(self) -> str:
        """Export comprehensive report as JSON."""
        report = self.generate_evaluation_report()
        return json.dumps(report, indent=2)

    def reset(self) -> None:
        """Reset all evaluators."""
        self.summarizer_evaluator.reset()
        self.action_evaluator.reset()
        self.start_time = datetime.utcnow()
