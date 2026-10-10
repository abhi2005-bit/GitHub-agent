import asyncio

from app.integrations.github_client import GitHubClient


async def main() -> None:
    client = GitHubClient()

    files = await client.list_repository_files(
        owner="abhi2005-bit",
        repository="policy-agent",
        branch="main",
    )

    print(f"Found {len(files)} tree entries:\n")

    for item in files[:20]:
        print(item["type"], item["path"])


if __name__ == "__main__":
    asyncio.run(main())