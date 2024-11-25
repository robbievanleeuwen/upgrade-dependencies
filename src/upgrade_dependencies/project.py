"""Class for a python project."""

import asyncio
from pathlib import Path
from typing import Any

import tomlkit
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from upgrade_dependencies.dependency import Dependency, GitHubDependency, PyPIDependency
from upgrade_dependencies.utils import (
    extract_from_yml_directory,
    parse_pre_commit_config,
)


class Project:
    """_summary_."""

    name: str
    gh_pat: str | None
    dependencies: list[Dependency]

    def __init__(
        self,
        project_path: str,
        gh_pat: str | None = None,
    ) -> None:
        """_summary_.

        Args:
            project_path: _description_
            gh_pat: _description_
        """
        # check pyproject.toml exists
        ppt_file_path = Path(project_path) / "pyproject.toml"

        if not ppt_file_path.exists():
            msg = f"{ppt_file_path} does not exist."
            raise ValueError(msg)

        # load pyproject.toml
        with Path(ppt_file_path).open("r") as f:
            cfg = tomlkit.load(fp=f).unwrap()

        # get project name
        self.name = cfg["project"]["name"]

        # save GitHub PAT
        self.gh_pat = gh_pat

        # initialise dependencies
        self.dependencies = []

        # get relevant paths
        workflows_dir = Path(project_path) / ".github" / "workflows"
        pre_commit_path = Path(project_path) / ".pre-commit-config.yaml"

        # save pypi dependencies
        self.save_pypi_dependencies(cfg=cfg, workflows_dir=workflows_dir)

        # save github dependencies
        self.save_github_dependencies(
            workflows_dir=workflows_dir,
            pre_commit_path=pre_commit_path,
        )

    def save_pypi_dependencies(
        self,
        cfg: dict[str, Any],
        workflows_dir: Path,
    ) -> None:
        """_summary_.

        Args:
            cfg: _description_
            workflows_dir: _description_
        """
        # create list of pypi dependencies to add
        pypi_dependencies: list[dict[str, Any]] = []

        # base dependencies
        for dep in cfg["project"]["dependencies"]:
            # parse requirement
            req = parse_requirement(requirement=dep)
            pypi_dependencies.append(
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
                    pypi_dependencies.append(
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
                    pypi_dependencies.append(
                        {
                            "package_name": req.name,
                            "specifier": req.specifier,
                            "base": False,
                            "extra": None,
                            "group": group,
                        },
                    )

        # add dependency objects
        for pp_dep in pypi_dependencies:
            self.dependencies.append(PyPIDependency(**pp_dep))

        # uv version
        if workflows_dir.exists():
            uv_version = extract_from_yml_directory(
                gha_path=workflows_dir,
                variable_name="UV_VERSION",
            )

            if len(uv_version) > 0:
                self.dependencies.append(
                    PyPIDependency(
                        package_name="uv",
                        specifier=SpecifierSet(f"=={uv_version[0]}"),
                        base=False,
                        group="uv",
                    ),
                )

    def save_github_dependencies(
        self,
        workflows_dir: Path,
        pre_commit_path: Path,
    ) -> None:
        """_summary_.

        Args:
            workflows_dir: _description_
            pre_commit_path: _description_

        Returns:
            _description_
        """
        # parse github actions
        if workflows_dir.exists():
            github_actions = extract_from_yml_directory(
                gha_path=workflows_dir,
                variable_name="uses",
            )
            github_actions = list(set(github_actions))  # get unique set

            # add github actions objects
            for gha in github_actions:
                if "@" in gha:
                    package_name, version = gha.split("@", maxsplit=1)
                else:
                    package_name = gha
                    version = ""

                # handle branch name in tag e.g. pypa/gh-action-pypi-publish@release/v1
                if "/" in version:
                    full_version = version
                    version = version.split("/")[-1]
                else:
                    full_version = None

                v = Version(version)

                self.dependencies.append(
                    GitHubDependency(
                        package_name=package_name,
                        specifier=SpecifierSet(f"~={v.major}.{v.minor}"),
                        action=True,
                        pre_commit=False,
                        full_version=full_version,
                    ),
                )

        # parse pre-commit-config
        if pre_commit_path.exists():
            pre_commit_repos = parse_pre_commit_config(file_path=pre_commit_path)

            for pc_repo in pre_commit_repos:
                url = pc_repo["repo"]
                owner = url.split("/")[-2]
                repo = url.split("/")[-1]
                v = Version(pc_repo["rev"])

                self.dependencies.append(
                    GitHubDependency(
                        package_name=f"{owner}/{repo}",
                        specifier=SpecifierSet(f"=={v}"),
                        action=False,
                        pre_commit=True,
                    ),
                )

    @property
    def base_dependencies(self) -> list[PyPIDependency]:
        """_summary_.

        Returns:
            _description_
        """
        return [
            dep
            for dep in self.dependencies
            if isinstance(dep, PyPIDependency) and dep.base
        ]

    @property
    def optional_dependencies(self) -> list[PyPIDependency]:
        """_summary_.

        Returns:
            _description_
        """
        return [
            dep
            for dep in self.dependencies
            if isinstance(dep, PyPIDependency) and dep.extra
        ]

    @property
    def optional_dependencies_grouped(self) -> dict[str, list[PyPIDependency]]:
        """_summary_.

        Returns:
            _description_
        """
        grouped_deps: dict[str, list[PyPIDependency]] = {}

        for opt_dep in self.optional_dependencies:
            if isinstance(opt_dep.extra, str):
                grouped_deps.setdefault(opt_dep.extra, []).append(opt_dep)

        return grouped_deps

    @property
    def group_dependencies(self) -> list[PyPIDependency]:
        """_summary_.

        Returns:
            _description_
        """
        return [
            dep
            for dep in self.dependencies
            if isinstance(dep, PyPIDependency) and dep.group
        ]

    @property
    def group_dependencies_grouped(self) -> dict[str, list[PyPIDependency]]:
        """_summary_.

        Returns:
            _description_
        """
        grouped_deps: dict[str, list[PyPIDependency]] = {}

        for group_dep in self.group_dependencies:
            if isinstance(group_dep.group, str):
                grouped_deps.setdefault(group_dep.group, []).append(group_dep)

        return grouped_deps

    @property
    def github_actions_dependencies(self) -> list[GitHubDependency]:
        """_summary_.

        Returns:
            _description_
        """
        return [
            dep
            for dep in self.dependencies
            if isinstance(dep, GitHubDependency) and dep.action
        ]

    @property
    def pre_commit_dependencies(self) -> list[GitHubDependency]:
        """_summary_.

        Returns:
            _description_
        """
        return [
            dep
            for dep in self.dependencies
            if isinstance(dep, GitHubDependency) and dep.pre_commit
        ]

    def fetch_all_data(self) -> None:
        """Fetches all (PyPI and GitHub) data."""
        self.pypi_dependency_data_async()
        self.github_dependency_data_async()

    async def fetch_all_pypi_data(self) -> None:
        """Fetches PyPI data for all Dependency objects concurrently."""
        results = await asyncio.gather(
            *[
                dep.save_data()
                for dep in self.dependencies
                if isinstance(dep, PyPIDependency)
            ],
            return_exceptions=True,
        )

        for dep, result in zip(self.dependencies, results, strict=False):
            if isinstance(result, Exception):
                print(f"Failed to fetch data for {dep.package_name}: {result}")

    def pypi_dependency_data_async(self) -> None:
        """Synchronously fetches PyPI data for all Dependency objects."""
        asyncio.run(self.fetch_all_pypi_data())

    async def fetch_all_github_data(self) -> None:
        """Fetches GitHub data for all dependency objects concurrently."""
        await asyncio.gather(
            *[
                dep.save_data(gh_pat=self.gh_pat)
                for dep in self.dependencies
                if isinstance(dep, GitHubDependency)
            ],
            return_exceptions=True,
        )

    def github_dependency_data_async(self) -> None:
        """Synchronously fetches GitHub data for all dependency objects."""
        asyncio.run(self.fetch_all_github_data())

    def update_dependency(
        self,
        dependency: Dependency,
        version: str | None = None,
    ) -> None:
        """_summary_.

        Args:
            dependency: _description_
            version: _description_. Defaults to None.
        """
        pass

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
