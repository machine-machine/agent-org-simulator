# PR #1248: Add request counter for rate limiting
import time

request_counts = {}  # Global mutable state

def check_rate_limit(client_ip: str, max_requests: int = 100, window_sec: int = 60):
    """Check if client has exceeded rate limit."""
    now = time.time()
    if client_ip not in request_counts:
        request_counts[client_ip] = []
    
    # Clean old entries
    request_counts[client_ip] = [t for t in request_counts[client_ip] if now - t < window_sec]
    
    if len(request_counts[client_ip]) >= max_requests:
        return False  # Rate limited
    
    request_counts[client_ip].append(now)
    return True

def reset_counts():
    """Reset all rate limit counters."""
    global request_counts
    request_counts = {}
