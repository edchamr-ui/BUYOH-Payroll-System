import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


class Config:
    """Base configuration for the BUYOH Payroll System."""

    SECRET_KEY = os.getenv("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{os.getenv('DATABASE_USER')}:"
        f"{os.getenv('DATABASE_PASSWORD')}@"
        f"{os.getenv('DATABASE_HOST')}:"
        f"{os.getenv('DATABASE_PORT')}/"
        f"{os.getenv('DATABASE_NAME')}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
