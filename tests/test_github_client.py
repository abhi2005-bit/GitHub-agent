from __future__ import annotations

import base64

import pytest
import httpx

from app.integrations.github_client import GitHubClient


class FakeGitHubClient(GitHubClient):
    def __init__(self, payload):
        super().__init__(base_url="https://example.invalid")
        self.payload = payload
        self.requests = []

    async def _get_json(self, url, resource_description, params=None):
        self.requests.append((url, params))
        return self.payload


@pytest.mark.asyncio
async def test_get_file_contents_decodes_utf8_and_uses_branch() -> None:
    body = "print('ok')\n".encode()
    client = FakeGitHubClient({
        "type": "file", "size": len(body), "encoding": "base64",
        "content": base64.b64encode(body).decode(),
    })
    result = await client.get_file_contents("owner", "repo", "app/main.py", "feature/demo")
    assert result == "print('ok')\n"
    assert client.requests[0][1] == {"ref": "feature/demo"}


@pytest.mark.asyncio
async def test_get_file_contents_rejects_binary_oversized_and_traversal() -> None:
    binary = base64.b64encode(b"\x00binary").decode()
    client = FakeGitHubClient({
        "type": "file", "size": 7, "encoding": "base64", "content": binary,
    })
    with pytest.raises(RuntimeError, match="binary"):
        await client.get_file_contents("owner", "repo", "data.bin")
    with pytest.raises(ValueError, match="repository-relative"):
        await client.get_file_contents("owner", "repo", "../secret.txt")

    oversized = FakeGitHubClient({
        "type": "file", "size": GitHubClient.MAX_TEXT_FILE_SIZE + 1,
        "encoding": "base64", "content": "",
    })
    with pytest.raises(RuntimeError, match="exceeds"):
        await oversized.get_file_contents("owner", "repo", "large.txt")


@pytest.mark.asyncio
async def test_investigation_endpoints_return_read_only_evidence() -> None:
    issues = FakeGitHubClient({"items": [
        {"number": 1, "title": "Auth bug", "state": "open", "pull_request": {"url": "x"}},
        {"number": 2, "title": "Login issue", "state": "open", "body": "details"},
    ]})
    result = await issues.search_open_issues("org", "repo", "authentication")
    assert [item["number"] for item in result] == [2]
    assert "repo:org/repo is:issue is:open authentication" in issues.requests[0][1]["q"]

    runs = FakeGitHubClient({"workflow_runs": [
        {"id": 12, "status": "completed", "conclusion": "failure", "head_branch": "main"}
    ]})
    run_result = await runs.list_workflow_runs("org", "repo", "main")
    assert run_result == [{"id": 12, "status": "completed", "conclusion": "failure", "head_branch": "main"}]
    assert runs.requests[0][1]["branch"] == "main"


@pytest.mark.asyncio
async def test_http_errors_authentication_and_timeouts_are_application_errors(monkeypatch) -> None:
    def unauthorized(request):
        assert request.headers["Authorization"] == "Bearer test-token"
        return httpx.Response(401, json={"message": "bad credentials"})

    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    client = GitHubClient(
        base_url="https://example.invalid",
        transport=httpx.MockTransport(unauthorized),
    )
    with pytest.raises(RuntimeError, match="authentication failed"):
        await client.get_repository("owner", "repo")

    def timed_out(request):
        raise httpx.ConnectTimeout("timed out", request=request)

    timeout_client = GitHubClient(
        base_url="https://example.invalid",
        transport=httpx.MockTransport(timed_out),
    )
    with pytest.raises(RuntimeError, match="Could not reach GitHub API"):
        await timeout_client.get_repository("owner", "repo")


@pytest.mark.asyncio
async def test_public_api_call_does_not_require_authentication(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    def ok(request):
        assert "Authorization" not in request.headers
        return httpx.Response(200, json={"full_name": "owner/repo"})

    client = GitHubClient(
        base_url="https://example.invalid",
        transport=httpx.MockTransport(ok),
    )
    assert await client.get_repository("owner", "repo") == {"full_name": "owner/repo"}


@pytest.mark.asyncio
async def test_repository_metadata_and_tree_are_preserved() -> None:
    class Responses(GitHubClient):
        def __init__(self):
            super().__init__(base_url="https://example.invalid")
            self.payloads = iter([
                {"full_name": "owner/repo", "stargazers_count": 3},
                {"tree": [{"path": "app.py", "type": "blob"}, {"path": "src", "type": "tree"}],
                 "truncated": False},
            ])

        async def _get_json(self, url, resource_description, params=None):
            return next(self.payloads)

    client = Responses()
    metadata = await client.get_repository("owner", "repo")
    tree = await client.list_repository_files("owner", "repo", "feature/x")
    assert metadata["stargazers_count"] == 3
    assert [item["path"] for item in tree] == ["app.py", "src"]


@pytest.mark.asyncio
async def test_missing_repository_or_file_returns_clear_http_error() -> None:
    def missing(request):
        return httpx.Response(404, json={"message": "Not Found"})

    client = GitHubClient(
        base_url="https://example.invalid",
        transport=httpx.MockTransport(missing),
    )
    with pytest.raises(RuntimeError, match="was not found or is not accessible"):
        await client.get_file_contents("owner", "repo", "missing.py")
