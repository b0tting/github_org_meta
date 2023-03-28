from git import Repo


class GitCommitTime():
    def __init__(self, repo_dir):
        self.time_results = None
        self.repo_dir = repo_dir

    def get_commit_times(self):
        time_brackets = dict.fromkeys(range(0, 24), 0)
        repo = Repo(self.repo_dir)
        count = 0
        for commit in repo.iter_commits("HEAD^"):
            date = commit.authored_date
            # time_brackets[date.hour] += 1
            count += 1
        print(count)
        return time_brackets


gct = GitCommitTime("D:\\drive\\aws\\werkplaats-3-rest-byte-bandits")
print(gct.get_commit_times())
