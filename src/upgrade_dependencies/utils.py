"""Upgrade dependencies utilities module."""

import glob
import os
import subprocess
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from upgrade_dependencies.dependency import GitHubDependency

yaml = YAML()


def extract_variable_from_file(
    file_path: str,
    variable_name: str,
) -> list[str]:
    """Function to extract all values of a particular variable from a YAML file.

    Args:
        file_path: _description_
        variable_name: _description_

    Returns:
        _description_
    """
    with Path(file_path).open("r") as f:
        data: Any = yaml.load(f)  # pyright: ignore

    # use a stack to process items without recursion
    stack: list[Any] = [data]  # stack to hold data elements to process
    variable_list: list[str] = []

    while stack:
        current = stack.pop()

        if isinstance(current, dict):  # if the current item is a dictionary
            for key, value in current.items():  # pyright: ignore[reportUnknownVariableType]
                if key == variable_name and isinstance(
                    value,
                    str,
                ):  # check key and type
                    variable_list.append(value)
                elif isinstance(value, dict | list):  # add nested structures to stack
                    stack.append(value)
        elif isinstance(current, list):  # if the current item is a list
            # add all elements to the stack
            stack.extend(current)  # pyright: ignore[reportUnknownArgumentType]

    return variable_list


def extract_from_yml_directory(
    gha_path: Path,
    variable_name: str,
) -> list[str]:
    """Function to process all YAML files in a directory.

    Args:
        gha_path: _description_
        variable_name: _description_

    Returns:
        _description_
    """
    values: list[str] = []

    # Find all .yml and .yaml files in the directory
    yaml_files = glob.glob(os.path.join(gha_path, "*.yml")) + glob.glob(
        os.path.join(gha_path, "*.yaml"),
    )

    for file_path in yaml_files:
        file_values = extract_variable_from_file(
            file_path=file_path,
            variable_name=variable_name,
        )
        values.extend(file_values)

    return values


def parse_pre_commit_config(file_path: Path) -> list[dict[str, str]]:
    """_summary_.

    Args:
        file_path: _description_

    Returns:
        _description_
    """
    with file_path.open("r") as f:
        data = yaml.load(f)  # pyright: ignore

    repos_info: list[dict[str, str]] = []

    # Extract repos and their information
    if "repos" in data and isinstance(data["repos"], list):
        for repo_entry in data["repos"]:  # pyright: ignore
            if isinstance(repo_entry, dict):
                repo_url = repo_entry.get("repo")  # pyright:ignore
                rev = repo_entry.get("rev")  # pyright:ignore
                if repo_url and rev:
                    repos_info.append({"repo": repo_url, "rev": rev})

    return repos_info


def update_uv(
    gha_path: Path,
    new_version: str,
) -> None:
    """_summary_.

    Args:
        gha_path: _description_
        new_version: _description_
    """
    # Find all .yml and .yaml files in the directory
    yaml_files = glob.glob(os.path.join(gha_path, "*.yml")) + glob.glob(
        os.path.join(gha_path, "*.yaml"),
    )

    for file_path in yaml_files:
        with Path(file_path).open("r") as f:
            data: dict[str, Any] = yaml.load(f)  # pyright: ignore

        try:
            data["env"]["UV_VERSION"] = new_version

            # temp_file = Path(file_path).with_suffix(".temp")
            with Path(file_path).open("w") as temp_f:
                yaml.dump(data, temp_f)  # pyright: ignore
        except KeyError:
            continue


def update_github_workflows(
    gha_path: Path,
    dependency: GitHubDependency,
    new_version: str,
) -> None:
    """_summary_.

    Args:
        gha_path: _description_
        dependency: _description_
        new_version: _description_
    """
    # Find all .yml and .yaml files in the directory
    yaml_files = glob.glob(os.path.join(gha_path, "*.yml")) + glob.glob(
        os.path.join(gha_path, "*.yaml"),
    )

    for file_path in yaml_files:
        with Path(file_path).open("r") as f:
            data: dict[str, Any] = yaml.load(f)  # pyright: ignore

        if dependency.full_version is not None:
            prefix = dependency.full_version.split("/")[0]
            new_req = f"{dependency.package_name}@{prefix}/v{new_version}"
        else:
            new_req = f"{dependency.package_name}@v{new_version}"

        changed = update_github_action_dependency(
            d=data,  # pyright: ignore
            dependency=dependency.package_name,
            new_requirement=new_req,
        )

        if changed:
            # temp_file = Path(file_path).with_suffix(".temp")
            with Path(file_path).open("w") as temp_f:
                yaml.dump(data, temp_f)  # pyright: ignore


def update_github_action_dependency(
    d: dict[str, Any],
    dependency: str,
    new_requirement: str,
    changed: bool = False,
) -> bool:
    """Recursively replace values of a given key in a nested dictionary.

    Args:
        d: _description_
        dependency: _description_
        new_requirement: _description_
        changed: _description_

    Returns:
        If the value has been replaced in any level of recursion
    """
    if isinstance(d, dict):  # pyright: ignore
        for key, value in d.items():
            if key == "uses":
                if "@" in value:
                    package_name, _ = value.split("@", maxsplit=1)
                else:
                    package_name = value

                if package_name == dependency:
                    d[key] = new_requirement
                    changed = True
            elif isinstance(value, dict):
                changed = update_github_action_dependency(
                    value,  # pyright: ignore
                    dependency,
                    new_requirement,
                    changed,
                )
            elif isinstance(value, list):
                for item in value:  # pyright: ignore
                    changed = update_github_action_dependency(
                        item,  # pyright: ignore
                        dependency,
                        new_requirement,
                        changed,
                    )

    return changed


def update_pre_commit(
    file_path: Path,
    dependency: GitHubDependency,
    new_version: str,
) -> None:
    """_summary_.

    Args:
        file_path: _description_
        dependency: _description_
        new_version: _description_
    """
    with Path(file_path).open("r") as f:
        data: dict[str, Any] = yaml.load(f)  # pyright: ignore

    # get repo url
    url = f"https://github.com/{dependency.owner}/{dependency.repo}"

    for repo in data["repos"]:  # pyright: ignore
        if repo["repo"] == url:
            v_str = "v" if dependency.has_v else ""
            repo["rev"] = f"{v_str}{new_version}"

    # temp_file = Path(file_path).with_suffix(".temp")
    with Path(file_path).open("w") as temp_f:
        yaml.dump(data, temp_f)  # pyright: ignore


def run_shell_command(
    shell_args: list[str],
    suppress_errors: bool = False,
) -> Any:
    """_summary_.

    Args:
        shell_args: _description_
        suppress_errors: _description_

    Returns:
        _description_
    """
    if suppress_errors:
        res = subprocess.run(  # noqa: S603
            shell_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        try:
            res = subprocess.run(shell_args, check=True, capture_output=True, text=True)  # noqa: S603
        except subprocess.CalledProcessError as e:
            msg = f"Command failed with return code {e.returncode}.\n"
            msg += f"Error output: {e.stderr}"
            raise RuntimeError(msg) from e

    return res


def get_git_status() -> list[str]:
    """Get the list of modified or untracked files from git status.

    Returns:
        _description_
    """
    result = run_shell_command(["git", "status", "-s"])

    # parse the result to get the list of files
    changed_files: list[str] = []

    for line in result.stdout.strip().split("\n"):
        if len(line) > 0:
            status, file_path = line.split(maxsplit=1)  # status and file name

            if status in ["M", "A", "D"]:  # modified, added, or deleted
                changed_files.append(file_path)

    return changed_files


def format_all_yml_files() -> None:
    """Formats the workflow and pre-commit config yaml files."""
    # pre-commit
    pre_commit_path = Path(".pre-commit-config.yaml")

    with pre_commit_path.open("r") as f:
        data: dict[str, Any] = yaml.load(f)  # pyright: ignore

    with pre_commit_path.open("w") as temp_f:
        yaml.dump(data, temp_f)  # pyright: ignore

    # workflows
    workflows_dir = Path("") / ".github" / "workflows"

    yaml_files = glob.glob(os.path.join(workflows_dir, "*.yml")) + glob.glob(
        os.path.join(workflows_dir, "*.yaml"),
    )

    for file_path in yaml_files:
        with Path(file_path).open("r") as f:
            data: dict[str, Any] = yaml.load(f)  # pyright: ignore

        with Path(file_path).open("w") as temp_f:
            yaml.dump(data, temp_f)  # pyright: ignore
