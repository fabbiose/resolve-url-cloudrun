from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse, urlunparse, urljoin
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

def resolve_redirects(url: str) -> tuple[str, list[str]]:
    session = requests.Session()

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Connection": "close"
    }

    current_url = url
    chain = [current_url]

    for _ in range(10):
        try:
            response = session.get(
                current_url,
                headers=headers,
                allow_redirects=False,
                timeout=(8, 8),
                stream=True
            )

            status = response.status_code
            location = response.headers.get("Location")
            response.close()

            if status in [301, 302, 303, 307, 308] and location:
                next_url = urljoin(current_url, location)
                current_url = next_url
                chain.append(current_url)
                continue

            return current_url, chain

        except requests.exceptions.ReadTimeout:
            return current_url, chain

        except requests.exceptions.ConnectTimeout:
            return current_url, chain

    return current_url, chain

@app.post("/resolve")
def resolve(payload: ResolveRequest):
    try:
        final_url, chain = resolve_redirects(payload.url)

        return {
            "final_url": final_url,
            "clean_url": clean_url(final_url),
            "redirect_chain": chain
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
