import traceback

import yaml
from flask import Flask, jsonify, render_template, request

from get_clone_and_pull_rac import GitProjectInfo, GitRepoCloneAndPull
from git_commit_times import GitCommitTimes

app = Flask(__name__, static_url_path="/assets", static_folder="assets")
settings = yaml.load(open("gitmeta.yml"), Loader=yaml.FullLoader)
for key, value in settings.items():
    app.config[key] = value
gct = GitCommitTimes(app.config["git_repo_dir"])
gpi = GitProjectInfo(
    settings["projects"], app.config["git_repo_dir"], app.config["github_organization"]
)
grcap = GitRepoCloneAndPull(
    settings["github_access_token"],
    settings["github_organization"],
)


@app.route("/project/<string:project>")
def get_project_page(project):
    tags = gct.get_tagged_state(project)
    return render_template(
        "charts.html", project=project, projects=settings["projects"], tags=tags
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
    labels = set([label for repo in result for label in repo["week_brackets"].keys()])
    labels = list(labels)
    labels.sort(key=lambda x: int(x))
    result = {"data": chartjs_datasets, "labels": labels}
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
        unmatched=grcap.unmatched_repos(project_expressions)
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


@app.route("/get_commit_weeks/<string:project>/<string:repo>")
def list_repo_commits(project):
    raise NotImplementedError


@app.route("/refresh_project/<string:project>")
def refresh_project(project):
    try:
        project_info = gpi.get_project_info(project)
        if not project_info:
            raise Exception(f"Error: project {project} not in project list")
        update_timestamp = grcap.pull_to_dir(settings["git_repo_dir"], project_info["name"], project_info["expression"])
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
