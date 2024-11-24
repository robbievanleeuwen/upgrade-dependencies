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
    gh_pat: str | None
    dependencies: list[Dependency]
    github_dependencies: list[GithubDependency]

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

        # workflows dir
        workflows_dir = Path(project_path) / ".github" / "workflows"

        # uv version
        if workflows_dir.exists():
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

        # parse github actions
        self.github_dependencies = []

        if workflows_dir.exists():
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

        # pre-commit dir
        pre_commit_path = Path(project_path) / ".pre-commit-config.yaml"

        # parse pre-commit-config
        if pre_commit_path.exists():
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
    def optional_dependencies_grouped(self) -> dict[str, list[Dependency]]:
        """_summary_.

        Returns:
            _description_
        """
        grouped_deps: dict[str, list[Dependency]] = {}

        for opt_dep in self.optional_dependencies:
            if isinstance(opt_dep.extra, str):
                grouped_deps.setdefault(opt_dep.extra, []).append(opt_dep)

        return grouped_deps

    @property
    def group_dependencies(self) -> list[Dependency]:
        """_summary_.

        Returns:
            _description_
        """
        return [dep for dep in self.dependencies if dep.group]

    @property
    def group_dependencies_grouped(self) -> dict[str, list[Dependency]]:
        """_summary_.

        Returns:
            _description_
        """
        grouped_deps: dict[str, list[Dependency]] = {}

        for group_dep in self.group_dependencies:
            if isinstance(group_dep.group, str):
                grouped_deps.setdefault(group_dep.group, []).append(group_dep)

        return grouped_deps

    @property
    def github_actions(self) -> list[GithubDependency]:
        """_summary_.

        Returns:
            _description_
        """
        return [gh_dep for gh_dep in self.github_dependencies if gh_dep.action]

    @property
    def pre_commit_actions(self) -> list[GithubDependency]:
        """_summary_.

        Returns:
            _description_
        """
        return [gh_dep for gh_dep in self.github_dependencies if gh_dep.pre_commit]

    def fetch_all_data(self) -> None:
        """Fetches all (PyPI and GitHub) data."""
        self.pypi_dependency_data_async()
        self.github_dependency_data_async()

    async def fetch_all_pypi_data(self) -> None:
        """Fetches PyPI data for all Dependency objects concurrently."""
        results = await asyncio.gather(
            *[dep.save_pypi_data() for dep in self.dependencies],
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
                gh_dep.save_github_data(gh_pat=self.gh_pat)
                for gh_dep in self.github_dependencies
            ],
            return_exceptions=True,
        )

    def github_dependency_data_async(self) -> None:
        """Synchronously fetches GitHub data for all dependency objects."""
        asyncio.run(self.fetch_all_github_data())

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
