"""Apply the small integration edits for secure runtime configuration."""

from pathlib import Path


def update_app_factory(root):
    path = root / "app" / "__init__.py"
    source = path.read_text(encoding="utf-8")
    import_line = (
        "from app.security import register_security_headers, "
        "validate_runtime_config\n"
    )
    if import_line not in source:
        anchor = "from app.extensions import db, login_manager, migrate\n"
        if anchor not in source:
            raise RuntimeError("Could not locate app-factory import anchor.")
        source = source.replace(anchor, anchor + import_line, 1)

    call_block = (
        "    validate_runtime_config(app)\n"
        "    register_security_headers(app)\n\n"
    )
    if call_block not in source:
        anchor = "    if config_overrides:\n        app.config.update(config_overrides)\n\n"
        if anchor not in source:
            raise RuntimeError("Could not locate app-factory configuration anchor.")
        source = source.replace(anchor, anchor + call_block, 1)

    path.write_text(source, encoding="utf-8")


def update_gitignore(root):
    path = root / ".gitignore"
    source = path.read_text(encoding="utf-8")
    additions = "\n# Local secrets\n.env\n.env.*\n!.env.example\ninstance/\n"
    if "!.env.example" not in source:
        source = source.rstrip() + additions
    path.write_text(source, encoding="utf-8")


def main():
    root = Path(__file__).resolve().parents[1]
    update_app_factory(root)
    update_gitignore(root)
    print("Secure configuration integration applied.")


if __name__ == "__main__":
    main()
