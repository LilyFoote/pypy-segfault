import asyncio
import json

import httpretty
import httpx


def register_github_api_user_response() -> None:
    with open("tests/api_responses/wilhelmklopp.json") as body:
        with open("tests/api_responses/wilhelmklopp-headers.json") as headers:
            httpretty.register_uri(
                httpretty.GET,
                "https://api.github.com/users/wilhelmklopp",
                body=body.read(),
                headers=json.load(headers),
            )


def register_github_api_invalid_response() -> None:
    with open("tests/api_responses/wilhelmklopp-headers.json") as headers:
        httpretty.register_uri(
            httpretty.GET,
            "https://api.github.com/invalid",
            body=json.dumps(
                {
                    "message": "Not Found",
                    "documentation_url": "https://docs.github.com/rest",
                }
            ),
            headers=json.load(headers),
            status=404,
        )


def register_github_api_invalid_post_response() -> None:
    with open("tests/api_responses/wilhelmklopp-headers.json") as headers:
        httpretty.register_uri(
            httpretty.POST,
            "https://api.github.com/invalid",
            body=json.dumps(
                {
                    "message": "Not Found",
                    "documentation_url": "https://docs.github.com/rest",
                }
            ),
            headers=json.load(headers),
            status=404,
        )


def register_github_api_user_response_httpx(httpx_mock):
    with open("tests/api_responses/wilhelmklopp.json") as body:
        with open("tests/api_responses/wilhelmklopp-headers.json") as headers:
            httpx_mock.add_response(
                method="GET",
                url="https://api.github.com/users/wilhelmklopp",
                json=json.load(body),
                headers=json.load(headers),
            )


async def pause(request):
    await asyncio.sleep(0.01)
    with open("tests/api_responses/wilhelmklopp.json") as body:
        with open("tests/api_responses/wilhelmklopp-headers.json") as headers:
            return httpx.Response(
                status_code=200,
                json=json.load(body),
                headers=json.load(headers),
            )


def register_github_api_user_response_httpx_async(httpx_mock):
    httpx_mock.add_callback(pause)
