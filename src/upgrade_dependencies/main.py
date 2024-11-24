"""CLI package."""

import asyncio
import os

import typer
from rich import print as rprint
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from upgrade_dependencies.project import Project

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

    for idx, gh_dep in enumerate(project.github_actions):
        text.append(gh_dep.package_name)
        text.append(str(gh_dep.specifier), style="green")

        if idx < len(project.github_actions) - 1:
            text.append("\n")

    if len(project.github_actions) > 0:
        rprint()
        rprint(Panel(text, title=title, title_align="left"))

    # pre-commit actions
    title = Text("Pre-commit Dependencies", style="bold")
    text = Text()

    for idx, pc_dep in enumerate(project.pre_commit_actions):
        text.append(pc_dep.package_name)
        text.append(str(pc_dep.specifier), style="green")

        if idx < len(project.pre_commit_actions) - 1:
            text.append("\n")

    if len(project.pre_commit_actions) > 0:
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

    for d in project.dependencies:
        if d.package_name == dependency:
            dep = d
            break
    else:
        rprint(f"Cannot find {dependency} in {project.name}.")
        return

    asyncio.run(dep.save_pypi_data())

    rprint(f"Dependency: {dep.package_name}")
    rprint(f"Version: {dep.specifier}")
    rprint(f"Latest version: {dep.get_latest_version()}")
    rprint(f"Needs Updating: {dep.needs_update()}")


@app.command()
def goodbye(name: str, formal: bool = False):
    """_summary_.

    Args:
        name: _description_
        formal: _description_. Defaults to False.
    """
    if formal:
        rprint(f"Goodbye Ms. {name}. Have a good day.")
    else:
        rprint(f"Bye {name}!")


def main():
    """_summary_."""
    app()
