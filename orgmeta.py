import tkinter as tk

import yaml

from lib import GitProjectInfo

settings = yaml.load(open("gitmeta.yml"), Loader=yaml.FullLoader)
gpi = GitProjectInfo(
    settings["projects"], settings["git_repo_dir"], settings["github_organization"]
)

def list_repos_button():
    all_projects = []
    for project in gpi.get_all_project_info():


window = tk.Tk()
window.title("OrgMeta")
window.geometry("500x500")




window.mainloop()
