import re
from typing import Optional, Tuple, List, Dict
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt

OL_BOOKS  = "https://openlibrary.org/api/books"
OL_SEARCH = "https://openlibrary.org/search.json"
OL_BASE   = "https://openlibrary.org"

def _clean_year(s: Optional[str]) -> Optional[int]:
    if not s: return None
    m = re.search(r"(19|20)\d{2}", s)
    return int(m.group(0)) if m else None

def _extract_description(obj: dict) -> Optional[str]:
    d = obj.get("description")
    if isinstance(d, dict):
        return (d.get("value") or "").strip() or None
    if isinstance(d, str):
        return d.strip() or None
    return None

@retry(wait=wait_exponential(multiplier=0.5, max=8), stop=stop_after_attempt(3))
def fetch_by_isbn(isbn13: str) -> dict:
    params = {"bibkeys": f"ISBN:{isbn13}", "jscmd": "data", "format": "json"}
    r = httpx.get(OL_BOOKS, params=params, timeout=10)
    r.raise_for_status()
    return r.json().get(f"ISBN:{isbn13}") or {}

def fetch_json(path: str) -> dict:
    url = path if path.startswith("http") else f"{OL_BASE}{path}"
    if not url.endswith(".json"):
        url += ".json"
    r = httpx.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

def parse_ol_payload(d: dict) -> Tuple[Optional[str], List[str], Optional[int], Optional[int]]:
    """Parse edition payload; hop to Work for description/subjects if needed."""
    desc = _extract_description(d)
    subjects = [s["name"] for s in d.get("subjects", []) if "name" in s][:10]
    pages = d.get("number_of_pages")
    year = _clean_year(d.get("publish_date"))

    # hop: edition -> work
    ed_key = d.get("key")
    if not ed_key:
        ol_ids = (d.get("identifiers", {}).get("openlibrary") or [])
        if ol_ids:
            ed_key = f"/books/{ol_ids[0]}"
    if ed_key:
        try:
            ed_json = fetch_json(ed_key)
            works = ed_json.get("works") or []
            wk_key = works[0].get("key") if works else None
            if wk_key:
                wk = fetch_json(wk_key)
                desc = desc or _extract_description(wk)
                if not subjects:
                    subs = wk.get("subjects") or []
                    if isinstance(subs, list):
                        subjects = [str(s) for s in subs][:10]
        except Exception:
            pass

    return desc, subjects, pages, year

# Work search by title+author
@retry(wait=wait_exponential(multiplier=0.5, max=8), stop=stop_after_attempt(3))
def fetch_work_by_title_author(title: str, author: Optional[str]) -> Optional[dict]:
    params = {"title": title, "limit": 1}
    if author:
        params["author"] = author
    r = httpx.get(OL_SEARCH, params=params, timeout=10)
    r.raise_for_status()
    docs = r.json().get("docs") or []
    if not docs:
        return None
    wk_key = docs[0].get("key")
    if not wk_key:
        return None
    return fetch_json(wk_key)

def parse_work_payload(work: dict) -> Tuple[Optional[str], List[str]]:
    desc = _extract_description(work)
    subs = work.get("subjects") or []
    if isinstance(subs, list):
        subs = [str(s) for s in subs][:10]
    else:
        subs = []
    return desc, subs
