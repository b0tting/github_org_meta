
import re

import git

from git.repo.base import Repo

from lib import GitProject
from lib.git_project_repo import GitProjectRepo
from lib.github_handler import GitHubHandler


class GitRepoCloneAndPull:

    def __init__(self, github_handler: GitHubHandler):
        self.github_handler = github_handler

    def clone_repo(self, remote_repo, local_repo):
        print(f"Cloning {remote_repo.name}")
        Repo.clone_from(local_repo.get_clone_url(self.github_handler.access_token), local_repo.get_local_repo_dir())

    def pull_project_to_dir(self, project: GitProject):
        print(f"Now pulling and cloning {project.name}")
        print(f"Pulling repositories into {project.repos_dir}")
        repo_regex = re.compile(project.expression)
        filtered_repo_list = [
            remote_repo for remote_repo in self.github_handler.all_repos if repo_regex.match(remote_repo.name)
        ]

        print(f"Found {len(filtered_repo_list)} repos to pull or clone")
        for remote_repo in filtered_repo_list:
            local_repo = GitProjectRepo(project, remote_repo.name)
            if local_repo.has_local_repo():
                try:
                    repo = Repo(local_repo.get_local_repo_dir())
                    self.fetch_repo(repo)
                except git.exc.InvalidGitRepositoryError as e:
                    print(f"Invalid repository: {e}")
            else:
                self.clone_repo(remote_repo, local_repo)
        project.update_repo_sync_time()

    def fetch_repo(self, repo):
        try:
            repo.remotes.origin.fetch()
        except git.exc.GitCommandError as e:
            print(f"Error pulling {repo}: {e} - skipping")
