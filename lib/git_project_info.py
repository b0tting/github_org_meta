from lib.git_project import GitProject
from lib.github_handler import GitHubHandler


class GitProjectInfo:
    def __init__(self, project_settings, cache_dir, github_handler: GitHubHandler):
        self.project_settings = project_settings
        self.basedir = cache_dir
        self.github_handler = github_handler
        self.projects = self.init_projects()

    def init_projects(self):
        projects = []
        for project_setting in self.project_settings:
            projects.append(
                GitProject(
                    name=project_setting["name"],
                    label=project_setting["label"],
                    expression=project_setting["expression"],
                    required_files=project_setting["required_files"],
                    github_org=self.github_handler.github_org,
                    base_dir=self.basedir,
                )
            )
        return projects

    def get_project_info(self, project_name):
        for project in self.projects:
            if project.name == project_name:
                return project
        raise Exception(f"Project {project_name} not found")

    def get_all_projects(self):
        return self.projects

    def get_unmatched_repos(self, gcap):
        repo_expressions = [project.expression for project in self.projects]
        repo_list = self.github_handler.unmatched_repos(repo_expressions)
        return repo_list
