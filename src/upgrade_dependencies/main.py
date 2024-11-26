"""CLI package."""

import asyncio
import os
from typing import TYPE_CHECKING

import typer
from packaging.version import Version
from rich import print as rprint
from rich.console import Group
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from upgrade_dependencies.dependency import GitHubDependency, PyPIDependency
from upgrade_dependencies.project import Project
from upgrade_dependencies.utils import get_git_status, run_shell_command

if TYPE_CHECKING:
    from upgrade_dependencies.dependency import Dependency

app = typer.Typer()
GH_PAT = os.getenv("GH_PAT")


@app.command()
def list_dependencies(project_path: str = ""):
    """Checks whether a dependency needs updating.

    Args:
        project_path: Path to the project. Defaults to the current working directory.
    """
    project = Project(
        project_path=project_path,
        gh_pat=GH_PAT,
    )

    # base dependencies
    title = Text("Base Dependencies", style="bold")
    text = Text()

    for idx, base_dep in enumerate(project.base_dependencies):
        text.append(base_dep.package_name)
        text.append(str(base_dep.specifier), style="green")

        if idx < len(project.base_dependencies) - 1:
            text.append("\n")

    rprint(Panel(text, title=title, title_align="left"))

    # optional dependencies
    title = Text("Optional Dependencies", style="bold")
    panels: list[Panel] = []

    for extra, opt_deps in project.optional_dependencies_grouped.items():
        extra_title = Text(extra)
        text = Text()

        for idx, opt_dep in enumerate(opt_deps):
            text.append(opt_dep.package_name)
            text.append(str(opt_dep.specifier), style="green")

            if idx < len(opt_deps) - 1:
                text.append("\n")

        panels.append(Panel(text, title=extra_title, title_align="left"))

    panel_group = Group(*panels)

    if len(panels) > 0:
        rprint()
        rprint(Panel(panel_group, title=title, title_align="left"))

    # group dependencies
    title = Text("Dependency Groups", style="bold")
    panels: list[Panel] = []

    for group, group_deps in project.group_dependencies_grouped.items():
        extra_title = Text(group)
        text = Text()

        for idx, group_dep in enumerate(group_deps):
            text.append(group_dep.package_name)
            text.append(str(group_dep.specifier), style="green")

            if idx < len(group_deps) - 1:
                text.append("\n")

        panels.append(Panel(text, title=extra_title, title_align="left"))

    panel_group = Group(*panels)

    if len(panels) > 0:
        rprint()
        rprint(Panel(panel_group, title=title, title_align="left"))

    # github actions
    title = Text("Github Actions Dependencies", style="bold")
    text = Text()

    for idx, gh_dep in enumerate(project.github_actions_dependencies):
        text.append(gh_dep.package_name)
        text.append(str(gh_dep.specifier), style="green")

        if idx < len(project.github_actions_dependencies) - 1:
            text.append("\n")

    if len(project.github_actions_dependencies) > 0:
        rprint()
        rprint(Panel(text, title=title, title_align="left"))

    # pre-commit actions
    title = Text("Pre-commit Dependencies", style="bold")
    text = Text()

    for idx, pc_dep in enumerate(project.pre_commit_dependencies):
        text.append(pc_dep.package_name)
        text.append(str(pc_dep.specifier), style="green")

        if idx < len(project.pre_commit_dependencies) - 1:
            text.append("\n")

    if len(project.pre_commit_dependencies) > 0:
        rprint()
        rprint(Panel(text, title=title, title_align="left"))


@app.command()
def check_dependency(
    dependency: str,
    project_path: str = "",
):
    """Checks whether a dependency needs updating.

    Args:
        dependency: Name of the dependency to check.
        project_path: Path to the project. Defaults to the current working directory.
    """
    project = Project(
        project_path=project_path,
        gh_pat=GH_PAT,
    )

    try:
        dep = project.get_dependency(name=dependency)
    except RuntimeError as e:
        rprint(f"Cannot find {dependency} in {project.name}.")
        raise typer.Exit(code=1) from e

    asyncio.run(dep.save_data())

    title = Text("Dependency Check", style="bold")
    needs_update = dep.needs_update()

    text = Text(dep.package_name)
    text.append(str(dep.specifier), style="green")
    text.append("\n")
    utd = (
        Text("Needs updating!", style="red")
        if needs_update
        else Text("Up to date!", style="green")
    )
    text.append(utd)
    text.append("\n")
    text.append("Latest version: ")
    text.append(str(dep.get_latest_version()), style="red" if needs_update else "green")

    rprint(Panel(text, title=title, title_align="left"))


@app.command()
def needs_updating(
    project_path: str = "",
    base: bool = True,
    optional_deps: bool = True,
    group_deps: bool = True,
    github_actions: bool = True,
    pre_commit: bool = True,
):
    """List the dependencies that need updating.

    Args:
        project_path: Path to the project. Defaults to the current working directory.
        base: If set to True, includes the base dependencies. Defaults to True.
        optional_deps: If set to True, includes the optional dependencies. Defaults to
            True.
        group_deps: If set to True, includes the dependency groups. Defaults to True.
        github_actions: If set to True, includes the github actions dependencies.
            Defaults to True.
        pre_commit: If set to True, includes the pre-commit dependencies. Defaults to
            True.
    """
    # create project object
    project = Project(
        project_path=project_path,
        gh_pat=GH_PAT,
    )

    # fetch relevant data
    if base or optional_deps or group_deps:
        project.pypi_dependency_data_async()

    if github_actions or pre_commit:
        project.github_dependency_data_async()

    title = Text("Dependencies to Update", style="bold")
    text = Text()
    deps: list[Dependency] = []

    if base:
        deps.extend(project.base_dependencies)

    if optional_deps:
        deps.extend(project.optional_dependencies)

    if group_deps:
        deps.extend(project.group_dependencies)

    if github_actions:
        deps.extend(project.github_actions_dependencies)

    if pre_commit:
        deps.extend(project.pre_commit_dependencies)

    # use a counter to help with new lines
    counter = 0

    for dep in deps:
        if dep.needs_update():
            if counter > 0:
                text.append("\n")

            text.append(f"{dep.package_name}: ")
            text.append(str(dep.specifier), style="red")
            text.append(" -> ")
            text.append(str(dep.get_latest_version()), style="green")
            counter += 1

    if counter == 0:
        text.append("All version are up to date!")

    rprint(Panel(text, title=title, title_align="left"))


@app.command()
def latest_versions(
    project_path: str = "",
    base: bool = True,
    optional_deps: bool = True,
    group_deps: bool = True,
    github_actions: bool = False,
    pre_commit: bool = True,
):
    """List the dependencies that aren't pinned to the latest version.

    Args:
        project_path: Path to the project. Defaults to the current working directory.
        base: If set to True, includes the base dependencies. Defaults to True.
        optional_deps: If set to True, includes the optional dependencies. Defaults to
            True.
        group_deps: If set to True, includes the dependency groups. Defaults to True.
        github_actions: If set to True, includes the github actions dependencies.
            Defaults to False.
        pre_commit: If set to True, includes the pre-commit dependencies. Defaults to
            True.
    """
    # create project object
    project = Project(
        project_path=project_path,
        gh_pat=GH_PAT,
    )

    # fetch relevant data
    if base or optional_deps or group_deps:
        project.pypi_dependency_data_async()

    if github_actions or pre_commit:
        project.github_dependency_data_async()

    title = Text("Latest Versions", style="bold")
    text = Text()
    deps: list[Dependency] = []

    if base:
        deps.extend(project.base_dependencies)

    if optional_deps:
        deps.extend(project.optional_dependencies)

    if group_deps:
        deps.extend(project.group_dependencies)

    if github_actions:
        deps.extend(project.github_actions_dependencies)

    if pre_commit:
        deps.extend(project.pre_commit_dependencies)

    # use a counter to help with new lines
    counter = 0

    for dep in deps:
        if not dep.is_specifier_latest():
            if counter > 0:
                text.append("\n")

            text.append(f"{dep.package_name}: ")
            text.append(str(dep.specifier), style="red")
            text.append(" -> ")
            text.append(str(dep.get_latest_version()), style="green")
            counter += 1

    if counter == 0:
        text.append("All version are up to date!")

    rprint(Panel(text, title=title, title_align="left"))


@app.command()
def update(
    dependency: str,
    version: str | None = None,
    project_path: str = "",
):
    """_summary_.

    Make sure branch locally and on github do not already exist!

    Args:
        dependency: _description_
        version: _description_
        project_path: _description_
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("Creating project...")
        project = Project(
            project_path=project_path,
            gh_pat=GH_PAT,
        )

        # search for dependency and save old version
        try:
            dep = project.get_dependency(name=dependency)
            old_ver = str(sorted(dep.specifier, key=str)[0].version)
        except RuntimeError as e:
            rprint(f"Cannot find {dependency} in {project.name}.")
            raise typer.Exit(code=1) from e

        # fetch data from pypi/github
        progress.update(task, description="Fetching dependency data...")
        asyncio.run(dep.save_data())

        # get latest/desired version
        if version is None:
            version = str(dep.get_latest_version())

        # create new branch
        progress.update(task, description="Creating new branch...")
        if isinstance(dep, GitHubDependency) and dep.action:
            v = Version(version)
            branch_name = f"dependency/{dep.short_name}-v{v.major}"
        else:
            branch_name = f"dependency/{dep.short_name}-{version}"

        run_shell_command(["git", "checkout", "-b", branch_name])

        # get status of files before changes
        progress.update(task, description="Updating dependency...")
        files_before = get_git_status()

        # warning if there are changed files
        if len(files_before) > 0:
            msg = ":warning-emoji: [italic]There are uncomitted changes in your current"
            msg += " branch. upgrade-dependencies will only commit files that were"
            msg += " unmodified prior to running [bold]update[/bold][/italic]."
            rprint(msg)

        # update dependency
        project.update_dependency(dependency=dep, version=version)

        # run uv.lock, don't worry if it doesn't work (i.e. uv not installed)
        run_shell_command(["uv", "lock"], suppress_errors=True)

        # get status of files after changes
        files_after = get_git_status()

        # get only the files that were changed
        changed_files = [f for f in files_after if f not in files_before]

        # git add the changed files
        run_shell_command(["git", "add", *changed_files])

        # commit the changes
        progress.update(task, description="Committing changes...")
        if isinstance(dep, GitHubDependency) and dep.action:
            old_v = Version(old_ver)
            v = Version(version)
            commit_message = (
                f"Bump {dep.package_name} from v{old_v.major} to v{v.major}"
            )
        else:
            commit_message = f"Bump {dep.package_name} from {old_ver} to {version}"

        run_shell_command(["git", "commit", "-m", commit_message])

        # push the branch to GitHub
        progress.update(task, description="Pushing changes to GitHub...")
        run_shell_command(["git", "push", "origin", branch_name])

        # create pr_body
        progress.update(task, description="Creating pull request...")
        if isinstance(dep, PyPIDependency):
            url = f"https://pypi.org/project/{dep.package_name}"
            pr_body = f"Bumps [{dep.package_name}]({url}) from {old_ver} to {version}."
        elif isinstance(dep, GitHubDependency):
            old_v = Version(old_ver)
            v = Version(version)
            url = f"https://github.com/{dep.owner}/{dep.repo}"
            pr_body = (
                f"Bumps [{dep.package_name}]({url}) from v{old_v.major} to v{v.major}."
            )
        else:
            pr_body = ""

        # create pull request
        pr = run_shell_command(
            [
                "gh",
                "pr",
                "create",
                "-a",
                "@me",
                "--base",
                "master",
                "--body",
                pr_body,
                "--label",
                "dependencies",
                "--title",
                commit_message,
            ],
        )

        # re-checkout master
        run_shell_command(["git", "checkout", "master"])

    rprint(f"✅ {dep.package_name} updated! View the pull request at {pr.stdout}")


def main():
    """_summary_."""
    app()
