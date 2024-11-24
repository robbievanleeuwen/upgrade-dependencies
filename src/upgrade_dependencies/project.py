"""Class for a python project."""

import asyncio
from pathlib import Path
from typing import Any

import tomlkit
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from upgrade_dependencies.dependency import Dependency
from upgrade_dependencies.github_dependency import GithubDependency
from upgrade_dependencies.utils import (
    extract_from_yml_directory,
    parse_pre_commit_config,
)


class Project:
    """_summary_."""

    name: str
    dependencies: list[Dependency]
    github_dependencies: list[GithubDependency]

    def __init__(
        self,
        pyproject_path: str = "pyproject.toml",
        workflows_dir: str | None = None,
        pre_commit_path: str | None = None,
        is_async: bool = True,
    ) -> None:
        """_summary_.

        Args:
            pyproject_path: _description_
            workflows_dir: _description_
            pre_commit_path: _description_
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

        # uv version
        if workflows_dir is not None:
            uv_version = extract_from_yml_directory(
                gha_path=workflows_dir,
                variable_name="UV_VERSION",
            )

            if len(uv_version) > 0:
                self.dependencies.append(
                    Dependency(
                        package_name="uv",
                        specifier=SpecifierSet(f"=={uv_version[0]}"),
                        base=False,
                        group="uv",
                    ),
                )

        # fetch pypi data
        if is_async:
            self.pypi_dependency_data_async()
        else:
            for dep in self.dependencies:
                dep.save_pypi_data()

        # parse github actions
        self.github_dependencies = []

        if workflows_dir is not None:
            github_actions = extract_from_yml_directory(
                gha_path=workflows_dir,
                variable_name="uses",
            )
            github_actions = list(set(github_actions))  # get unique set

            # add github actions objects
            for gha in github_actions:
                if "@" in gha:
                    action, version = gha.split("@", maxsplit=1)
                else:
                    action = gha
                    version = ""

                owner, repo = action.split("/", maxsplit=1)

                # handle additional "/"" e.g. pandoc/actions/setup@v1
                if "/" in repo:
                    repo = repo.split("/")[0]

                # handle branch name in tag e.g. pypa/gh-action-pypi-publish@release/v1
                if "/" in version:
                    version = version.split("/")[-1]

                v = Version(version)

                self.github_dependencies.append(
                    GithubDependency(
                        owner=owner,
                        repo=repo,
                        specifier=SpecifierSet(f"~={v.major}.{v.minor}"),
                        action=True,
                        pre_commit=False,
                    ),
                )

        # parse pre-commit-config
        if pre_commit_path is not None:
            pre_commit_repos = parse_pre_commit_config(file_path=pre_commit_path)

            for pc_repo in pre_commit_repos:
                url = pc_repo["repo"]
                owner = url.split("/")[-2]
                repo = url.split("/")[-1]
                v = Version(pc_repo["rev"])

                self.github_dependencies.append(
                    GithubDependency(
                        owner=owner,
                        repo=repo,
                        specifier=SpecifierSet(f"=={v}"),
                        action=False,
                        pre_commit=True,
                    ),
                )

        # fetch github data
        for gh_dep in self.github_dependencies:
            gh_dep.save_github_data()

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
