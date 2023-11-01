import os
import pickle

from lib import GitProject


class GitCacheHandler:
    def __init__(self, repo_dir):
        self.repo_dir = repo_dir

    def cache_refresh_required(self, cache_file, project: GitProject):
        repo_sync = project.repo_sync_time
        last_update_mtime = repo_sync.get_last_updated_time()
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
