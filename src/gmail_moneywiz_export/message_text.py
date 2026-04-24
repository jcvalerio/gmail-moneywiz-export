from base64 import urlsafe_b64decode

from bs4 import BeautifulSoup

from gmail_moneywiz_export.normalization import clean_text


def extract_message_text(payload: dict) -> str:
    plain_parts: list[str] = []
    html_parts: list[str] = []
    _collect_parts(payload, plain_parts, html_parts)

    if plain_parts:
        return clean_text("\n\n".join(part for part in plain_parts if part.strip()))
    if html_parts:
        text = "\n\n".join(_html_to_text(part) for part in html_parts if part.strip())
        return clean_text(text)
    return ""


def _collect_parts(
    payload: dict, plain_parts: list[str], html_parts: list[str]
) -> None:
    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})
    data = body.get("data")

    if data:
        decoded = _decode_body(data)
        if mime_type == "text/plain":
            plain_parts.append(decoded)
        elif mime_type == "text/html":
            html_parts.append(decoded)

    for part in payload.get("parts", []) or []:
        _collect_parts(part, plain_parts, html_parts)


def _decode_body(data: str) -> str:
    padding = "=" * (-len(data) % 4)
    decoded = urlsafe_b64decode(data + padding)
    return decoded.decode("utf-8", errors="replace")


def _html_to_text(value: str) -> str:
    soup = BeautifulSoup(value, "html.parser")
    return soup.get_text("\n")
