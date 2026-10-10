from __future__ import annotations

import base64
import binascii
from typing import Any
from urllib.parse import quote

import httpx


class GitHubClient:
    """
    Client for communicating with the GitHub REST API.
    """

    BASE_URL = "https://api.github.com"
    API_VERSION = "2026-03-10"
    TIMEOUT = 10.0
    MAX_TEXT_FILE_SIZE = 1_000_000

    def __init__(self, base_url: str = BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")

    @staticmethod
    def _validate_repository_details(
        owner: str,
        repository: str,
    ) -> tuple[str, str]:
        """Validate and normalize repository identifiers."""

        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("GitHub owner cannot be empty.")

        if not isinstance(repository, str) or not repository.strip():
            raise ValueError("Repository name cannot be empty.")

        return owner.strip(), repository.strip()

    async def _get_json(
        self,
        url: str,
        resource_description: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        """Send a GET request and handle HTTP and network errors."""

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.API_VERSION,
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.TIMEOUT,
                headers=headers,
            ) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code

            if status_code == 404:
                message = (
                    f"{resource_description} was not found "
                    "or is not accessible."
                )
            elif status_code == 403:
                remaining = exc.response.headers.get(
                    "X-RateLimit-Remaining"
                )

                if remaining == "0":
                    message = "GitHub API rate limit exceeded."
                else:
                    message = (
                        "GitHub denied access. Check permissions, "
                        "repository visibility, or API rate limits."
                    )
            elif status_code == 401:
                message = "GitHub authentication failed."
            else:
                message = (
                    f"GitHub API returned HTTP {status_code} "
                    f"while fetching {resource_description}."
                )

            raise RuntimeError(message) from exc

        except httpx.RequestError as exc:
            raise RuntimeError(
                f"Could not reach GitHub API: {exc}"
            ) from exc

        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError(
                "GitHub returned an invalid JSON response."
            ) from exc

    async def get_repository(
        self,
        owner: str,
        repository: str,
    ) -> dict[str, Any]:
        """Fetch repository metadata from GitHub."""

        owner, repository = self._validate_repository_details(
            owner,
            repository,
        )

        url = f"{self.base_url}/repos/{owner}/{repository}"

        data = await self._get_json(
            url=url,
            resource_description=f"Repository '{owner}/{repository}'",
        )

        if not isinstance(data, dict):
            raise RuntimeError(
                "GitHub returned an unexpected repository response."
            )

        return data

    async def list_repository_files(
        self,
        owner: str,
        repository: str,
        branch: str = "main",
    ) -> list[dict[str, Any]]:
        """Fetch the recursive file tree for a repository branch."""

        owner, repository = self._validate_repository_details(
            owner,
            repository,
        )

        if not isinstance(branch, str) or not branch.strip():
            raise ValueError("Branch cannot be empty.")

        branch = branch.strip()
        encoded_branch = quote(branch, safe="")

        url = (
            f"{self.base_url}/repos/{owner}/{repository}"
            f"/git/trees/{encoded_branch}"
        )

        data = await self._get_json(
            url=url,
            resource_description=(
                f"Repository tree for '{owner}/{repository}' "
                f"on branch '{branch}'"
            ),
            params={"recursive": "1"},
        )

        if not isinstance(data, dict):
            raise RuntimeError(
                "GitHub returned an unexpected repository tree response."
            )

        tree = data.get("tree")

        if not isinstance(tree, list):
            raise RuntimeError(
                "GitHub response does not contain a valid tree."
            )

        if data.get("truncated") is True:
            raise RuntimeError(
                "GitHub returned a truncated repository tree. "
                "Fetch subtrees separately to obtain a complete listing."
            )

        return [
            entry
            for entry in tree
            if (
                isinstance(entry, dict)
                and isinstance(entry.get("path"), str)
                and isinstance(entry.get("type"), str)
            )
        ]

    async def get_file_contents(
        self,
        owner: str,
        repository: str,
        path: str,
        branch: str = "main",
    ) -> str:
        """
        Fetch and decode a text file from a GitHub repository.

        Supports UTF-8 text files up to 1,000,000 bytes.
        """

        owner, repository = self._validate_repository_details(
            owner,
            repository,
        )

        if not isinstance(path, str) or not path.strip():
            raise ValueError("File path cannot be empty.")

        if not isinstance(branch, str) or not branch.strip():
            raise ValueError("Branch cannot be empty.")

        path = path.strip().strip("/")
        branch = branch.strip()

        if not path or any(part in {".", ".."} for part in path.split("/")):
            raise ValueError("File path is invalid.")

        encoded_path = quote(path, safe="/")

        url = (
            f"{self.base_url}/repos/{owner}/{repository}"
            f"/contents/{encoded_path}"
        )

        data = await self._get_json(
            url=url,
            resource_description=(
                f"File '{path}' in repository '{owner}/{repository}'"
            ),
            params={"ref": branch},
        )

        if not isinstance(data, dict):
            raise RuntimeError(
                f"'{path}' is not a readable file."
            )

        if data.get("type") != "file":
            raise RuntimeError(
                f"'{path}' is not a regular file."
            )

        size = data.get("size")

        if not isinstance(size, int) or isinstance(size, bool):
            raise RuntimeError(
                f"GitHub returned an invalid size for '{path}'."
            )

        if size > self.MAX_TEXT_FILE_SIZE:
            raise RuntimeError(
                f"'{path}' exceeds the supported file size of "
                f"{self.MAX_TEXT_FILE_SIZE} bytes."
            )

        if size < 0:
            raise RuntimeError(
                f"GitHub returned an invalid size for '{path}'."
            )

        if data.get("encoding") != "base64":
            raise RuntimeError(
                f"GitHub did not return Base64 content for '{path}'. "
                "The file may be too large or unsupported."
            )

        content = data.get("content")

        if not isinstance(content, str):
            raise RuntimeError(
                f"GitHub did not return file content for '{path}'."
            )

        try:
            # GitHub Base64 responses may contain newline characters.
            encoded_content = "".join(content.split())
            decoded_bytes = base64.b64decode(
                encoded_content,
                validate=True,
            )
            decoded_text = decoded_bytes.decode("utf-8")

        except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
            raise RuntimeError(
                f"'{path}' is not a supported UTF-8 text file."
            ) from exc

        if "\x00" in decoded_text:
            raise RuntimeError(
                f"'{path}' appears to be a binary file, not text."
            )

        return decoded_text