import html
import re
import urllib.parse
import urllib.request

from backend.tools.base import Tool, ToolContext, ToolError

SEARCH_URL = "https://html.duckduckgo.com/html/?q="
TIMEOUT = 10
MAX_RESULTS = 8

_RESULT = re.compile(
    r'<a[^>]+class="result__a"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>'
    r'.*?class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
    re.S,
)


def _clean(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def _real_url(url: str) -> str:
    """DuckDuckGo wraps links as //duckduckgo.com/l/?uddg=<real url>."""
    query = urllib.parse.urlparse(url).query
    target = urllib.parse.parse_qs(query).get("uddg")
    return target[0] if target else url


def fetch_page(query: str) -> str:
    """Download the search result page. Tests replace this function."""
    request = urllib.request.Request(
        SEARCH_URL + urllib.parse.quote_plus(query), headers={"User-Agent": "Mozilla/5.0 AgentOS"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_results(page: str, limit: int):
    results = []
    for m in _RESULT.finditer(page):
        results.append({
            "title": _clean(m["title"]),
            "url": _real_url(html.unescape(m["url"])),
            "snippet": _clean(m["snippet"]),
        })
        if len(results) >= limit:
            break
    return results


def run(args: dict, ctx: ToolContext):
    query = str(args.get("query", "")).strip()
    if not query:
        raise ToolError("Give a search phrase in 'query'.")
    try:
        limit = max(1, min(int(args.get("max_results") or 5), MAX_RESULTS))
    except ValueError:
        raise ToolError("'max_results' must be a number.")
    try:
        page = fetch_page(query)
    except Exception as e:
        raise ToolError(f"Web search is not available right now: {e}")
    results = parse_results(page, limit)
    if not results:
        raise ToolError("No results found. Try different words.")
    return {"query": query, "results": results}


TOOL = Tool(
    name="web_search",
    description="Search the internet for fresh information. Returns title, link and a short snippet.",
    args={"query": "what to search for", "max_results": "how many results, 1-8 (default 5)"},
    run=run,
)
