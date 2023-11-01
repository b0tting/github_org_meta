import re
from pathlib import Path
from github import Github, Auth

import yaml


class TeamZipper:
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

    def get_all_teams_for_project(self, project_name):
        project = self.get_project_info(project_name)
        relevant_teams = []
        regex = re.compile(project["expression"])
        org = self.github.get_organization(self.git_config["github_organization"])
        for team in org.get_teams():
            if team.get_repos().totalCount == 0:
                continue

            print(f"Team {team.name} has {team.get_repos().totalCount} repos")
            repos = team.get_repos()
            for repo in repos:
                if regex.match(repo.name):
                    print(f"Team has a relevant project repo: {repo.name}")
                    relevant_teams.append(team)
                    break
        return relevant_teams

    def join_all_members_from_teams_in_team(self, teams_list, team_target_name):
        target_team = self.github.get_organization(
            self.git_config["github_organization"]
        ).get_team_by_slug(team_target_name)
        for team in teams_list:
            print(f"Team {team.name}")
            for member in team.get_members():
                print(f"Member {member.name}")
                target_team.add_membership(member)


teamzip = TeamZipper()
relevant_teams = teamzip.get_all_teams_for_project("wp1-2023-pygame")
teamzip.join_all_members_from_teams_in_team(relevant_teams, "wp1-2023")
