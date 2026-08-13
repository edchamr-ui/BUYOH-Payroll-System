"""Integrate structured logging and safe error handling."""

from pathlib import Path


def update_factory(root):
    path = root / "app" / "__init__.py"
    source = path.read_text(encoding="utf-8")
    import_block = (
        "from app.observability import (\n"
        "    configure_logging,\n"
        "    register_error_handlers,\n"
        "    register_request_observability,\n"
        ")\n"
    )
    if import_block not in source:
        anchor = "from app.health import health_bp\n"
        if anchor not in source:
            raise RuntimeError("Could not locate app-factory import anchor.")
        source = source.replace(anchor, anchor + import_block, 1)

    setup = (
        "    configure_logging(app)\n"
        "    register_request_observability(app)\n"
        "    register_error_handlers(app)\n\n"
    )
    if setup not in source:
        anchor = "    register_security_headers(app)\n\n"
        if anchor not in source:
            raise RuntimeError("Could not locate app-factory setup anchor.")
        source = source.replace(anchor, anchor + setup, 1)
    path.write_text(source, encoding="utf-8")


def update_config(root):
    path = root / "config.py"
    source = path.read_text(encoding="utf-8")
    line = '    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()\n'
    if line not in source:
        anchor = '    DEBUG = env_bool("FLASK_DEBUG", False)\n'
        if anchor not in source:
            raise RuntimeError("Could not locate configuration anchor.")
        source = source.replace(anchor, anchor + line, 1)
    path.write_text(source, encoding="utf-8")


def update_env_example(root):
    path = root / ".env.example"
    source = path.read_text(encoding="utf-8")
    if "LOG_LEVEL=" not in source:
        source = source.rstrip() + "\n\n# Logging\nLOG_LEVEL=INFO\n"
    path.write_text(source, encoding="utf-8")


def main():
    root = Path(__file__).resolve().parents[1]
    update_factory(root)
    update_config(root)
    update_env_example(root)
    print("Production observability integrated.")


if __name__ == "__main__":
    main()
