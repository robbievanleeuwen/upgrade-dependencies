"""Class for a python project."""

import asyncio
from pathlib import Path
from typing import Any

import tomlkit
from packaging.requirements import InvalidRequirement, Requirement

from upgrade_dependencies.dependency import Dependency


class Project:
    """_summary_."""

    name: str
    dependencies: list[Dependency]

    def __init__(
        self,
        pyproject_path: str = "pyproject.toml",
        is_async: bool = True,
    ) -> None:
        """_summary_.

        Args:
            pyproject_path: _description_
            is_async: _description_
        """
        # load pyproject.toml
        with Path(pyproject_path).open("r") as f:
            cfg = tomlkit.load(fp=f).unwrap()

        # get project name
        self.name = cfg["project"]["name"]

        # create list of dependencies to add
        project_dependencies: list[dict[str, Any]] = []

        # base dependencies
        for dep in cfg["project"]["dependencies"]:
            # parse requirement
            req = parse_requirement(requirement=dep)
            project_dependencies.append(
                {
                    "package_name": req.name,
                    "specifier": req.specifier,
                    "base": True,
                    "extra": None,
                    "group": None,
                },
            )

        # optional dependencies
        opt_deps = cfg["project"].get("optional-dependencies")

        if opt_deps:
            for extra, deps in cfg["project"]["optional-dependencies"].items():
                for dep in deps:
                    req = parse_requirement(requirement=dep)
                    project_dependencies.append(
                        {
                            "package_name": req.name,
                            "specifier": req.specifier,
                            "base": False,
                            "extra": extra,
                            "group": None,
                        },
                    )

        # dependency groups
        dep_groups = cfg.get("dependency-groups")

        if dep_groups:
            for group, deps in cfg["dependency-groups"].items():
                for dep in deps:
                    req = parse_requirement(requirement=dep)
                    project_dependencies.append(
                        {
                            "package_name": req.name,
                            "specifier": req.specifier,
                            "base": False,
                            "extra": None,
                            "group": group,
                        },
                    )

        # add dependency objects
        self.dependencies = []

        for proj_dep in project_dependencies:
            self.dependencies.append(Dependency(**proj_dep))

        # fetch pypi data
        if is_async:
            self.pypi_dependency_data_async()
        else:
            for dep in self.dependencies:
                dep.save_pypi_data()

    @property
    def base_dependencies(self) -> list[Dependency]:
        """_summary_.

        Returns:
            _description_
        """
        return [dep for dep in self.dependencies if dep.base]

    @property
    def optional_dependencies(self) -> list[Dependency]:
        """_summary_.

        Returns:
            _description_
        """
        return [dep for dep in self.dependencies if dep.extra]

    @property
    def group_dependencies(self) -> list[Dependency]:
        """_summary_.

        Returns:
            _description_
        """
        return [dep for dep in self.dependencies if dep.group]

    async def fetch_all_pypi_data(self) -> None:
        """Fetches PyPI data for all Dependency objects concurrently."""
        results = await asyncio.gather(
            *[dep.save_pypi_data_async() for dep in self.dependencies],
            return_exceptions=True,
        )

        for dep, result in zip(self.dependencies, results, strict=False):
            if isinstance(result, Exception):
                print(f"Failed to fetch data for {dep.package_name}: {result}")

    def pypi_dependency_data_async(self) -> None:
        """Synchronously fetches PyPI data for all Dependency objects."""
        asyncio.run(self.fetch_all_pypi_data())

    def __repr__(self) -> str:
        """_summary_.

        Returns:
            _description_
        """
        return self.name


def parse_requirement(requirement: str) -> Requirement:
    """_summary_.

    Args:
        requirement: _description_

    Returns:
        _description_
    """
    try:
        req = Requirement(requirement)
    except InvalidRequirement as e:
        msg = f"Invalid requirement {requirement}: {e}"
        raise AttributeError(msg) from e

    return req
