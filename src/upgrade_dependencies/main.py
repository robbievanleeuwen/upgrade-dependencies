"""CLI package."""

import os

import typer

# import rich
from upgrade_dependencies.project import Project

app = typer.Typer()
GH_PAT = os.getenv("GH_PAT")

# TODO: specify base dir and assume project structure!


@app.command()
def check_dependency(
    dependency: str,
    project_path: str = "",
    is_async: bool = True,
):
    """Checks whether a dependency needs updating.

    Args:
        dependency: Name of the dependency to check.
        project_path: Path to the project. Defaults to the current working directory.
        is_async: If set to True, asynchronously fetches the package data.
    """
    project = Project(
        project_path=project_path,
        is_async=is_async,
        gh_pat=GH_PAT,
    )

    for d in project.dependencies:
        if d.package_name == dependency:
            dep = d
            break
    else:
        print(f"Cannot find {dependency} in {project.name}.")
        return

    print(f"Dependency: {dep.package_name}")
    print(f"Version: {dep.specifier}")
    print(f"Latest version: {dep.get_latest_version()}")
    print(f"Needs Updating: {dep.needs_update()}")


@app.command()
def goodbye(name: str, formal: bool = False):
    """_summary_.

    Args:
        name: _description_
        formal: _description_. Defaults to False.
    """
    if formal:
        print(f"Goodbye Ms. {name}. Have a good day.")
    else:
        print(f"Bye {name}!")


def main():
    """_summary_."""
    app()
