"""Development entry point for the BUYOH Payroll application."""

from app import create_app


app = create_app()


if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
