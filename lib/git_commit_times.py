import glob
import os
import re
import time

from git import GitCommandError, InvalidGitRepositoryError, Repo
from pydriller import Repository

from lib import GitCacheHandler


class GitCommitTimes:
    CONFIG_LOCK_BACKUP_TIME = 5

    def __init__(self, repos_dir, git_project_info):
        self.repo_dir = repos_dir
        self.repo_name_expression = re.compile(r"[\\/]")
        self.repo_map = self.get_repo_dirs(repos_dir)
        self.cache_handler = GitCacheHandler(repos_dir)
        self.time_results = None
        self.git_project_info = git_project_info

    def traverse_with_backoff_time(self, repo_url):
        repo = Repository(repo_url, include_refs=True)
        commit_list = []
        for n in range(3):
            try:
                for commit in repo.traverse_commits():
                    commit_list.append(commit)
                break
            except GitCommandError as e:
                if "bad revision 'HEAD'" in str(e):
                    break
                else:
                    raise e
            except IOError as e:
                time.sleep(self.CONFIG_LOCK_BACKUP_TIME)
        return commit_list

    def get_repo_dirs(self, glob_dir) -> dict:
        repo_list = glob.glob(glob_dir + "/*/*")
        for repo_dir in repo_list:
            try:
                Repo(repo_dir).git_dir
            except InvalidGitRepositoryError:
                print(f"Invalid git repository: {repo_dir}")
                repo_list.remove(repo_dir)
        repo_map = {}
        for repo in repo_list:
            name = self.get_repo_name(repo)
            repo_map[name] = repo
        return repo_map

    def get_repo_name(self, repo_url):
        return self.repo_name_expression.split(repo_url)[-1]

    def get_filtered_repos(self, project):
        project_info = self.git_project_info.get_project_info(project)
        expression = re.compile(project_info["expression"])
        return [repo for repo in self.repo_map.items() if expression.match(repo[0])]

    def get_commits_over_weeks(self, project, ignore_cache=False) -> list:
        cache = self.cache_handler.get_cache("get_commits_over_weeks", project)
        if cache and not ignore_cache:
            return cache
        else:
            week_results = []
            for name, repo_url in self.get_filtered_repos(project):
                week_results.append(
                    {
                        "name": name,
                        "week_brackets": self.get_week_number_commits(repo_url),
                    }
                )
            if week_results:
                self.cache_handler.save_cache(
                    "get_commits_over_weeks", project, week_results
                )
            return week_results

    def get_week_number_commits(self, repo_url):
        week_brackets = {}
        commits = self.traverse_with_backoff_time(repo_url)
        for commit in commits:
            commit_date = commit.author_date
            week_number = str(commit_date.isocalendar()[1])
            if week_number not in week_brackets:
                week_brackets[week_number] = 0
            week_brackets[week_number] += 1
        return week_brackets

    def get_all_commit_times(self, project) -> list:
        cache = self.cache_handler.get_cache("get_all_commit_times", project)
        time_labels = [f"{hour:02d}:00" for hour in range(0, 24)]
        if cache:
            return time_labels, cache
        else:
            time_results = []
            for name, repo_url in self.get_filtered_repos(project):
                time_results.append(
                    {
                        "name": name,
                        "time_brackets": self.get_repo_commit_times(
                            repo_url, time_labels
                        ),
                    }
                )
            if time_results:
                self.cache_handler.save_cache(
                    "get_all_commit_times", project, time_results
                )
            return time_labels, time_results

    def get_repo_commit_times(self, repo_url, time_labels):
        time_brackets = {label: 0 for label in time_labels}
        commits = self.traverse_with_backoff_time(repo_url)
        for commit in commits:
            date = commit.author_date
            clean_hour = f"{date.hour:02d}:00"
            time_brackets[clean_hour] += 1
        return time_brackets

    def get_number_commits(self, project) -> list:
        cache = self.cache_handler.get_cache("get_number_commits", project)
        if cache:
            return cache
        else:
            number_results = []
            for name, repo_url in self.get_filtered_repos(project):
                commits = self.traverse_with_backoff_time(repo_url)
                number_results.append(
                    {
                        "name": name,
                        "number_commits": len(list(commits)),
                    }
                )
            self.cache_handler.save_cache("get_number_commits", project, number_results)
            return number_results

    def get_tagged_state(self, project) -> list:
        cache = self.cache_handler.get_cache("get_tagged_state", project)
        if cache:
            return cache
        else:
            tag_results = []
            for name, repo_url in self.get_filtered_repos(project):
                repo = Repo(repo_url)
                tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
                if tags:
                    tag_results.append(
                        {
                            "name": name,
                            "tag": tags[-1].name,
                            "date": tags[-1].commit.committed_datetime,
                        }
                    )
                else:
                    tag_results.append(
                        {"name": name, "tag": "No tags", "date": "No tags"}
                    )
            self.cache_handler.save_cache("get_tagged_state", project, tag_results)
            return tag_results

    def get_got_required_files(self, project_name) -> list:
        cache = self.cache_handler.get_cache("get_got_required_files", project_name)
        if cache:
            return cache
        else:
            project = self.git_project_info.get_project_info(project_name)
            project_dir = os.path.join(self.repo_dir, project["name"])
            required_files_results = []

            regexes = {regex[0]: re.compile(regex[1]) for regex in project["required_files"].items()}
            for name, repourl in self.get_filtered_repos(project_name):
                project_repo_dir = os.path.join(project_dir, name)
                current = {"name": name}
                project_files = os.listdir(project_repo_dir)
                for regex in regexes:
                    current[regex] = False
                    for project_file in project_files:
                        if regexes[regex].match(project_file):
                            current[regex] = True
                            break

                # Add completed results
                required_count = 0
                for regex in regexes:
                    if current[regex]:
                        required_count += 1
                current["required_files"] = required_count

                required_files_results.append(current)
            self.cache_handler.save_cache(
                "get_tagged_state", project_name, required_files_results
            )
            return required_files_results
