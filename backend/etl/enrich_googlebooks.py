import os
from typing import Optional, List, Tuple
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt
from dotenv import load_dotenv

load_dotenv()

GB = "https://www.googleapis.com/books/v1/volumes"

@retry(wait=wait_exponential(multiplier=0.5, max=8), stop=stop_after_attempt(3))
def fetch_by_isbn(isbn13: str) -> dict:
    key = os.getenv("GOOGLE_BOOKS_API_KEY")
    params = {"q": f"isbn:{isbn13}", "projection": "full"}
    if key: params["key"] = key
    r = httpx.get(GB, params=params, timeout=15)
    r.raise_for_status()
    items = r.json().get("items") or []
    return items[0] if items else {}

def parse_gb_payload(item: dict) -> Tuple[Optional[str], List[str], Optional[int], Optional[int]]:
    vi = item.get("volumeInfo", {})
    desc = vi.get("description")
    cats = vi.get("categories") or []
    pages = vi.get("pageCount")
    year = None
    if vi.get("publishedDate"):
        year = int(vi["publishedDate"][:4]) if vi["publishedDate"][:4].isdigit() else None
    return desc, cats[:10], pages, year
