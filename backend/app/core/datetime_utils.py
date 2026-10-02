from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return a naive datetime representing the current UTC time.
    
    Avoids deprecated datetime.utcnow() in Python 3.12+ while maintaining
    full compatibility with offset-naive SQLite and PostgreSQL DateTime columns.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
