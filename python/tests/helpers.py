from __future__ import annotations

import json
import os
import pathlib
import re
import sqlite3
import sys
import threading
import types
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

from kolo.db import setup_db
from kolo.profiler import KoloProfiler

if TYPE_CHECKING:
    from django.http import HttpResponse


def wait_for_save_in_db() -> None:
    """Pause execution of the main thread until the db is ready"""
    for thread in threading.enumerate():
        if thread.name == "kolo-save_request_in_db":
            thread.join()


class ExtractFrames:
    """
    Save the arguments passed to a sys.setprofile callback for testing

    The code run in a profiling callback cannot be traced by sys.settrace,
    which means we cannot get coverage information from normal execution.
    Instead, we can save the frame, event and arg arguments in self.frames
    for test code to process explicitly. By passing these arguments to the
    callback we want to test, we gain coverage reporting for the callback.

    https://github.com/nedbat/coveragepy/commit/9288ef767b461153c297f98e8d2989b796c41bba
    """

    def __init__(self) -> None:
        self.frames: List[Tuple[types.FrameType, str, object]] = []

    def __call__(self, frame: types.FrameType, event: str, arg: object) -> None:
        # Skip recording frames for ExtractFrames.__exit__
        if (
            os.path.normpath("tests/helpers") not in frame.f_code.co_filename
        ):  # pragma: no cover
            self.frames.append((frame, event, arg))  # pragma: no cover

    def __enter__(self):
        sys.setprofile(self)
        return self

    def __exit__(self, *exc):
        sys.setprofile(None)

    def __iter__(self):
        yield from self.frames


def profile_view(view, headers=None, config=None) -> "HttpResponse":
    from kolo.middleware import KoloMiddleware
    from django.test import RequestFactory
    from django.urls import get_resolver

    if headers is None:
        headers = {}
    if config is None:  # pragma: no branch
        config = {}  # pragma: no cover

    db_path = setup_db()

    request = RequestFactory().get(f"/{view.__name__}", **headers)
    request.resolver_match = get_resolver().resolve(request.path_info)

    profiler = KoloProfiler(db_path, config=config)
    view = KoloMiddleware(view)

    with ExtractFrames() as extract_frames:
        response = view(request)

    for frame in extract_frames:
        profiler(*frame)

    profiler.save_request_in_db()

    return response


def profile_view_frozen_time(
    view, time, config=None
) -> Tuple["HttpResponse", datetime]:
    from kolo.middleware import KoloMiddleware
    from django.test import RequestFactory
    from django.urls import get_resolver
    from freezegun import freeze_time

    if config is None:  # pragma: no branch
        config = {}  # pragma: no cover

    db_path = setup_db()

    request = RequestFactory().get(f"/{view.__name__}")
    request.resolver_match = get_resolver().resolve(request.path_info)

    profiler = KoloProfiler(db_path, config=config)
    view = KoloMiddleware(view)

    with ExtractFrames() as extract_frames:
        response = view(request)

    with freeze_time(time):
        now = datetime.now(timezone.utc)
        for frame in extract_frames:
            profiler(*frame)

    profiler.save_request_in_db()

    return response, now


def load_data_from_db(db_path: pathlib.Path) -> Tuple[Dict[str, Any], str]:
    connection = sqlite3.connect(str(db_path))
    cursor = connection.execute(
        "select id, data from invocations order by created_at desc"
    )
    id, raw_data = cursor.fetchone()
    connection.close()
    return json.loads(raw_data), id


def load_rows_from_db(db_path: pathlib.Path) -> List[Tuple[Dict[str, Any], str]]:
    connection = sqlite3.connect(str(db_path))
    cursor = connection.execute(
        "select id, data from invocations order by created_at desc"
    )
    rows = cursor.fetchall()
    connection.close()
    return [(json.loads(raw_data), id) for id, raw_data in reversed(rows)]


def format_timestamp(timestamp: datetime) -> str:
    from django.db import connection

    if connection.vendor == "postgresql":
        return f"'{timestamp.isoformat()}'::timestamp"
    elif connection.vendor == "microsoft":
        return f"{timestamp}"
    return f"'{timestamp}'"


class RegexString:
    def __init__(self, regex: str):
        self.regex = re.compile(regex)

    def __eq__(self, other):
        if not isinstance(other, str):
            return False
        return bool(self.regex.fullmatch(other))

    def __repr__(self):
        return rf"RegexString(r'{self.regex.pattern}')"


def assert_issuperset(big: Dict[Any, Any], small: Dict[Any, Any]) -> None:
    from pprint import pprint

    print()
    pprint(big)
    pprint(small)
    assert {**big, **small} == big
