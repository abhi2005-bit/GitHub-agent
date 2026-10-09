from app.models.project import Project
from app.repositories.project_repository import ProjectRepository


class ProjectContext:

    def __init__(self, project_repository: ProjectRepository):
        self.project_repository = project_repository

    def get_project(self, project_id: int) -> Project:
        project = self.project_repository.get(project_id)

        if project is None:
            raise ValueError(
                f"Project with id {project_id} does not exist."
            )

        return project