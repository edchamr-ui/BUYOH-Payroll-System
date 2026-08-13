"""Register the operational health blueprint in the app factory."""

from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    path = root / "app" / "__init__.py"
    source = path.read_text(encoding="utf-8")

    import_line = "from app.health import health_bp\n"
    if import_line not in source:
        anchor = "from app.extensions import db, login_manager, migrate\n"
        if anchor not in source:
            raise RuntimeError("Could not locate app-factory import anchor.")
        source = source.replace(anchor, anchor + import_line, 1)

    registration = "    app.register_blueprint(health_bp)\n"
    if registration not in source:
        anchor = "    register_security_headers(app)\n\n"
        if anchor not in source:
            raise RuntimeError("Could not locate app-factory setup anchor.")
        source = source.replace(anchor, anchor + registration + "\n", 1)

    path.write_text(source, encoding="utf-8")
    print("Health endpoints registered.")


if __name__ == "__main__":
    main()
