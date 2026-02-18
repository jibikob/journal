from fastapi import FastAPI

app = FastAPI(title="Personal Journal API")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
