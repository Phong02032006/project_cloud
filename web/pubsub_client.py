import os
import re
import time
from datetime import datetime, timezone

import jwt
import requests
from flask import current_app, has_app_context


def _cfg(key: str, default: str = "") -> str:
    if has_app_context():
        return (current_app.config.get(key) or default).strip()
    return (os.environ.get(key) or default).strip()


def get_hub_name() -> str:
    return _cfg("AZURE_WEBPUBSUB_HUB", "quizcloud") or "quizcloud"


def exam_group(exam_id: int) -> str:
    return f"exam_{exam_id}"


def is_configured() -> bool:
    return bool(_cfg("AZURE_WEBPUBSUB_CONNECTION_STRING"))


def _parse_connection_string(conn_str: str) -> tuple[str, str]:
    parts = {}
    for segment in conn_str.split(";"):
        if "=" in segment:
            k, v = segment.split("=", 1)
            parts[k.strip().lower()] = v.strip()
    endpoint = parts.get("endpoint", "").rstrip("/")
    access_key = parts.get("accesskey", "")
    port = parts.get("port", "")
    if endpoint and port and not re.search(r":\d+$", endpoint):
        endpoint = f"{endpoint}:{port}"
    if not endpoint or not access_key:
        raise ValueError("Invalid AZURE_WEBPUBSUB_CONNECTION_STRING")
    return endpoint, access_key


def get_client_access_url(exam_id: int, user_id: int | str) -> dict:
    """Return Azure Web PubSub client connection info scoped to group `exam_<exam_id>`."""
    hub = get_hub_name()
    group = exam_group(exam_id)
    conn_str = _cfg("AZURE_WEBPUBSUB_CONNECTION_STRING")
    if not conn_str:
        return {"enabled": False, "url": None, "hub": hub, "group": group}

    roles = [f"webpubsub.joinLeaveGroup.{group}"]
    uid = str(user_id or "anonymous")

    try:
        try:
            from azure.messaging.webpubsubservice import WebPubSubServiceClient

            client = WebPubSubServiceClient.from_connection_string(conn_str, hub=hub)
            token = client.get_client_access_token(
                user_id=uid,
                roles=roles,
                groups=[group],
            )
            url = token.get("url") if isinstance(token, dict) else getattr(token, "url", None)
        except ImportError:
            endpoint, access_key = _parse_connection_string(conn_str)
            ws_endpoint = re.sub(r"^http", "ws", endpoint, flags=re.IGNORECASE)
            aud = f"{endpoint}/client/hubs/{hub}"
            now = int(time.time())
            claims = {
                "aud": aud,
                "sub": uid,
                "iat": now,
                "exp": now + 3600,
                "role": roles,
                "webpubsub.group": [group],
            }
            access_token = jwt.encode(claims, access_key, algorithm="HS256")
            url = f"{ws_endpoint}/client/hubs/{hub}?access_token={access_token}"

        return {"enabled": bool(url), "url": url, "hub": hub, "group": group}
    except Exception:
        if has_app_context():
            current_app.logger.warning(
                "Could not generate Azure Web PubSub client URL for %s; falling back to local sync",
                group,
                exc_info=True,
            )
        return {"enabled": False, "url": None, "hub": hub, "group": group}


def publish_exam_event(exam_id: int, event_type: str, data: dict | None = None) -> dict:
    """Publish a real-time exam event to Azure Web PubSub group `exam_<exam_id>`, or log in local fallback mode."""
    hub = get_hub_name()
    group = exam_group(exam_id)
    payload = {
        "event": event_type,
        "exam_id": exam_id,
        "group": group,
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data": data or {},
    }

    conn_str = _cfg("AZURE_WEBPUBSUB_CONNECTION_STRING")
    if not conn_str:
        if has_app_context():
            current_app.logger.info(
                "WebPubSub local fallback [group=%s event=%s]: %s",
                group,
                event_type,
                payload["data"],
            )
        return payload

    try:
        try:
            from azure.messaging.webpubsubservice import WebPubSubServiceClient

            client = WebPubSubServiceClient.from_connection_string(conn_str, hub=hub)
            client.send_to_group(group=group, message=payload, content_type="application/json")
        except ImportError:
            endpoint, access_key = _parse_connection_string(conn_str)
            send_url = f"{endpoint}/api/hubs/{hub}/groups/{group}/:send?api-version=2024-01-01"
            aud = f"{endpoint}/api/hubs/{hub}/groups/{group}/:send"
            now = int(time.time())
            token = jwt.encode({"aud": aud, "iat": now, "exp": now + 300}, access_key, algorithm="HS256")
            resp = requests.post(
                send_url,
                json=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                timeout=5,
            )
            resp.raise_for_status()
    except Exception:
        if has_app_context():
            current_app.logger.warning(
                "Failed to publish event '%s' to Azure Web PubSub group %s",
                event_type,
                group,
                exc_info=True,
            )
    return payload
