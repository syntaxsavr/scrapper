from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from scraper_kaggle import KaggleScraperSelenium
from contextlib import asynccontextmanager
from threading import Lock


# how to run this?
# uvicorn scraper_kaggle_service:app --host 127.0.0.1 --port 8101
@asynccontextmanager
async def lifespan(app: FastAPI):
    global scraper
    scraper = KaggleScraperSelenium()
    try:
        yield
        if scraper is not None:
            scraper.close()
            scraper = None
    finally:
        # clean up items this is similarly done with db-connections, finally gets executed no matter what
        if scraper is not None:
            scraper.close()
            scraper = None


scraper = None
app = FastAPI(lifespan=lifespan)
busy_lock = Lock()


@app.post("/scrape")
async def scrape(query: str, limit: int):
    acquired = busy_lock.acquire(blocking=False)
    if not acquired:
        raise HTTPException(status_code=423, detail="busy")

    try:
        # results = scraper.scrape(query)
        results = await run_in_threadpool(scraper.scrape, query, limit)
        ans = []
        for r in results:
            ans.append(
                {
                    "title": r["title"],
                    "link": r["link"],
                    "thumbnail": r["thumbnail"],
                    "date": r["date"],
                    "query": query,
                }
            )
        return ans
    finally:
        busy_lock.release()


@app.get("/status")
async def status():
    if busy_lock.locked():
        return {"status": "busy"}
    else:
        return {"status": "ready"}
