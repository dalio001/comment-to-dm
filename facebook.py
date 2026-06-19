"""Facebook Pages / Messenger Graph API client.

Uses only the official Graph API. The Facebook side has one big advantage over
Instagram: `private_replies` lets you send a Messenger DM in direct response to a
public comment, sidestepping the usual 24-hour messaging window and the
"user must message you first" rule.
"""
from graph import graph_request


def reply_to_comment(comment_id, message, access_token):
    """Post a public reply under a Facebook comment.

    POST /{comment-id}/comments
    """
    return graph_request("POST", f"{comment_id}/comments", access_token, data={"message": message})


def send_dm(comment_id, message, access_token):
    """Send a private Messenger reply to the author of a comment.

    POST /{comment-id}/private_replies
    """
    return graph_request("POST", f"{comment_id}/private_replies", access_token, data={"message": message})


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
