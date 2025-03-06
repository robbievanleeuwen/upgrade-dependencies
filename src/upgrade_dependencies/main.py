"""CLI package."""

import asyncio
import os
from typing import TYPE_CHECKING, Annotated

import typer
from packaging.version import Version
from rich import print as rprint
from rich.console import Group
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

import upgrade_dependencies.utils as utils
from upgrade_dependencies.dependency import GitHubDependency, PyPIDependency
from upgrade_dependencies.project import Project

if TYPE_CHECKING:
    from upgrade_dependencies.dependency import Dependency

app = typer.Typer()
GH_PAT = os.getenv("GH_PAT")


@app.command()
def list_dependencies():
    """List all the dependencies for the project."""
    project = Project(gh_pat=GH_PAT)

    # base dependencies
    title = Text("Base Dependencies", style="bold")
    text = Text()

    for idx, base_dep in enumerate(project.base_dependencies):
        text.append(base_dep.package_plus_extras)
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
            text.append(opt_dep.package_plus_extras)
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
            text.append(group_dep.package_plus_extras)
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
    dependency: Annotated[str, typer.Argument(help="Name of the dependency to check")],
):
    """Checks whether a dependency needs updating."""
    project = Project(gh_pat=GH_PAT)

    try:
        dep = project.get_dependency(name=dependency)
    except RuntimeError as e:
        rprint(f"Cannot find {dependency} in {project.name}.")
        raise typer.Exit(code=1) from e

    if isinstance(dep, GitHubDependency):
        asyncio.run(dep.save_data(gh_pat=GH_PAT))
    else:
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
    base: Annotated[bool, typer.Option(help="Include base dependencies")] = True,
    optional_deps: Annotated[
        bool,
        typer.Option(help="Include optional dependencies"),
    ] = True,
    group_deps: Annotated[bool, typer.Option(help="Include dependency groups")] = True,
    github_actions: Annotated[
        bool,
        typer.Option(help="Include GitHub actions dependencies"),
    ] = True,
    pre_commit: Annotated[
        bool,
        typer.Option(help="Include pre-commit dependencies"),
    ] = True,
):
    """Lists the dependencies that need updating."""
    # create project object
    project = Project(gh_pat=GH_PAT)

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
    base: Annotated[bool, typer.Option(help="Include base dependencies")] = True,
    optional_deps: Annotated[
        bool,
        typer.Option(help="Include optional dependencies"),
    ] = True,
    group_deps: Annotated[bool, typer.Option(help="Include dependency groups")] = True,
    github_actions: Annotated[
        bool,
        typer.Option(help="Include GitHub actions dependencies"),
    ] = False,
    pre_commit: Annotated[
        bool,
        typer.Option(help="Include pre-commit dependencies"),
    ] = True,
):
    """List the dependencies that aren't specified to the latest version."""
    # create project object
    project = Project(gh_pat=GH_PAT)

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
    dependency: Annotated[str, typer.Argument(help="Dependency to update")],
    version: Annotated[
        str | None,
        typer.Option(help="Version to update to, latest version if not specified"),
    ] = None,
    target_branch: Annotated[
        str,
        typer.Option(help="Name of the branch to merge PR to"),
    ] = "master",
):
    """Updates a dependency to a specific (or latest) version.

    Makes changes to the dependency specification locally and creates a GitHub pull
    request on a new branch (branch name = dependency/{package_name}-{version}). Make
    sure this branch name does not exist locally or on GitHub.

    Requires git and the GitHub CLI to be installed. It is recommended to have a clean
    git before running this command.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("Creating project...")
        project = Project(gh_pat=GH_PAT)

        # search for dependency and save old version
        try:
            dep = project.get_dependency(name=dependency)
            old_ver = str(sorted(dep.specifier, key=str)[0].version)
        except RuntimeError as e:
            rprint(f":no_entry_sign: Cannot find {dependency} in {project.name}.")
            raise typer.Exit(code=1) from e

        # fetch data from pypi/github
        progress.update(task, description="Fetching dependency data...")

        if isinstance(dep, GitHubDependency):
            asyncio.run(dep.save_data(gh_pat=GH_PAT))
        else:
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

        utils.run_shell_command(["git", "checkout", "-b", branch_name])

        # get status of files before changes
        progress.update(task, description="Updating dependency...")
        files_before = utils.get_git_status()

        # warning if there are changed files
        if len(files_before) > 0:
            msg = ":warning-emoji: [italic]There are uncomitted changes in your current"
            msg += " branch. upgrade-dependencies will only commit files that were"
            msg += " unmodified prior to running [bold]update[/bold][/italic]."
            rprint(msg)

        # update dependency
        project.update_dependency(dependency=dep, version=version)

        # run uv.lock, don't worry if it doesn't work (i.e. uv not installed)
        utils.run_shell_command(["uv", "lock"], suppress_errors=True)

        # get status of files after changes
        files_after = utils.get_git_status()

        # get only the files that were changed
        changed_files = [f for f in files_after if f not in files_before]

        # git add the changed files
        utils.run_shell_command(["git", "add", *changed_files])

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

        utils.run_shell_command(["git", "commit", "-m", commit_message])

        # push the branch to GitHub
        progress.update(task, description="Pushing changes to GitHub...")
        utils.run_shell_command(["git", "push", "origin", branch_name])

        # create pr_body
        progress.update(task, description="Creating pull request...")
        if isinstance(dep, PyPIDependency):
            url = f"https://pypi.org/project/{dep.package_name}"
            pr_body = f"Bumps [{dep.package_name}]({url}) from {old_ver} to {version}."
        elif isinstance(dep, GitHubDependency):
            url = f"https://github.com/{dep.owner}/{dep.repo}"
            if dep.action:
                old_v = Version(old_ver)
                v = Version(version)
                pr_body = f"Bumps [{dep.package_name}]({url}) from v{old_v.major} to"
                pr_body += f" v{v.major}."
            else:
                pr_body = (
                    f"Bumps [{dep.package_name}]({url}) from {old_ver} to {version}."
                )
        else:
            pr_body = ""

        # create pull request
        pr = utils.run_shell_command(
            [
                "gh",
                "pr",
                "create",
                "-a",
                "@me",
                "--base",
                target_branch,
                "--body",
                pr_body,
                "--label",
                "dependencies",
                "--title",
                commit_message,
            ],
        )

        # re-checkout master branch
        utils.run_shell_command(["git", "checkout", target_branch])

    msg = f"✅ [bold]{dep.package_name}[/bold] updated! View the pull request at"
    msg += f" {pr.stdout}"
    rprint(msg)


@app.command()
def format_yml():
    """Formats the workflow and pre-commit config yaml files."""
    utils.format_all_yml_files()
