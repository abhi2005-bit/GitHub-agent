from __future__ import annotations

import asyncio

from app.bootstrap import create_agent_runner
from app.repositories.project_repository import ProjectRepository
from app.services.project_service import ProjectService


async def main() -> None:
    print("=" * 40)
    print("        DEVPILOT AGENT")
    print("=" * 40)

    # 1. Initialize shared project storage and registration service.
    repository = ProjectRepository()
    project_service = ProjectService(repository)

    # 2. Register a project using its metadata.
    print("\nRegister a GitHub repository.")
    print("This step stores metadata locally; it does not connect to GitHub.")

    name = input("Project name: ").strip()
    owner = input("GitHub owner: ").strip()
    repository_name = input("Repository name: ").strip()
    branch = input("Branch [main]: ").strip() or "main"

    try:
        project = project_service.register_github_project(
            name=name,
            owner=owner,
            repository=repository_name,
            branch=branch,
        )
    except (ValueError, TypeError) as exc:
        print(f"\nProject registration failed: {exc}")
        return

    print(
        f"\nProject registered successfully."
        f"\nProject ID: {project.id}"
        f"\nProject: {project.owner}/{project.repository}"
        f"\nBranch: {project.branch}"
    )

    # 3. Assemble the agent using the same repository.
    try:
        runner = create_agent_runner(repository)
    except Exception as exc:
        print(f"\nAgent initialization failed: {exc}")
        return

    # 4. Receive the user's engineering goal.
    goal = input(
        "\nWhat should DevPilot investigate? "
    ).strip()

    if not goal:
        print("Goal cannot be empty.")
        return

    # 5. Execute the agent run.
    print("\nDevPilot is processing your request...")

    result = await runner.run(
        goal=goal,
        project_id=project.id,
    )

    # 6. Display the agent's response.
    print("\n" + "=" * 40)
    print("           AGENT RESULT")
    print("=" * 40)

    print(f"\nState: {result.state.value}")
    print(f"Iterations: {result.iterations}")

    for message in result.messages:
        print(f"\n[{message.role}] {message.content}")

    if result.error:
        print(f"\nError: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())