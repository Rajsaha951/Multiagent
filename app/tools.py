"""LangChain tools the agents can call: web search (Tavily) and page scraping."""
import ipaddress
import os
import socket
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool

TAVILY_URL = os.getenv("TAVILY_BASE_URL", "https://api.tavily.com")


@tool
def web_search(query: str) -> str:
    """Search the web for recent, reliable information. Returns titles, URLs and snippets."""
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        return "Search unavailable: TAVILY_API_KEY is not set."
    try:
        resp = requests.post(
            f"{TAVILY_URL}/search",
            headers={"Authorization": f"Bearer {key}"},
            json={"query": query, "max_results": 5},
            timeout=15,
        )
        if not resp.ok:
            return f"Search failed with status {resp.status_code}."
        blocks = [
            f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {str(r['content'])[:400]}"
            for r in resp.json().get("results", [])
        ]
        return "\n----\n".join(blocks) or "No results found."
    except Exception as e:
        return f"Search failed: {e}"


def _is_public_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return not (addr.is_private or addr.is_loopback or addr.is_link_local
                or addr.is_reserved or addr.is_multicast or addr.is_unspecified)


def _is_safe_url(url: str) -> bool:
    """SSRF guard: the model picks the URL, so never let it reach internal addresses."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith((".local", ".internal")):
        return False
    try:
        return _is_public_ip(host)          # host is an IP address
    except ValueError:
        pass
    try:                                     # host is a name: check every IP it resolves to
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True                          # cannot resolve here; the request itself will fail
    return all(_is_public_ip(info[4][0]) for info in infos)


def _get_following_safe_redirects(url: str, hops: int = 3) -> requests.Response:
    for _ in range(hops + 1):
        if not _is_safe_url(url):
            raise ValueError("URL is not allowed")
        resp = requests.get(url, timeout=10, allow_redirects=False,
                            headers={"User-Agent": "Mozilla/5.0 (ResearchMind)"})
        if resp.is_redirect and resp.headers.get("location"):
            url = urljoin(url, resp.headers["location"])
            continue
        return resp
    raise ValueError("Too many redirects")


@tool
def scrape_url(url: str) -> str:
    """Fetch a web page and return its cleaned text (first ~4000 characters)."""
    try:
        resp = _get_following_safe_redirects(url)
        if not resp.ok:
            return f"Could not scrape {url}: status {resp.status_code}"
        ctype = resp.headers.get("content-type", "")
        if "text/html" not in ctype and "text/plain" not in ctype:
            return f"Could not scrape {url}: unsupported content type ({ctype or 'unknown'})"
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return f"SOURCE: {url}\n{text[:4000]}"
    except Exception as e:
        return f"Could not scrape {url}: {e}"
