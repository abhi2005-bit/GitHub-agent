from app.models.project import Project

class ProjectRepository:

    def __init__(self):
        self.projects: dict[int, Project] = {}

    def add(self,project:Project):
        self.projects[project.id] = project
        return project

    def get(self,project_id:int)->Project | None:
        return self.projects.get(project_id)

    def get_all(self)->list[Project]:
        return list(self.projects.values())

    def remove(self,project_id:int):
        if project_id in self.projects:
            del self.projects[project_id]
            return True
        else:
            return False
