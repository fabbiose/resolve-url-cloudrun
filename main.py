from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse, urlunparse
from playwright.sync_api import sync_playwright

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
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
            )

            page.goto(payload.url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)

            final_url = page.url
            browser.close()

        return {
            "final_url": final_url,
            "clean_url": clean_url(final_url)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
