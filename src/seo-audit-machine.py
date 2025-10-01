from gsc_api import list_sites, list_sitemaps, url_inspect

sites = list_sites()
print("Sites:", [s["siteUrl"] for s in sites])

if sites:
    for site in sites:
        site_url = site["siteUrl"]
        print("Sitemaps for", site)
        for sm in list_sitemaps(site_url):
            print(" -", sm.get("path"), sm.get("lastSubmitted"), sm.get("isPending"))
        # print(url_inspect(site_url, "/content/science-fiction-and-fantasy-author"))
