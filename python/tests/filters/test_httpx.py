import json
import threading

import httpx
import pytest

import kolo
from kolo.db import setup_db
from kolo.profiler import KoloProfiler

from .httpretty_responses import (
    register_github_api_user_response_httpx,
    register_github_api_user_response_httpx_async,
)
from ..helpers import ExtractFrames, load_data_from_db


@pytest.mark.parametrize("use_rust", (False, True))
def test_get_sync(kolo_storage, use_rust, httpx_mock):
    register_github_api_user_response_httpx(httpx_mock)

    url = "https://api.github.com/users/wilhelmklopp"
    with kolo.enable(config={"use_rust": use_rust}):
        r = httpx.get(url)

    response_data = r.json()
    assert response_data["name"] == "Wilhelm Klopp"

    data, _id = load_data_from_db(kolo_storage.db_path)
    frames = data["frames_of_interest"]

    thread = threading.current_thread()
    api_request, api_response = frames
    assert api_request["type"] == "outbound_http_request"
    assert api_request["body"] is None
    assert "frame_id" in api_request
    assert api_request["headers"] == {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate",
        "connection": "keep-alive",
        "host": "api.github.com",
        "user-agent": f"python-httpx/{httpx.__version__}",
    }
    assert api_request["method"] == "GET"
    assert api_request["method_and_full_url"] == f"GET {url}"
    assert api_request["thread"] == "MainThread"
    assert api_request["thread_native_id"] == thread.native_id
    assert "timestamp" in api_request
    assert api_request["url"] == url

    assert api_response["type"] == "outbound_http_response"
    assert json.loads(api_response["body"]) == response_data
    assert api_response["frame_id"] == api_request["frame_id"]
    assert api_response["status_code"] == 200
    assert api_response["headers"]["server"] == "GitHub.com"
    assert api_response["method"] == "GET"
    assert api_response["method_and_full_url"] == f"GET {url}"
    assert api_response["thread"] == "MainThread"
    assert api_response["thread_native_id"] == thread.native_id
    assert api_response["timestamp"] >= api_request["timestamp"]
    assert api_response["url"] == url


@pytest.mark.parametrize("use_rust", (False, True))
def test_get_streaming_response(kolo_storage, use_rust, httpx_mock):
    register_github_api_user_response_httpx(httpx_mock)

    url = "https://api.github.com/users/wilhelmklopp"
    with kolo.enable(config={"use_rust": use_rust}):
        with httpx.stream("GET", url) as r:
            r.read()
            response_data = r.json()

    assert response_data["name"] == "Wilhelm Klopp"

    data, _id = load_data_from_db(kolo_storage.db_path)
    frames = data["frames_of_interest"]

    api_request, api_response = frames
    assert api_request["type"] == "outbound_http_request"
    assert api_response["type"] == "outbound_http_response"
    assert api_response["body"] is None


@pytest.mark.parametrize("use_rust", (False, True))
def test_get_binary_response(kolo_storage, use_rust, httpx_mock):
    url = "https://api.github.com/users/wilhelmklopp"
    body = "utf-32 body".encode("utf-32")
    httpx_mock.add_response("GET", url=url, content=body)

    with kolo.enable(config={"use_rust": use_rust}):
        httpx.get(url)

    data, _id = load_data_from_db(kolo_storage.db_path)
    frames = data["frames_of_interest"]

    api_request, api_response = frames
    assert api_request["type"] == "outbound_http_request"
    assert api_response["type"] == "outbound_http_response"
    assert api_response["body"] == body.decode("utf-8", errors="replace")


@pytest.mark.asyncio
@pytest.mark.parametrize("use_rust", (False, True))
async def test_get_async(kolo_storage, use_rust, httpx_mock):
    register_github_api_user_response_httpx_async(httpx_mock)

    url = "https://api.github.com/users/wilhelmklopp"
    with kolo.enable(config={"use_rust": use_rust}):
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            await client.get(url)

    response_data = r.json()
    assert response_data["name"] == "Wilhelm Klopp"

    data, _id = load_data_from_db(kolo_storage.db_path)
    frames = data["frames_of_interest"]
    api_frames = [frame for frame in frames if "outbound_http_" in frame["type"]]

    thread = threading.current_thread()
    api_request, api_response, api_request_2, api_response_2 = api_frames
    assert api_request["type"] == "outbound_http_request"
    assert api_request["body"] is None
    assert "frame_id" in api_request
    assert api_request["headers"] == {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate",
        "connection": "keep-alive",
        "host": "api.github.com",
        "user-agent": f"python-httpx/{httpx.__version__}",
    }
    assert api_request["method"] == "GET"
    assert api_request["method_and_full_url"] == f"GET {url}"
    assert api_request["thread"] == "MainThread"
    assert api_request["thread_native_id"] == thread.native_id
    assert "timestamp" in api_request
    assert api_request["url"] == url

    assert api_response["type"] == "outbound_http_response"
    assert json.loads(api_response["body"]) == response_data
    assert api_response["frame_id"] == api_request["frame_id"]
    assert api_response["headers"]["server"] == "GitHub.com"
    assert api_response["method"] == "GET"
    assert api_response["method_and_full_url"] == f"GET {url}"
    assert api_response["status_code"] == 200
    assert api_response["thread"] == "MainThread"
    assert api_response["thread_native_id"] == thread.native_id
    assert api_response["timestamp"] >= api_request["timestamp"]
    assert api_response["url"] == url

    assert api_request_2["type"] == "outbound_http_request"
    assert api_request_2["body"] is None
    assert "frame_id" in api_request_2
    assert api_request_2["headers"] == {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate",
        "connection": "keep-alive",
        "host": "api.github.com",
        "user-agent": f"python-httpx/{httpx.__version__}",
    }
    assert api_request_2["method"] == "GET"
    assert api_request_2["method_and_full_url"] == f"GET {url}"
    assert api_request_2["thread"] == "MainThread"
    assert api_request_2["thread_native_id"] == thread.native_id
    assert "timestamp" in api_request_2
    assert api_request_2["url"] == url

    assert api_response_2["type"] == "outbound_http_response"
    assert json.loads(api_response_2["body"]) == response_data
    assert api_response_2["frame_id"] == api_request_2["frame_id"]
    assert api_response_2["headers"]["server"] == "GitHub.com"
    assert api_response_2["method"] == "GET"
    assert api_response_2["method_and_full_url"] == f"GET {url}"
    assert api_response_2["status_code"] == 200
    assert api_response_2["thread"] == "MainThread"
    assert api_response_2["thread_native_id"] == thread.native_id
    assert api_response_2["timestamp"] >= api_request_2["timestamp"]
    assert api_response_2["url"] == url

    assert api_request["frame_id"] != api_request_2["frame_id"]


def test_get_sync_coverage(kolo_storage, httpx_mock):
    register_github_api_user_response_httpx(httpx_mock)
    db_path = setup_db()
    profiler = KoloProfiler(db_path)

    url = "https://api.github.com/users/wilhelmklopp"
    with ExtractFrames() as extract_frames:
        r = httpx.get(url)

    for frame in extract_frames:
        profiler(*frame)
    profiler.save_request_in_db()

    response_data = r.json()
    assert response_data["name"] == "Wilhelm Klopp"

    data, _id = load_data_from_db(kolo_storage.db_path)
    frames = data["frames_of_interest"]

    thread = threading.current_thread()
    api_request, api_response = frames
    assert api_request["type"] == "outbound_http_request"
    assert api_request["body"] is None
    assert "frame_id" in api_request
    assert api_request["headers"] == {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate",
        "connection": "keep-alive",
        "host": "api.github.com",
        "user-agent": f"python-httpx/{httpx.__version__}",
    }
    assert api_request["method"] == "GET"
    assert api_request["method_and_full_url"] == f"GET {url}"
    assert api_request["thread"] == "MainThread"
    assert api_request["thread_native_id"] == thread.native_id
    assert "timestamp" in api_request
    assert api_request["url"] == url

    assert api_response["type"] == "outbound_http_response"
    assert json.loads(api_response["body"]) == response_data
    assert api_response["frame_id"] == api_request["frame_id"]
    assert api_response["status_code"] == 200
    assert api_response["headers"]["server"] == "GitHub.com"
    assert api_response["method"] == "GET"
    assert api_response["method_and_full_url"] == f"GET {url}"
    assert api_response["thread"] == "MainThread"
    assert api_response["thread_native_id"] == thread.native_id
    assert api_response["timestamp"] >= api_request["timestamp"]
    assert api_response["url"] == url


def test_get_binary_response_coverage(kolo_storage, httpx_mock):
    url = "https://api.github.com/users/wilhelmklopp"
    body = "utf-32 body".encode("utf-32")
    httpx_mock.add_response("GET", url=url, content=body)

    db_path = setup_db()
    profiler = KoloProfiler(db_path)

    with ExtractFrames() as extract_frames:
        httpx.get(url)

    for frame in extract_frames:
        profiler(*frame)
    profiler.save_request_in_db()

    data, _id = load_data_from_db(kolo_storage.db_path)
    frames = data["frames_of_interest"]

    api_request, api_response = frames
    assert api_request["type"] == "outbound_http_request"
    assert api_response["type"] == "outbound_http_response"
    assert api_response["body"] == body.decode("utf-8", errors="replace")


@pytest.mark.asyncio
async def test_get_async_coverage(kolo_storage, httpx_mock):
    register_github_api_user_response_httpx_async(httpx_mock)
    db_path = setup_db()
    profiler = KoloProfiler(db_path)

    url = "https://api.github.com/users/wilhelmklopp"
    with ExtractFrames() as extract_frames:
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            await client.get(url)

    for frame in extract_frames:
        profiler(*frame)
    profiler.save_request_in_db()

    response_data = r.json()
    assert response_data["name"] == "Wilhelm Klopp"

    data, _id = load_data_from_db(kolo_storage.db_path)
    frames = data["frames_of_interest"]
    api_frames = [frame for frame in frames if "outbound_http_" in frame["type"]]

    thread = threading.current_thread()
    api_request, api_response, api_request_2, api_response_2 = api_frames
    assert api_request["type"] == "outbound_http_request"
    assert api_request["body"] is None
    assert "frame_id" in api_request
    assert api_request["headers"] == {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate",
        "connection": "keep-alive",
        "host": "api.github.com",
        "user-agent": f"python-httpx/{httpx.__version__}",
    }
    assert api_request["method"] == "GET"
    assert api_request["method_and_full_url"] == f"GET {url}"
    assert api_request["thread"] == "MainThread"
    assert api_request["thread_native_id"] == thread.native_id
    assert "timestamp" in api_request
    assert api_request["url"] == url

    assert api_response["type"] == "outbound_http_response"
    assert json.loads(api_response["body"]) == response_data
    assert api_response["frame_id"] == api_request["frame_id"]
    assert api_response["headers"]["server"] == "GitHub.com"
    assert api_response["method"] == "GET"
    assert api_response["method_and_full_url"] == f"GET {url}"
    assert api_response["status_code"] == 200
    assert api_response["thread"] == "MainThread"
    assert api_response["thread_native_id"] == thread.native_id
    assert api_response["timestamp"] >= api_request["timestamp"]
    assert api_response["url"] == url

    assert api_request_2["type"] == "outbound_http_request"
    assert api_request_2["body"] is None
    assert "frame_id" in api_request_2
    assert api_request_2["headers"] == {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate",
        "connection": "keep-alive",
        "host": "api.github.com",
        "user-agent": f"python-httpx/{httpx.__version__}",
    }
    assert api_request_2["method"] == "GET"
    assert api_request_2["method_and_full_url"] == f"GET {url}"
    assert api_request_2["thread"] == "MainThread"
    assert api_request_2["thread_native_id"] == thread.native_id
    assert "timestamp" in api_request_2
    assert api_request_2["url"] == url

    assert api_response_2["type"] == "outbound_http_response"
    assert json.loads(api_response_2["body"]) == response_data
    assert api_response_2["frame_id"] == api_request_2["frame_id"]
    assert api_response_2["headers"]["server"] == "GitHub.com"
    assert api_response_2["method"] == "GET"
    assert api_response_2["method_and_full_url"] == f"GET {url}"
    assert api_response_2["status_code"] == 200
    assert api_response_2["thread"] == "MainThread"
    assert api_response_2["thread_native_id"] == thread.native_id
    assert api_response_2["timestamp"] >= api_request_2["timestamp"]
    assert api_response_2["url"] == url

    assert api_request["frame_id"] != api_request_2["frame_id"]
