"""Shared Facebook Graph API HTTP layer.

Both instagram.py and facebook.py talk to graph.facebook.com — the IG Graph API
and the Pages API live on the same host. This module centralizes the request,
logging, and rate-limit backoff so the platform clients stay thin.
"""
import logging
import time

import requests

logger = logging.getLogger("graph")

GRAPH_VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

# Meta rate-limit / transient error codes worth retrying.
RATE_LIMIT_CODES = {4, 17, 32, 613, 80007}


class GraphAPIError(Exception):
    """Raised when the Graph API returns a non-retryable error or retries are exhausted."""


def graph_request(method, path, access_token, params=None, data=None, max_retries=3):
    """Perform a Graph API call with logging and exponential backoff on rate limits.

    Returns the parsed JSON body on success; raises GraphAPIError otherwise.
    """
    url = f"{BASE_URL}/{path.lstrip('/')}"
    params = dict(params or {})
    params["access_token"] = access_token

    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.request(method, url, params=params, data=data, timeout=30)
        except requests.RequestException as exc:
            logger.warning("Graph %s %s network error (%d/%d): %s", method, path, attempt, max_retries, exc)
            if attempt == max_retries:
                raise GraphAPIError(f"network error: {exc}") from exc
            time.sleep(backoff)
            backoff *= 2
            continue

        body = {}
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": resp.text}

        if resp.ok:
            logger.info("Graph %s %s -> %d", method, path, resp.status_code)
            return body

        err = body.get("error", {}) if isinstance(body, dict) else {}
        code = err.get("code")
        logger.error("Graph %s %s -> %d: %s", method, path, resp.status_code, err or body)

        is_rate_limited = resp.status_code == 429 or code in RATE_LIMIT_CODES
        if is_rate_limited and attempt < max_retries:
            logger.info("Rate limited, backing off %.1fs (attempt %d/%d)", backoff, attempt, max_retries)
            time.sleep(backoff)
            backoff *= 2
            continue

        raise GraphAPIError(f"HTTP {resp.status_code}: {err or body}")

    raise GraphAPIError("retries exhausted")
