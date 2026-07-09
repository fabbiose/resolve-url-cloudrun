from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse, urlunparse
from playwright.sync_api import sync_playwright
import time

app = FastAPI()

class ResolveRequest(BaseModel):
    url: str

def clean_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/resolve")
def resolve(payload: ResolveRequest):
    try:
        start_host = urlparse(payload.url).netloc
        final_url = payload.url

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

            try:
                page.goto(payload.url, wait_until="commit", timeout=15000)
            except Exception:
                pass

            deadline = time.time() + 20

            while time.time() < deadline:
                current_url = page.url
                current_host = urlparse(current_url).netloc

                if current_url != "about:blank":
                    final_url = current_url

                if current_host and current_host != start_host:
                    break

                page.wait_for_timeout(500)

            browser.close()

        return {
            "final_url": final_url,
            "clean_url": clean_url(final_url)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
