import glob
import os
import pickle
import time

import git
from git import Repo, InvalidGitRepositoryError
from git.exc import GitCommandError
from pydriller import Repository

from get_clone_and_pull_rac import GitRepoCloneAndPull


class CacheHandler:
    def __init__(self, repo_dir):
        self.repo_dir = repo_dir

    def cache_refresh_required(self, cache_file, project):
        project_dir = os.path.join(self.repo_dir, project)
        last_update_mtime = GitRepoCloneAndPull.get_last_updated_time(project_dir)
        cache_file_mtime = (
            os.stat(cache_file).st_mtime if os.path.exists(cache_file) else None
        )
        # IF the cache file does not exist or the last update time is newer than the cache file?
        if not cache_file_mtime:
            return True
        if last_update_mtime and last_update_mtime > cache_file_mtime:
            return True
        return False

    def get_cache_file_name(self, cache_name, project):
        return os.path.join(self.repo_dir, project, "." + cache_name + ".cache")

    def _load_cache(self, cache_file):
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        else:
            return None

    def save_cache(self, cache_entry, project, data):
        cache_file = self.get_cache_file_name(cache_entry, project)
        with open(cache_file, "wb") as f:
            pickle.dump(data, f)

    def get_cache(self, cache_entry, project):
        cache_file = self.get_cache_file_name(cache_entry, project)
        if not self.cache_refresh_required(cache_file, project):
            print(f"Loading cached commit times from {cache_file}")
            return self._load_cache(cache_file)
        else:
            return None


class GitCommitTimes:
    CONFIG_LOCK_BACKUP_TIME = 5

    def __init__(self, repos_dir, fetch=False):
        self.repo_dir = repos_dir
        self.repo_list = self.get_repo_dirs(repos_dir)
        self.cache_handler = CacheHandler(repos_dir)
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


if __name__ == "__main__":
    repo_dir = "D:\\drive\\aws\\werkplaats-3-rest-*"
    gct = GitCommitTimes(repo_dir, fetch=True)
    result = gct.get_all_commit_times()
    print(result)
