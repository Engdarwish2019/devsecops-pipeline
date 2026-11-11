"""Small inventory API used to demonstrate a secure delivery pipeline."""

import os
import threading
import time
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field, StringConstraints
from starlette.routing import Match

APP_VERSION = os.getenv("APP_VERSION", "dev")

# Labelled by route template ("/api/v1/items/{item_id}"), never by raw path, so label
# cardinality stays fixed. Argo Rollouts reads the 5xx ratio of these during a canary.
REQUESTS = Counter("http_requests_total", "HTTP requests handled.", ["method", "route", "status"])
LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency in seconds.", ["method", "route"])

app = FastAPI(
    title="demo-api",
    version=APP_VERSION,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
}


def route_template(request: Request) -> str:
    for route in request.app.router.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return route.path
    return "unmatched"


@app.middleware("http")
async def add_security_headers_and_metrics(request: Request, call_next) -> Response:
    route = route_template(request)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        REQUESTS.labels(request.method, route, "500").inc()
        raise
    REQUESTS.labels(request.method, route, str(response.status_code)).inc()
    LATENCY.labels(request.method, route).observe(time.perf_counter() - start)
    response.headers.update(SECURITY_HEADERS)
    return response


ItemName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64, pattern=r"^[\w .-]+$")]


class ItemIn(BaseModel):
    name: ItemName
    quantity: int = Field(ge=0, le=1_000_000)


class Item(ItemIn):
    id: int


_items: dict[int, Item] = {}
_lock = threading.Lock()


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "demo-api", "version": APP_VERSION}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/items")
def list_items() -> list[Item]:
    with _lock:
        return list(_items.values())


@app.post("/api/v1/items", status_code=201)
def create_item(item: ItemIn) -> Item:
    with _lock:
        if len(_items) >= 1000:
            raise HTTPException(status_code=507, detail="Item limit reached")
        new = Item(id=len(_items) + 1, **item.model_dump())
        _items[new.id] = new
        return new


@app.get("/api/v1/items/{item_id}")
def get_item(item_id: int) -> Item:
    with _lock:
        item = _items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
