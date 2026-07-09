from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse, urlunparse
from playwright.sync_api import sync_playwright
import requests

app = FastAPI()

class ResolveRequest(BaseModel):
    url: str

def clean_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

@app.get("/")
def health():
    return {"status": "ok"}

def resolve_with_requests(url: str) -> str:
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Connection": "close"
    }

    response = session.get(
        url,
        headers=headers,
        allow_redirects=True,
        timeout=30,
        stream=True
    )

    final_url = response.url
    response.close()
    return final_url

def resolve_with_browser(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-http2"
            ]
        )

        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )

        page.goto(url, wait_until="commit", timeout=45000)
        page.wait_for_timeout(5000)

        final_url = page.url
        browser.close()
        return final_url

@app.post("/resolve")
def resolve(payload: ResolveRequest):
    errors = []

    try:
        final_url = resolve_with_browser(payload.url)
        return {
            "method": "browser",
            "final_url": final_url,
            "clean_url": clean_url(final_url)
        }
    except Exception as e:
        errors.append(f"browser: {str(e)}")

    try:
        final_url = resolve_with_requests(payload.url)
        return {
            "method": "requests",
            "final_url": final_url,
            "clean_url": clean_url(final_url),
            "browser_error": errors[0]
        }
    except Exception as e:
        errors.append(f"requests: {str(e)}")

    raise HTTPException(status_code=500, detail=errors)
