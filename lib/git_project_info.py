import datetime
import os

from lib import GitRepoCloneAndPull


class GitProjectInfo:
    def __init__(self, projects, basedir, github_org):
        self.projects = projects
        self.basedir = basedir
        self.github_org = github_org

    @staticmethod
    def convert_timestamp(timestamp):
        if timestamp:
            return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
        else:
            return "Never"

    def get_project_info(self, project):
        for project_info in self.projects:
            if project_info["name"] == project:
                return project_info
        return None

    def get_all_project_info(self):
        result = {"github_org": self.github_org, "projects": ""}
        project_list = []
        for project in self.projects:
            update_timestamp = self.get_updated_time(project["name"])
            project_list.append(
                {
                    "name": project["name"],
                    "label": project["label"],
                    "last_updated": self.convert_timestamp(update_timestamp),
                    "has_required_files": "required_files" in project and project["required_files"] is not None,
                    "base_repo_url": "https://github.com/" + self.github_org
                }
            )
        result["projects"] = project_list
        return result

    def get_updated_time(self, project):
        return GitRepoCloneAndPull.get_last_updated_time(
            os.path.join(self.basedir, project)
        )

    def get_unmatched_repos(self, gcap):
        repo_expressions = [project["expression"] for project in self.projects]
        repo_list = gcap.unmatched_repos(repo_expressions)
        return repo_list

    @staticmethod
    def get_clone_url(project, github_org):
        if project == None:
            return f"https://github.com/{github_org}"
        else:
            return f"https://github.com/{github_org}/{project}.git"
