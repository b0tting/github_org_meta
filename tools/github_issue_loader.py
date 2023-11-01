# This tool is used to load issues from a CSV file into the Github repositories
import re
from pathlib import Path

import yaml
from github import Github, Auth


class RepoRetriever:
    def __init__(self):
        path = Path(__file__).parent.parent
        yaml_file = path / "gitmeta.yml"
        self.git_config = yaml.load(open(yaml_file), Loader=yaml.FullLoader)
        self.auth = Auth.Token(self.git_config["github_access_token"])
        self.github = Github(auth=self.auth)

    def get_project_info(self, project_name):
        for project in self.git_config["projects"]:
            if project["name"] == project_name:
                return project
        raise Exception(f"Project {project_name} not found")

    def get_matching_repos(self, project_name):
        project = self.get_project_info(project_name)
        regex = re.compile(project["expression"])
        org = self.github.get_organization(self.git_config["github_organization"])
        repos = []
        for repo in org.get_repos():
            if regex.match(repo.name):
                repos.append(repo)
        return repos

    def get_single_repo(self, repo_name):
        org = self.github.get_organization(self.git_config["github_organization"])
        return org.get_repo(repo_name)


class IssueLoader:
    def __init__(self, issue_file):
        self.issue_file = issue_file
        self.issues = self.load_issues()

    def load_issues(self):
        with open(self.issue_file) as file:
            raw_issues = yaml.load(file, Loader=yaml.FullLoader)
            issues = raw_issues.get("github_issues")
            if not issues:
                raise Exception("No issues found in issue file or incorrect format")
        return issues

    def has_no_issues(self, repo):
        return repo.get_issues().totalCount == 0

    def create_issues_on_repos(self, repos, force_delete=False):
        for repo in repos:
            if self.has_no_issues(repo):
                self.create_issues_on_repo(repo)
            else:
                if force_delete:
                    raise NotImplementedError(
                        "Force delete not implemented in Github API"
                    )
                else:
                    print(f"Repo {repo.name} already has issues, skipping")

    def create_issue_on_repo(self, issue_name, repo):
        for issue in self.issues:
            if issue["name"] == issue_name:
                self.__create_issue_on_repo(issue, repo)
                break

    def __create_issue_on_repo(self, issue, repo):
        print(f"Creating issue {issue['name']} on repo {repo.name}")
        repo.create_issue(
            title=issue["title"],
            body=issue["body"],
        )

    def create_issues_on_repo(self, repo):
        for issue in self.issues:
            self.__create_issue_on_repo(issue, repo)


repore = RepoRetriever()
# repos = repro.get_matching_repos("wp2-2023-pygame")
myrepo = repore.get_single_repo("passworder_github_test")
issue_loader = IssueLoader("wp2-issues.yaml")
issue_loader.create_issue_on_repo(repo=myrepo, issue_name="notities")
