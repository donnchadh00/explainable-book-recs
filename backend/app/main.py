from fastapi import FastAPI

app = FastAPI(title="Book Recs API")

@app.get("/health")
async def health():
    return {"status": "ok"}
