"""Upgrade dependencies utilities module."""

import glob
import os
from pathlib import Path
from typing import Any

import yaml


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
        data: Any = yaml.safe_load(f)

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
    gha_path: str,
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


def parse_pre_commit_config(file_path: str) -> list[dict[str, str]]:
    """_summary_.

    Args:
        file_path: _description_

    Returns:
        _description_
    """
    with Path(file_path).open("r") as f:
        data = yaml.safe_load(f)

    repos_info: list[dict[str, str]] = []

    # Extract repos and their information
    if "repos" in data and isinstance(data["repos"], list):
        for repo_entry in data["repos"]:
            if isinstance(repo_entry, dict):
                repo_url = repo_entry.get("repo")  # pyright:ignore
                rev = repo_entry.get("rev")  # pyright:ignore
                if repo_url and rev:
                    repos_info.append({"repo": repo_url, "rev": rev})

    return repos_info
