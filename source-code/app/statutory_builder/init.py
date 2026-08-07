from flask import Blueprint

statutory_builder_bp = Blueprint(
    "statutory_builder",
    __name__,
    url_prefix="/statutory-builder",
)

from app.statutory_builder import routes
