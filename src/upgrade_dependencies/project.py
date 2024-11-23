"""Class for a python project."""

from pathlib import Path

import tomlkit
from packaging.requirements import InvalidRequirement, Requirement

from upgrade_dependencies.dependency import Dependency


class Project:
    """_summary_."""

    name: str
    base_dependencies: list[Dependency]
    optional_dependencies: list[Dependency]
    group_dependencies: list[Dependency]

    def __init__(
        self,
        filename: str = "pyproject.toml",
    ) -> None:
        """_summary_.

        Args:
            filename: _description_
        """
        # load pyproject.toml
        with Path(filename).open("r") as f:
            cfg = tomlkit.load(fp=f).unwrap()

        # get project name
        self.name = cfg["project"]["name"]

        # add base dependencies
        self.base_dependencies = []

        for dep in cfg["project"]["dependencies"]:
            # parse requirement
            req = parse_requirement(requirement=dep)
            self.base_dependencies.append(
                Dependency(package_name=req.name, specifier=req.specifier),
            )

        # add optional dependencies
        self.optional_dependencies = []

        opt_deps = cfg["project"].get("optional-dependencies")

        if opt_deps:
            for extra, deps in cfg["project"]["optional-dependencies"].items():
                for dep in deps:
                    req = parse_requirement(requirement=dep)
                    self.base_dependencies.append(
                        Dependency(
                            package_name=req.name,
                            specifier=req.specifier,
                            base=False,
                            extra=extra,
                        ),
                    )

        # add dependency groups
        self.group_dependencies = []

        dep_groups = cfg.get("dependency-groups")

        if dep_groups:
            for group, deps in cfg["dependency-groups"].items():
                for dep in deps:
                    req = parse_requirement(requirement=dep)
                    self.base_dependencies.append(
                        Dependency(
                            package_name=req.name,
                            specifier=req.specifier,
                            base=False,
                            group=group,
                        ),
                    )

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
