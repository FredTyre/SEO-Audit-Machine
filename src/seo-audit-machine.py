import argparse

from pathlib import Path

from sitemap_parser import discover_from_roots

from gsc_api import (
    list_sites, 
    list_sitemaps, 
    url_inspect, 
    get_sitemap as gsc_get_sitemap, 
    search_analytics_pages
)

from database import (
    connect, 
    add_site, 
    upsert_sitemap,
    get_sitemaps_by_url,
    upsert_url, 
    record_inspection
)

ROOT = Path(__file__).resolve().parent.parent
DB_FOLDER = ROOT / "database"
DB_PATH = DB_FOLDER / "seo_audit_machine.db"

def migrate_all_gsc_sites(conn):
    sites = list_sites()

    if not sites:
        raise SystemExit("No Google Search Console sites found.")
    
    for site in sites:
        migrate_gsc_site(conn, site)

def migrate_gsc_site(conn, site):    
    site_url = site.get("siteUrl", "")
    if site_url == "":
        print("Skipping site with no URL:", site)
        return
        
    permission_level = site.get("permissionLevel", "")
    site_id = add_site(conn, site_url, name=permission_level)

    print("Using site:", site_url, "→ site_id:", site_id)

    # Store sitemap metadata
    for sm in list_sitemaps(site_url):
        feed = sm.get("path")
        if not feed:
            continue
        meta = gsc_get_sitemap(site_url, feed)
        upsert_sitemap(
            conn,
            site_id,
            url=feed,
            last_submitted = meta.get("lastSubmitted"),
            is_pending = bool(meta.get("isPending")),
        )
        print(" - sitemap:", feed)

    # Optional: try one inspection and store it
    test_url = site_url.replace("sc-domain:", "https://").rstrip("/") + "/"
    resp = url_inspect(site_url, test_url)

    # Map the response into DB fields (same logic used in CLI)
    ir = resp.get("inspectionResult", {}) if isinstance(resp, dict) else {}
    idx = ir.get("indexStatusResult", {}) or {}
    mapped = dict(
        index_status = idx.get("verdict") or idx.get("indexingState"),
        coverage_state = idx.get("coverageState"),
        robots_txt_state = idx.get("robotsTxtState"),
        canonical_url = idx.get("googleCanonical") or idx.get("userCanonical"),
        page_fetch_state = ir.get("pageFetchState"),
        last_crawl_time = idx.get("lastCrawlTime"),
        referring_urls = ir.get("referringUrls") or [],
        raw=resp,
    )

    url_id = upsert_url(conn, site_id, test_url)
    record_inspection(
        conn, url_id,
        index_status = mapped["index_status"],
        coverage_state = mapped["coverage_state"],
        robots_txt_state = mapped["robots_txt_state"],
        canonical_url = mapped["canonical_url"],
        page_fetch_state = mapped["page_fetch_state"],
        last_crawl_time = mapped["last_crawl_time"],
        referring_urls = mapped["referring_urls"],
        raw = mapped["raw"],
    )
    print("Stored inspection for", test_url)

def parse_sitemap_urls(conn, site_id, sitemap_url, max_urls=None) -> int:
    count = 0
    for item in discover_from_roots([sitemap_url], max_urls=max_urls):
        upsert_url(
            conn, 
            site_id, 
            item.loc,
            in_sitemap = True,
            last_modified = item.lastmod,   # <lastmod> -> last_modified
            change_freq = item.changefreq,  # <changefreq> -> change_freq
            priority = item.priority,       # <priority> -> priority (0.0–1.0)
        )
        count += 1

    return count

def _cmd_sync_sites(args: argparse.Namespace, conn) -> None:
    with connect(DB_PATH) as conn:
        migrate_all_gsc_sites(conn)

def _cmd_ingest_sitemaps(args: argparse.Namespace, conn) -> None:
    with connect(DB_PATH) as conn:
        site_url = args.site
        max_urls = args.max_urls

        sitemaps = get_sitemaps_by_url(conn, site_url)
        if not sitemaps:
            print("No sitemaps found for site:", site_url)
            return

        total_urls = 0
        for sm in sitemaps:
            site_id = sm.site_id
            sitemap_url = sm.url
            if not sitemap_url:
                continue
            print("Processing sitemap:", sitemap_url)
            urls = parse_sitemap_urls(conn, site_id, sitemap_url, max_urls)
            total_urls += urls
            print(f" - URLs ingested from sitemap: {urls}")

        print(f"Total URLs ingested: {total_urls}")

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="seo-audit-machine", description="SEO Audit Machine CLI")
    p.add_argument("--db", default=str(DB_PATH), help="Path to SQLite DB (default: database/seo_audit_machine.db)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s2 = sub.add_parser("sync-sites", help="Sync sites & sitemaps metadata from GSC → DB")
    s2.set_defaults(func=_cmd_sync_sites)

    s3 = sub.add_parser("ingest-sitemaps", help="Parse sitemap roots from GSC and store URLs")
    s3.add_argument("--site", required=True, help="GSC property URL (exact string from sites.list())")
    s3.add_argument("--max-urls", type=int, default=None, help="Stop after this many URLs (for testing)")
    s3.set_defaults(func=_cmd_ingest_sitemaps)

    # s4 = sub.add_parser("inspect-url", help="Inspect a URL via GSC and store the result")
    # s4.add_argument("--site", required=True, help="GSC property URL, e.g., https://example.com or sc-domain:example.com")
    # s4.add_argument("--url", required=True, help="URL to inspect (full https://…)")
    # s4.set_defaults(func=cmd_inspect_url)

    # s5 = sub.add_parser("fetch-search-analytics", help="Discover pages from GSC Search Analytics (dimensions=[page])")
    # s5.add_argument("--site", required=True, help="GSC property URL (exact)")
    # s5.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    # s5.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    # s5.add_argument("--rows", type=int, default=25000, help="Row page size (default 25000)")
    # s5.set_defaults(func=_cmd_fetch_search_analytics)
    
    return p
    
# ingest-sitemaps --site "https://fixture.example/" --max-urls 500
def main() -> None:
    print("Running SEO Audit Machine...")

    p = build_parser()
    args = p.parse_args()
    with connect(args.db) as conn:
        args.func(args, conn)

if __name__ == "__main__":
    main()
