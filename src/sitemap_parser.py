"""
Sitemap fetching & parsing utilities.

- Supports sitemap index recursion
- Handles .xml and .xml.gz
- Returns URLs with optional <lastmod>
"""
from __future__ import annotations

import gzip
from dataclasses import dataclass
from typing import Generator, Iterable, Optional
import requests
from xml.etree import ElementTree as ET

@dataclass
class DiscoveredURL:
    loc: str
    lastmod: Optional[str] = None
    changefreq: Optional[str] = None
    priority: Optional[float] = None

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

def _read_body(resp: requests.Response) -> bytes:
    ct = (resp.headers.get("Content-Type") or "").lower()
    if resp.url.endswith(".gz") or "gzip" in resp.headers.get("Content-Encoding", "").lower():
        return gzip.decompress(resp.content)
    return resp.content

def fetch_xml(url: str, *, timeout: float = 20.0) -> ET.Element:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "SEOAuditMachine/0.1"})
    r.raise_for_status()
    body = _read_body(r)
    return ET.fromstring(body)

def iter_sitemap(url: str, *, max_urls: Optional[int] = None) -> Generator[DiscoveredURL, None, None]:
    """Yield DiscoveredURL from a sitemap or sitemap index URL."""
    root = fetch_xml(url)
    tag = root.tag.lower()
    yielded = 0

    if tag.endswith("sitemapindex"):
        for sm_el in root.findall("sm:sitemap", NS):
            loc_el = sm_el.find("sm:loc", NS)
            if loc_el is None or not loc_el.text:
                continue
            child = loc_el.text.strip()
            for item in iter_sitemap(child, max_urls=None if max_urls is None else max(0, max_urls - yielded)):
                yield item
                yielded += 1
                if max_urls is not None and yielded >= max_urls:
                    return
    else:
        for url_el in root.findall("sm:url", NS):
            loc_el = url_el.find("sm:loc", NS)
            if loc_el is None or not loc_el.text:
                continue
            loc = loc_el.text.strip()
            lastmod_el = url_el.find("sm:lastmod", NS)
            lastmod = lastmod_el.text.strip() if lastmod_el is not None and lastmod_el.text else None
            yield DiscoveredURL(loc=loc, lastmod=lastmod)
            yielded += 1
            if max_urls is not None and yielded >= max_urls:
                return

def discover_from_roots(roots: Iterable[str], *, max_urls: Optional[int] = None) -> Generator[DiscoveredURL, None, None]:
    """Given a list of sitemap or sitemap-index URLs, yield DiscoveredURL."""
    yielded = 0
    for root_url in roots:
        for item in iter_sitemap(root_url, max_urls=None if max_urls is None else max(0, max_urls - yielded)):
            yield item
            yielded += 1
            if max_urls is not None and yielded >= max_urls:
                return
