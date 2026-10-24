"""Launch clarity A/B studies via the Terac MCP.

The Terac MCP provides tools like:
  - terac.create_study
  - terac.list_responses
  - terac.get_results

This module wraps those MCP calls. In Claude Code, Terac tools are available
directly via MCP — this file defines the study logic and prompts.
"""

import json
from datetime import datetime
from pathlib import Path

WIKI_DIR = Path(__file__).parent.parent.parent / "wiki"
STUDY_PROMPTS_FILE = Path(__file__).parent.parent / "terac_prompts.json"


def build_clarity_study(pages: list[dict]) -> dict:
    """Build an A/B clarity study for Terac.

    pages: [{"slug": "...", "version_a": "jargon text", "version_b": "plain text"}]

    Returns the study config to send to terac.create_study.
    """
    questions = []
    for i, page in enumerate(pages):
        questions.append({
            "id": f"q{i+1}",
            "type": "compare",
            "text": "Which explanation is easier to understand?",
            "options": [
                {"id": "a", "text": page["version_a"][:500]},
                {"id": "b", "text": page["version_b"][:500]},
            ],
            "follow_up": {
                "type": "rating",
                "text": "Rate clarity from 1 (confusing) to 5 (crystal clear)",
                "scale": 5,
            },
            "feedback": {
                "type": "text",
                "text": "In one sentence, what confused you most?",
            },
        })

    return {
        "title": f"CNCF Wiki Clarity Study — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        "target_audience": "general_population",
        "questions": questions,
        "metadata": {"page_slugs": [p["slug"] for p in pages]},
    }


def build_pricing_study() -> dict:
    """Build a willingness-to-pay study."""
    return {
        "title": "CNCF Wiki — Pricing Feedback",
        "target_audience": "general_population",
        "questions": [
            {
                "id": "q1",
                "type": "compare",
                "text": "Would you pay $3 for a cited cloud-native wiki delivered in minutes?",
                "options": [
                    {"id": "yes", "text": "Yes, $3 seems fair"},
                    {"id": "no", "text": "No, I'd want it cheaper or free"},
                ],
                "feedback": {
                    "type": "text",
                    "text": "What would make it worth paying for?",
                },
            }
        ],
    }


def analyze_clarity_results(responses: list[dict]) -> dict:
    """Analyze Terac responses to determine winning patterns.

    Returns: {winner: "a"|"b", avg_score: float, key_complaints: list, per_page: dict}
    """
    if not responses:
        return {"winner": "none", "avg_score": 0, "key_complaints": [], "per_page": {}}

    a_wins = 0
    b_wins = 0
    total_score = 0
    score_count = 0
    complaints = []

    for r in responses:
        answers = r.get("answers", {})
        for q_id, ans in answers.items():
            if ans.get("choice") == "a":
                a_wins += 1
            elif ans.get("choice") == "b":
                b_wins += 1
            rating = ans.get("rating")
            if rating:
                total_score += rating
                score_count += 1
            fb = ans.get("feedback", "")
            if fb:
                complaints.append(fb)

    return {
        "winner": "a" if a_wins > b_wins else "b",
        "a_wins": a_wins,
        "b_wins": b_wins,
        "avg_score": round(total_score / score_count, 2) if score_count else 0,
        "key_complaints": complaints[:10],
        "total_responses": len(responses),
    }
