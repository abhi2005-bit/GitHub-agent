from __future__ import annotations

from app.models.project import Project, ProjectSource
from app.repositories.project_repository import ProjectRepository


class ProjectService:
    """
    Handles project registration and validation for DevPilot.
    """

    def __init__(self, project_repository: ProjectRepository) -> None:
        self.project_repository = project_repository

    def register_github_project(
        self,
        name: str,
        owner: str,
        repository: str,
        branch: str = "main",
    ) -> Project:
        """
        Register a GitHub project using its repository metadata.
        """

        # Validate the required fields.
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Project name cannot be empty.")

        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("GitHub owner cannot be empty.")

        if not isinstance(repository, str) or not repository.strip():
            raise ValueError("Repository name cannot be empty.")

        if not isinstance(branch, str) or not branch.strip():
            raise ValueError("Branch cannot be empty.")

        # Normalize whitespace.
        name = name.strip()
        owner = owner.strip()
        repository = repository.strip()
        branch = branch.strip()

        # Prevent registering the same GitHub repository twice.
        for existing_project in self.project_repository.get_all():
            if (
                existing_project.source == ProjectSource.GITHUB
                and existing_project.owner is not None
                and existing_project.repository is not None
                and existing_project.owner.casefold() == owner.casefold()
                and existing_project.repository.casefold()
                == repository.casefold()
            ):
                raise ValueError(
                    f"GitHub repository '{owner}/{repository}' "
                    "is already registered."
                )

        # Generate the next project ID.
        existing_projects = self.project_repository.get_all()

        project_id = max(
            (project.id for project in existing_projects),
            default=0,
        ) + 1

        # Create the project model.
        project = Project(
            id=project_id,
            name=name,
            source=ProjectSource.GITHUB,
            owner=owner,
            repository=repository,
            branch=branch,
        )

        # Store and return the registered project.
        return self.project_repository.add(project)