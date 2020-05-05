from datetime import date, time

from django.utils.timezone import datetime

from .models import Block


def find_availability(
    start: datetime, end: datetime, blocks: [Block]
) -> [(datetime, datetime)]:
    blocks = sorted(blocks, key=lambda k: k.start)

    available = [(start, end)]

    for block in blocks:
        for start, end in available:
            if block.overlaps(start, end):
                available.remove((start, end))
                if start < block.start and end <= block.end:
                    available.append((start, block.start))
                elif start < block.start and end > block.end:
                    available.append((start, block.start))
                    available.append((block.end, end))
                elif start >= block.start and end > block.end:
                    available.append((block.end, end))
                else:
                    pass  # the availability and block are the same

    return available
