"""Job Status Enum Module."""
from enum import unique, IntEnum


@unique
class JobStatus(IntEnum):
    """Job status enum."""

    NEW = 0
    SUBMITTED = 1
    DONE = 2
