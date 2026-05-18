"""URL and source normalization helpers."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    parsed = urlsplit((url or "").strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    query = urlencode(
        [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    )
    return urlunsplit((scheme, netloc, path, query, ""))


def domain_from_url(url: str) -> str | None:
    host = urlsplit(url).netloc.lower()
    return host or None


def canonical_title(title: str | None) -> str | None:
    return " ".join((title or "").split()) or None
