"""Facebook Pages / Messenger Graph API client.

Uses only the official Graph API. The Facebook side has one big advantage over
Instagram: a private reply lets you send a Messenger DM in direct response to a
public comment, sidestepping the usual 24-hour messaging window and the
"user must message you first" rule.
"""
import json

from graph import graph_request


def reply_to_comment(comment_id, message, access_token):
    """Post a public reply under a Facebook comment.

    POST /{comment-id}/comments
    """
    return graph_request("POST", f"{comment_id}/comments", access_token, data={"message": message})


def send_dm(comment_id, message, access_token):
    """Send a private Messenger reply to the author of a comment.

    Uses the Messenger Send API with a comment_id recipient:
        POST /me/messages  { recipient: {comment_id}, message: {text} }

    This is the supported path for comment-to-DM. The older
    /{comment-id}/private_replies edge returns code 100 / subcode 33 on many
    post types (reels, photos), so it is not used.
    """
    return graph_request(
        "POST",
        "me/messages",
        access_token,
        data={
            "recipient": json.dumps({"comment_id": comment_id}),
            "message": json.dumps({"text": message}),
            "messaging_type": "RESPONSE",
        },
    )


def send_text_dm(recipient_id, message, access_token):
    """Send a plain Messenger message to a known user (PSID).

    POST /me/messages  { recipient: {id}, message: {text} }

    Used for the follow-up step: once the user has replied, they are an open
    conversation, so we address them by PSID instead of a comment_id.
    """
    return graph_request(
        "POST",
        "me/messages",
        access_token,
        data={
            "recipient": json.dumps({"id": recipient_id}),
            "message": json.dumps({"text": message}),
            "messaging_type": "RESPONSE",
        },
    )


def get_post_details(post_id, access_token):
    """Fetch post image + message for dashboard preview.

    GET /{post-id}?fields=id,message,full_picture,permalink_url
    """
    body = graph_request(
        "GET",
        post_id,
        access_token,
        params={"fields": "id,message,full_picture,permalink_url"},
    )
    return {
        "id": body.get("id"),
        "caption": body.get("message", ""),
        "thumbnail": body.get("full_picture", ""),
        "permalink": body.get("permalink_url", ""),
    }
