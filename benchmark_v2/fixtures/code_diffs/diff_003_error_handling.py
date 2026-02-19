# PR #1249: Add webhook delivery system
import requests
import json

def deliver_webhook(url: str, payload: dict, retries: int = 3):
    """Deliver webhook payload to URL with retries."""
    for attempt in range(retries):
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                return {"success": True, "attempt": attempt + 1}
        except:
            pass
    return {"success": False, "attempts": retries}

def process_event_queue(events: list[dict]):
    """Process all pending webhook events."""
    results = []
    for event in events:
        try:
            result = deliver_webhook(event["url"], event["payload"])
            results.append(result)
        except:
            results.append({"success": False, "error": "unknown"})
    return results
