from datetime import datetime
from decimal import Decimal
from typing import Any
from prisma.bases import _PrismaModel


def format_rows(stats: list):
    for record in stats:
        yield format_row(record)

def format_row(record: Any):
    record_dict = dict(record)
    for key, value in record_dict.items():
        if isinstance(value, Decimal):
            record_dict[key] = float(value)
        
        if isinstance(value, datetime):
            record_dict[key] = value.isoformat(timespec="seconds")
        
        if isinstance(value, _PrismaModel):
            record_dict[key] = format_row(value)

    return record_dict