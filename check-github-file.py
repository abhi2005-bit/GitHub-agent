import asyncio

from app.integrations.github_client import GitHubClient


async def main() -> None:
    client = GitHubClient()

    content = await client.get_file_contents(
        owner="abhi2005-bit",
        repository="policy-agent",
        path="README.md",
        branch="main",
    )

    print("===== README.md =====")
    print(content)


if __name__ == "__main__":
    asyncio.run(main())