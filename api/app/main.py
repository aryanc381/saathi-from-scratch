"""Responsible for creating the FastAPI app: it wires the routers and turns every error into one JSON shape."""
import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.models.errors import ApiError
from app.routers import audit, auth, customers, drafts, health

logger = logging.getLogger("saathi")


# Builds the JSON body every error uses: { "error": { code, message } }.
def error_response(status, code, message):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


# Turns an expected ApiError into the standard error body.
def handle_api_error(request, error):
    return error_response(error.status, error.code, error.message)


# Turns a bad request body or query into a 400 that names the field but never echoes the input.
def handle_validation_error(request, error):
    first = error.errors()[0]
    field = ".".join(str(part) for part in first["loc"])
    return error_response(400, "validation_error", f"{field}: {first['msg']}")


# Logs an unexpected error and returns a 500 with no internal details.
def handle_unexpected_error(request, error):
    logger.exception("Unhandled error")
    return error_response(500, "internal_error", "Something went wrong")


# Creates the app, registers the routers and the error handlers.
def create_app():
    app = FastAPI(title="Saathi API")
    for module in (health, auth, customers, drafts, audit):
        app.include_router(module.router)
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
    return app


app = create_app()
