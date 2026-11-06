"""
Programmer: python_scripts (Abhijith Warrier)
PYTHON BACKEND PATTERNS — CENTRALIZED EXCEPTION HANDLING

Define domain exceptions and translate them at the API boundary into consistent
JSON errors. This read-only stock check demonstrates 404, 409, 422 and safe 500
responses; it does not reserve stock or implement a checkout transaction.

Run: python centralized_exception_handling.py
Serve: uvicorn centralized_exception_handling:app --reload
"""
import json
import logging
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)

# 1. Domain errors describe business failures, without HTTP dependencies.
class DomainError(Exception):
    pass


class ProductNotFound(DomainError):
    pass


class OutOfStock(DomainError):
    pass


def get_catalog() -> dict[int, dict]:
    return {1: {"name": "Notebook", "stock": 3},
            2: {"name": "Pen", "stock": 0}}


def check_availability(product_id: int, catalog: dict[int, dict]) -> dict:
    product = catalog.get(product_id)
    if product is None:
        raise ProductNotFound()
    if product["stock"] <= 0:
        raise OutOfStock()
    return {"product_id": product_id, "available": True}


# 2. HTTP translation belongs to the API layer, not the domain classes.
app = FastAPI(debug=False)
ERROR_MAP = {
    ProductNotFound: (404, "PRODUCT_NOT_FOUND", "Product not found."),
    OutOfStock: (409, "OUT_OF_STOCK", "Product is out of stock."),
}


def error_response(status: int, code: str, message: str,
                   headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(status_code=status,
                        content={"error": {"code": code, "message": message}},
                        headers=headers)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    # Exact-type map: explicitly register each public domain error.
    translated = ERROR_MAP.get(type(exc))
    if translated is None:
        return await unexpected_error_handler(request, exc)
    return error_response(*translated)


# 3. Normalize framework failures through the same response builder.
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return error_response(422, "INVALID_REQUEST", "Request validation failed.")


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    message = {404: "Route not found.", 405: "Method not allowed."}.get(
        exc.status_code, "Request failed.")
    return error_response(exc.status_code, f"HTTP_{exc.status_code}",
                          message, headers=exc.headers)


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    # Traceback stays server-side. Never expose str(exc) to clients.
    # Production logs still need restricted access and redaction policies.
    logger.error("Unhandled API error", exc_info=(type(exc), exc, exc.__traceback__))
    return error_response(500, "INTERNAL_ERROR", "Something went wrong.")


# 4. The endpoint contains no repeated try/except response formatting.
@app.get("/products/{product_id}/availability")
def availability(product_id: int,
                 catalog: Annotated[dict[int, dict], Depends(get_catalog)]):
    return check_availability(product_id, catalog)


# 5. Exercise real request handling in-process, without starting a server.
if __name__ == "__main__":
    with TestClient(app, raise_server_exceptions=False) as client:
        for product_id in (1, 999, 2, "bad"):
            response = client.get(f"/products/{product_id}/availability")
            print(response.status_code, json.dumps(response.json()))
