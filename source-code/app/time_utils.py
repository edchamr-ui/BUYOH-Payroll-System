"""Application-wide time helpers."""

from datetime import UTC, datetime


def legacy_utc_now():
    """Return naive UTC for existing ``DateTime`` database columns.

    The current schema stores timestamps without timezone information.  Build
    the value from an aware UTC datetime to avoid the deprecated naive UTC
    constructor while
    preserving the established database representation.  A future schema
    migration can move these columns to timezone-aware storage separately.
    """

    return datetime.now(UTC).replace(tzinfo=None)
