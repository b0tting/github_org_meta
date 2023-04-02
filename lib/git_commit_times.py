import glob
import re
import time

from git import GitCommandError, InvalidGitRepositoryError, Repo
from pydriller import Repository

from lib import GitCacheHandler


class GitCommitTimes:
    CONFIG_LOCK_BACKUP_TIME = 5

    def __init__(self, repos_dir):
        self.repo_dir = repos_dir
        self.repo_list = self.get_repo_dirs(repos_dir)
        self.cache_handler = GitCacheHandler(repos_dir)
        self.time_results = None

    def traverse_with_backoff_time(self, repo_url):
        repo = Repository(repo_url, include_refs=True)
        commit_list = []
        name = None
        for n in range(3):
            try:
                for commit in repo.traverse_commits():
                    commit_list.append(commit)
                    if not name:
                        name = commit.project_name
                break
            except GitCommandError as e:
                if "bad revision 'HEAD'" in str(e):
                    break
                else:
                    raise e
            except IOError as e:
                time.sleep(self.CONFIG_LOCK_BACKUP_TIME)
        if not name:
            name = re.split(r'[\\/]', repo_url)[-1]
        return name, commit_list

    def get_repo_dirs(self, glob_dir) -> list:
        repo_list = glob.glob(glob_dir + "/*/*")
        for repo_dir in repo_list:
            try:
                Repo(repo_dir).git_dir
            except InvalidGitRepositoryError:
                print(f"Invalid git repository: {repo_dir}")
                repo_list.remove(repo_dir)
        return repo_list

    def get_commits_over_weeks(self, project, ignore_cache=False) -> list:
        cache = self.cache_handler.get_cache("get_commits_over_weeks", project)
        if cache and not ignore_cache:
            return cache
        else:
            week_results = []
            for repo_url in self.repo_list:
                if project in repo_url:
                    week_results.append(self.get_week_number_commits(repo_url))
            print(week_results)
            if week_results:
                self.cache_handler.save_cache(
                    "get_commits_over_weeks", project, week_results
                )
            return week_results

    def get_week_number_commits(self, repo_url):
        week_brackets = {}
        name, commits = self.traverse_with_backoff_time(repo_url)
        for commit in commits:
            commit_date = commit.author_date
            week_number = str(commit_date.isocalendar()[1])
            if week_number not in week_brackets:
                week_brackets[week_number] = 0
            week_brackets[week_number] += 1
        return {"name": name, "week_brackets": week_brackets}

    def get_all_commit_times(self, project) -> list:
        cache = self.cache_handler.get_cache("get_all_commit_times", project)
        time_labels = [f"{hour:02d}:00" for hour in range(0, 24)]
        if cache:
            return time_labels, cache
        else:
            time_results = []
            for repo_url in self.repo_list:
                if project in repo_url:
                    time_results.append(
                        self.get_repo_commit_times(repo_url, time_labels)
                    )
            if time_results:
                self.cache_handler.save_cache(
                    "get_all_commit_times", project, time_results
                )
            return time_labels, time_results

    def get_repo_commit_times(self, repo_url, time_labels):
        time_brackets = {label: 0 for label in time_labels}
        name, commits = self.traverse_with_backoff_time(repo_url)
        for commit in commits:
            date = commit.author_date
            clean_hour = f"{date.hour:02d}:00"
            time_brackets[clean_hour] += 1

        return {"name": name, "time_brackets": time_brackets}

    def get_number_commits(self, project) -> list:
        cache = self.cache_handler.get_cache("get_number_commits", project)
        if cache:
            return cache
        else:
            number_results = []
            for repo_url in self.repo_list:
                if project in repo_url:
                    name, commits = self.traverse_with_backoff_time(repo_url)
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
            for repo_url in self.repo_list:
                if project in repo_url:
                    repo = Repo(repo_url)
                    tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
                    name = repo_url.split("\\")[-1]
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
