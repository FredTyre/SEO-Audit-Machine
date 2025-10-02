from __future__ import annotations
import pathlib

from datetime import date
from typing import Any, List, Dict, Optional, cast

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials as UserCredentials  # concrete class

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

ROOT = pathlib.Path(__file__).resolve().parent.parent
SECRETS = ROOT / ".secrets" / "client_secret.json"
TOKEN = ROOT / "token.json"

def _get_creds() -> UserCredentials:
    creds: Optional[UserCredentials] = None

    if TOKEN.exists():
        # typeshed sometimes widens this return type; cast to the concrete class we expect
        creds = cast(UserCredentials, UserCredentials.from_authorized_user_file(str(TOKEN), SCOPES))

    if not creds or not creds.valid:
        if creds and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS), SCOPES)
            creds = cast(UserCredentials, flow.run_local_server(port=0))

        # concrete class defines to_json()
        TOKEN.write_text(creds.to_json())

    return creds

def _svc():
    return build("searchconsole", "v1", credentials=_get_creds(), cache_discovery=False)

def build_service(api_name: str, api_version: str):
    creds = _get_creds()
    return build(api_name, api_version, credentials=creds, cache_discovery=False)

# -------- High-level helpers --------

def list_sites() -> List[Dict[str, Any]]:
    """Returns sites you have access to (verified/properties)."""
    svc = build_service("searchconsole", "v1")
    resp = svc.sites().list().execute()
    return resp.get("siteEntry", []) or []

def list_sitemaps(site_url: str) -> List[Dict[str, Any]]:
    """Lists all sitemaps for a given property (siteUrl)."""
    svc = build_service("searchconsole", "v1")
    resp = svc.sitemaps().list(siteUrl=site_url).execute()
    return resp.get("sitemap", []) or []

def get_sitemap(site_url: str, feedpath: str) -> Dict[str, Any]:
    """Gets a specific sitemap’s metadata (e.g., lastSubmitted, is pending, etc.)."""
    svc = build_service("searchconsole", "v1")
    return svc.sitemaps().get(siteUrl=site_url, feedpath=feedpath).execute()

def search_analytics_pages(
    site_url: str,
    *,
    start_date: str,
    end_date: str,
    row_limit: int = 25000,
    start_row: int = 0,
    dimensions: Optional[list] = None,
    filter_pages_prefix: Optional[str] = None,
) -> List[Dict]:
    """
    Call Search Analytics query for `dimensions=['page']` and return raw rows.
    NOTE: This returns a sample, NOT a full list of indexed URLs.
    """
    dims = dimensions or ["page"]
    svc = build_service("searchconsole", "v1")  # reuse your existing builder
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dims,
        "rowLimit": row_limit,
        "startRow": start_row,
        # Optional filters: e.g., restrict to a prefix
        # "dimensionFilterGroups": [{
        #   "filters": [{"dimension": "page", "operator": "contains", "expression": "/blog/"}]
        # }]
    }
    res = svc.searchanalytics().query(siteUrl=site_url, body=body).execute()
    return res.get("rows", [])

def url_inspect(site_url: str, url: str) -> Dict[str, Any]:
    """
    URL Inspection API call — returns index status, coverage info, canonical, etc.
    Requires: property ownership for `site_url`.
    """
    svc = build_service("searchconsole", "v1")
    body = {"inspectionUrl": url, "siteUrl": site_url}
    return svc.urlInspection().index().inspect(body=body).execute()
