"""Transparent source type and quality heuristics."""

from urllib.parse import urlsplit


OFFICIAL_DOMAINS = (
    "amd.com",
    "nvidia.com",
    "intel.com",
    "microsoft.com",
    "google.com",
    "google.dev",
    "googleblog.com",
    "openai.com",
)


# Known blogging / dev-community platforms. These domains publish primarily
# long-form articles and should score as ``blog`` rather than ``unknown``.
# Extend this list as new platforms surface in live runs.
BLOG_DOMAINS = (
    "medium.com",
    "substack.com",
    "dev.to",
    "hashnode.com",
    "hashnode.dev",
    "ghost.io",
    "wordpress.com",
    "blogspot.com",
    "bearblog.dev",
    "posthaven.com",
    "write.as",
)

# URL path segments that strongly indicate an article / blog post. Checked
# against the URL path (not the host) to catch company blogs at custom
# domains (e.g. ``company.com/blog/...``, ``company.com/articles/...``).
BLOG_PATH_SEGMENTS = (
    "/blog/",
    "/blogs/",
    "/article/",
    "/articles/",
    "/post/",
    "/posts/",
    "/writeups/",
    "/insights/",
)

# Academic paper hosts / preprint servers / peer-reviewed mirrors. Anything on
# this list should classify as ``paper`` even when the path lacks ``/abs/`` or
# similar arxiv-style markers.
PAPER_DOMAINS = (
    "arxiv.org",
    "alphaxiv.org",
    "biorxiv.org",
    "medrxiv.org",
    "chemrxiv.org",
    "openreview.net",
    "semanticscholar.org",
    "ieeexplore.ieee.org",
    "dl.acm.org",
    "acm.org",
    "aclanthology.org",
    "link.springer.com",
    "springer.com",
    "sciencedirect.com",
    "nature.com",
    "science.org",
    "cell.com",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "jmir.org",
    "ai.jmir.org",
    "jmlr.org",
    "proceedings.mlr.press",
    "papers.nips.cc",
    "mdpi.com",
    "plos.org",
    "tandfonline.com",
    "wiley.com",
    "onlinelibrary.wiley.com",
    "frontiersin.org",
    "oup.com",
    "cambridge.org",
)

# Source-code hosting platforms. Treated as a distinct ``repo`` type so
# READMEs, research-report repos, and reference implementations can contribute
# to the ledger without being conflated with blogs.
REPO_DOMAINS = (
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "codeberg.org",
    "sourcehut.org",
    "sr.ht",
)


def _host_matches(host: str, candidates: tuple[str, ...]) -> bool:
    return any(host == domain or host.endswith(f".{domain}") for domain in candidates)


def classify_source_type(url: str, title: str = "", provider: str = "") -> str:
    parsed = urlsplit(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    haystack = f"{url} {title} {provider}".lower()
    if provider == "arxiv" or _host_matches(host, PAPER_DOMAINS):
        return "paper"
    if _host_matches(host, OFFICIAL_DOMAINS):
        return "official"
    if ("docs." in host or "documentation" in haystack) and any(domain in host for domain in OFFICIAL_DOMAINS):
        return "documentation"
    if "benchmark" in haystack or "mlperf" in haystack:
        return "benchmark"
    if any(domain in host for domain in ("reuters.com", "bloomberg.com", "apnews.com", "theverge.com")):
        return "news"
    if _host_matches(host, BLOG_DOMAINS):
        return "blog"
    if "blog" in haystack:
        return "blog"
    if any(segment in path for segment in BLOG_PATH_SEGMENTS):
        return "blog"
    if _host_matches(host, REPO_DOMAINS):
        return "repo"
    if any(domain in host for domain in ("reddit.com", "news.ycombinator.com", "stackoverflow.com")):
        return "forum"
    return "unknown"


def source_quality_score(source_type: str) -> float:
    return {
        "official": 0.95,
        "documentation": 0.9,
        "paper": 0.85,
        "benchmark": 0.85,
        "news": 0.6,
        "repo": 0.55,
        "blog": 0.45,
        "forum": 0.25,
        "unknown": 0.2,
    }.get(source_type, 0.2)
