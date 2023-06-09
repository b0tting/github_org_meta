import yaml
from flask import Flask, jsonify, render_template, request

from lib import GitCommitTimes, GitProjectInfo, GitRepoCloneAndPull

app = Flask(__name__, static_url_path="/assets", static_folder="assets")
settings = yaml.load(open("gitmeta.yml"), Loader=yaml.FullLoader)
for key, value in settings.items():
    app.config[key] = value

gpi = GitProjectInfo(
    settings["projects"], app.config["git_repo_dir"], app.config["github_organization"]
)
gct = GitCommitTimes(app.config["git_repo_dir"], gpi)
grcap = GitRepoCloneAndPull(
    settings["github_access_token"],
    settings["github_organization"],
)


@app.route("/project/<string:project>")
def get_project_page(project):
    try:
        tags = gct.get_tagged_state(project)
        # ...this is not the way
        for repo in tags:
            repo["clone_url"] = gpi.get_clone_url(
                repo["name"], app.config["github_organization"]
            )
    except FileNotFoundError:
        tags = []

    project_info = gpi.get_project_info(project)
    project_info["base_repo_url"] = gpi.get_clone_url(None, gpi.github_org)
    return render_template(
        "charts.html", project=project, projects=settings["projects"], tags=tags, project_info=project_info
    )


@app.route("/get_commit_times/<string:project>")
def get_commit_times(project):
    labels, result = gct.get_all_commit_times(project)
    chartjs_datasets = [
        {"label": repo["name"], "data": repo["time_brackets"]} for repo in result
    ]
    return jsonify({"dataset": chartjs_datasets, "labels": list(labels)})


@app.route("/get_commit_weeks/<string:project>")
def get_commit_weeks(project):
    ignore_cache = request.args.get("ignore_cache", False)
    result = gct.get_commits_over_weeks(project, ignore_cache)
    chartjs_datasets = [
        {"label": repo["name"], "data": repo["week_brackets"]} for repo in result
    ]
    week_numbers = set(
        [label for repo in result for label in repo["week_brackets"].keys()]
    )
    week_numbers = list(week_numbers)
    week_numbers.sort(key=lambda x: int(x))
    result = {"data": chartjs_datasets, "labels": week_numbers}
    return jsonify(result)


@app.route("/get_commit_number/<string:project>")
def get_commit_number(project):
    result = gct.get_number_commits(project)
    chartjs_datasets = result
    chartjs_datasets.sort(key=lambda x: x["number_commits"], reverse=True)
    return jsonify(chartjs_datasets)


@app.route("/get_project_info")
def get_project_info():
    project_infos = gpi.projects
    project_expressions = [project["expression"] for project in project_infos]
    return render_template(
        "project_info.html",
        projects=settings["projects"],
        project_info=gpi.get_all_project_info(),
        unmatched=grcap.unmatched_repos(project_expressions),
    )


@app.route("/repo_details")
def get_repo_details():
    return render_template(
        "repo_details.html",
        repos=settings["projects"],
        project_info=gpi.get_all_project_info(),
    )


@app.route("/get_unmatched_repos")
def get_unmatched_repos():
    projects = gpi.projects
    project_expressions = [project["expression"] for project in projects]
    return grcap.unmatched_repos(project_expressions)


@app.route("/get_repos/<string:project>")
def list_repos(project):
    return jsonify(gpi.get_repos_for_project(project))


@app.route("/get_required_files/<string:project>")
def get_required_files(project):
    result = gct.get_got_required_files(project)
    return jsonify(result)


@app.route("/refresh_project/<string:project>")
def refresh_project(project):
    try:
        project_info = gpi.get_project_info(project)
        if not project_info:
            raise Exception(f"Error: project {project} not in project list")
        update_timestamp = grcap.pull_to_dir(
            settings["git_repo_dir"], project_info["name"], project_info["expression"]
        )
        update_date = gpi.convert_timestamp(update_timestamp)
        return {"result": "success", "update_date": update_date}
    except Exception as e:
        return {"result": "failed", "error": str(e)}, 500


# @app.route("/get_commit_number")
# def get_commit_number():
#     result = gct.get_number_commits()
#     chartjs_datasets = result
#     chartjs_datasets.sort(key=lambda x: x["number_commits"], reverse=True)
#     return jsonify(chartjs_datasets)


@app.route("/")
def hello_world():
    return render_template("index.html", projects=settings["projects"])


app.run(debug=True)
