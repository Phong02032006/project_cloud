import os
import re


def _fix_database_url(url):
    if not url:
        return "sqlite:///quiz.db"
    # Azure SQL via pymssql requires username@servername if not already provided
    m = re.match(r"^(mssql\+pymssql://)([^:@]+)(:[^@]+@)([^.]+)(\.database\.windows\.net.*)$", url)
    if m:
        prefix, user, pass_at, server, rest = m.groups()
        if "@" not in user and "%40" not in user:
            return f"{prefix}{user}%40{server}{pass_at}{server}{rest}"
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    # Reject oversized requests before they are buffered; the largest upload is a 10 MB lesson document.
    MAX_CONTENT_LENGTH = 12 * 1024 * 1024
    # Local: SQLite. Azure: mssql+pymssql://USER:PASSWORD@SERVER.database.windows.net:1433/DBNAME
    SQLALCHEMY_DATABASE_URI = _fix_database_url(os.environ.get("DATABASE_URL", "sqlite:///quiz.db"))
    # pool_pre_ping matters for Azure SQL serverless (free offer), which auto-pauses and drops idle connections.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # "dev" = pick a role on a login form (local only); "entra" = Microsoft Entra External ID.
    AUTH_MODE = os.environ.get("AUTH_MODE", "dev")
    ENTRA_CLIENT_ID = os.environ.get("ENTRA_CLIENT_ID", "")
    ENTRA_CLIENT_SECRET = os.environ.get("ENTRA_CLIENT_SECRET", "")
    # e.g. https://<tenant-subdomain>.ciamlogin.com/<tenant-subdomain>.onmicrosoft.com
    ENTRA_AUTHORITY = os.environ.get("ENTRA_AUTHORITY", "")

    # Empty GRADER_URL = grade in-process and store PDFs locally (no AWS needed).
    GRADER_URL = os.environ.get("GRADER_URL", "")
    GRADER_SECRET = os.environ.get("GRADER_SECRET", "")
    # true = queue submissions on SQS and receive results via /api/grader/callback (needs GRADER_URL).
    GRADER_ASYNC = os.environ.get("GRADER_ASYNC", "").lower() in ("1", "true", "yes")
    LOCAL_CERT_DIR = os.environ.get("LOCAL_CERT_DIR", "")

    # Optional: Azure Blob Storage for question images.
    AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
    AZURE_STORAGE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER", "question-images")

    # Optional: Azure OpenAI for automatic MCQ generation.
    AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
    AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")

    # Optional: Azure Web PubSub for real-time exam monitoring and tab-leave alerts.
    AZURE_WEBPUBSUB_CONNECTION_STRING = os.environ.get("AZURE_WEBPUBSUB_CONNECTION_STRING", "")
    AZURE_WEBPUBSUB_HUB = os.environ.get("AZURE_WEBPUBSUB_HUB", "quizcloud")
