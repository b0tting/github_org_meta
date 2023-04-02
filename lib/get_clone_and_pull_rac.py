import os.path
import re

import git
from github import Github
from git.repo.base import Repo


class GitRepoCloneAndPull:
    LAST_UPDATE_FILE = ".last_update"

    def __init__(self, github_access_token, github_org):
        self.github_access_token = github_access_token
        self.github_org = github_org
        self.repo_list = self.list_all_repos()

    @staticmethod
    def get_last_updated_time(repos_dir):
        update_file = os.path.join(repos_dir, GitRepoCloneAndPull.LAST_UPDATE_FILE)
        if os.path.exists(update_file):
            return os.stat(update_file).st_mtime
        else:
            return None

    @staticmethod
    def set_last_updated_time(repos_dir):
        update_file = os.path.join(repos_dir, GitRepoCloneAndPull.LAST_UPDATE_FILE)
        if os.path.exists(update_file):
            os.utime(update_file, None)
        else:
            with open(update_file, "a"):
                os.utime(update_file, None)
        return os.stat(update_file).st_mtime

    def clone_repo(self, repo, repo_dir):
        print(f"Cloning {repo.name}")
        clone_url = repo.clone_url.replace(
            "https://", f"https://{self.github_org}:{self.github_access_token}@"
        )
        Repo.clone_from(clone_url, repo_dir)

    def unmatched_repos(self, repo_name_expression_list):
        result = []
        compiled_expressions = [re.compile(repo_name_expression) for repo_name_expression in repo_name_expression_list]
        for repo in self.repo_list:
            matched = False
            for repo_name_expression in compiled_expressions:
                if repo_name_expression.match(repo.name):
                    matched = True
                    break
            if not matched:
                result.append({"name": repo.name, "clone_url": repo.clone_url})
        return result

    def pull_to_dir(self, repo_basedir, project, repo_name_expression):
        print(f"Now pulling and cloning {project}")
        repos_dir = os.path.join(repo_basedir, project)
        if not repo_name_expression or len(repo_name_expression) < 3:
            raise ValueError(
                "A filter expression is required before pulling the repos. The filter should be at least 3 characters long."
            )
        if os.path.exists(repos_dir):
            print(f"Pulling repositories into {repos_dir}")
        repo_regex = re.compile(repo_name_expression)
        filtered_repo_list = [
            repo for repo in self.repo_list if repo_regex.match(repo.name)
        ]
        print(f"Found {len(filtered_repo_list)} repos to pull or clone")
        for repo_meta in filtered_repo_list:
            repo_dir = os.path.join(repos_dir, repo_meta.name)
            if os.path.exists(repo_dir):
                try:
                    repo = Repo(repo_dir)
                    self.pull_repo(repo, repo_meta, repo_dir)
                except git.exc.InvalidGitRepositoryError as e:
                    print(f"Invalid repository: {e}")
            else:
                self.clone_repo(repo_meta, repo_dir)
        update_date = GitRepoCloneAndPull.set_last_updated_time(repos_dir)
        return update_date

    def pull_repo(self, repo, repo_meta, repo_dir, with_reset=False):
        if with_reset:
            print(f"Forcing repo reset on {repo_meta.name}")
            try:
                repo.git.reset("--hard", "origin/main")
            except git.exc.GitCommandError as e:
                print(f"Error resetting {repo_meta.name}: {e}")
        print(f"Pulling {repo_meta.name}")
        try:
            repo.git.checkout("main")
            repo.remotes.origin.pull()
        except git.exc.GitCommandError as e:
            if not with_reset:
                print(f"Error pulling {repo_meta.name}: {e} - trying reset")
                self.pull_repo(repo, repo_meta, repo_dir, with_reset=True)
            else:
                print(f"Error pulling {repo_meta.name}: {e} - skipping")

    def list_all_repos(self):
        g = Github(self.github_access_token)
        org = g.get_organization(self.github_org)
        return org.get_repos()
