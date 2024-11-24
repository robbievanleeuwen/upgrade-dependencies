"""Upgrade dependencies utilities module."""

import glob
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml


def extract_uses_from_file(file_path: str) -> list[str]:
    """Function to extract all 'uses' values from a YAML file.

    Args:
        file_path: _description_

    Returns:
        _description_
    """
    with Path(file_path).open("r") as f:
        data: Any = yaml.safe_load(f)

    # use a stack to process items without recursion
    stack: list[Any] = [data]  # stack to hold data elements to process
    uses_list: list[str] = []

    while stack:
        current = stack.pop()

        if isinstance(current, dict):  # if the current item is a dictionary
            for key, value in current.items():  # pyright: ignore[reportUnknownVariableType]
                if key == "uses" and isinstance(value, str):  # check key and type
                    uses_list.append(value)
                elif isinstance(value, dict | list):  # add nested structures to stack
                    stack.append(value)
        elif isinstance(current, list):  # if the current item is a list
            # add all elements to the stack
            stack.extend(current)  # pyright: ignore[reportUnknownArgumentType]

    return uses_list


def extract_uv_version_from_file(file_path: str) -> list[str]:
    """Function to extract UV_VERSION from a YAML file.

    Args:
        file_path: _description_

    Returns:
        _description_
    """
    with Path(file_path).open("r") as f:
        data = yaml.safe_load(f)

    # Directly access the 'env' key if it exists
    if isinstance(data, dict) and "env" in data:
        env = data.get("env")  # pyright: ignore
        if isinstance(env, dict):
            return [env.get("UV_VERSION")]  # pyright: ignore
    return []


def extract_from_yml_directory(
    gha_path: str,
    extract_method: Callable[[str], list[str]],
) -> list[str]:
    """Function to process all YAML files in a directory.

    Args:
        gha_path: _description_
        extract_method: _description_

    Returns:
        _description_
    """
    uses_values: list[str] = []

    # Find all .yml and .yaml files in the directory
    yaml_files = glob.glob(os.path.join(gha_path, "*.yml")) + glob.glob(
        os.path.join(gha_path, "*.yaml"),
    )

    for file_path in yaml_files:
        file_uses = extract_method(file_path)
        uses_values.extend(file_uses)

    return uses_values
