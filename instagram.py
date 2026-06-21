"""Instagram Graph API client.

Uses only the official Instagram Graph API (no Selenium / instagrapi / unofficial APIs).
"""
import json

from graph import graph_request


def reply_to_comment(comment_id, message, access_token):
    """Post a public reply under an Instagram comment.

    POST /{ig-comment-id}/replies
    """
    return graph_request("POST", f"{comment_id}/replies", access_token, data={"message": message})


def send_dm(comment_id, message, ig_business_account_id, access_token):
    """Send a private DM in response to a comment (Instagram private reply).

    POST /{ig-business-account-id}/messages  with recipient={comment_id}

    Private replies let you message the commenter even if they never DMed you first,
    within Meta's allowed window — provided the app holds instagram_manage_messages.
    """
    payload = {
        "recipient": json.dumps({"comment_id": comment_id}),
        "message": json.dumps({"text": message}),
    }
    return graph_request("POST", f"{ig_business_account_id}/messages", access_token, data=payload)


def send_text_dm(recipient_id, message, ig_business_account_id, access_token):
    """Send a plain DM to a known user (IGSID) — used for the follow-up step.

    POST /{ig-business-account-id}/messages  with recipient={id}
    """
    payload = {
        "recipient": json.dumps({"id": recipient_id}),
        "message": json.dumps({"text": message}),
    }
    return graph_request("POST", f"{ig_business_account_id}/messages", access_token, data=payload)


def list_recent_media(ig_business_account_id, access_token, limit=15):
    """List recent media so the auto-arm job can match a just-published reel.

    GET /{ig-business-account-id}/media?fields=id,caption,media_type,timestamp
    """
    body = graph_request(
        "GET",
        f"{ig_business_account_id}/media",
        access_token,
        params={"fields": "id,caption,media_type,timestamp", "limit": limit},
    )
    items = body.get("data", []) if isinstance(body, dict) else []
    return [
        {
            "id": m.get("id"),
            "caption": m.get("caption", "") or "",
            "media_type": m.get("media_type", ""),
            "timestamp": m.get("timestamp", ""),
        }
        for m in items
    ]


def get_post_details(post_id, access_token):
    """Fetch media thumbnail + caption for dashboard preview.

    GET /{ig-media-id}?fields=id,caption,media_url,thumbnail_url,permalink
    """
    body = graph_request(
        "GET",
        post_id,
        access_token,
        params={"fields": "id,caption,media_url,thumbnail_url,permalink"},
    )
    return {
        "id": body.get("id"),
        "caption": body.get("caption", ""),
        # thumbnail_url exists for videos; media_url for images.
        "thumbnail": body.get("thumbnail_url") or body.get("media_url", ""),
        "permalink": body.get("permalink", ""),
    }
