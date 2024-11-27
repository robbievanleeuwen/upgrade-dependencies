"""Class for a python project."""

import asyncio
from pathlib import Path
from typing import Any

import tomlkit
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

import upgrade_dependencies.utils as utils
from upgrade_dependencies.dependency import Dependency, GitHubDependency, PyPIDependency


class Project:
    """_summary_."""

    name: str
    gh_pat: str | None
    dependencies: list[Dependency]
    project_path: str

    def __init__(
        self,
        project_path: str = "",
        gh_pat: str | None = None,
    ) -> None:
        """_summary_.

        Args:
            project_path: _description_
            gh_pat: _description_
        """
        # save project path
        self.project_path = project_path

        # check pyproject.toml exists
        ppt_file_path = Path(project_path) / "pyproject.toml"

        if not ppt_file_path.exists():
            msg = f"{ppt_file_path} does not exist."
            raise ValueError(msg)

        # load pyproject.toml
        with Path(ppt_file_path).open("r") as f:
            ppt = tomlkit.load(fp=f).unwrap()

        # get project name
        self.name = ppt["project"]["name"]

        # save GitHub PAT
        self.gh_pat = gh_pat

        # initialise dependencies
        self.dependencies = []

        # get relevant paths
        workflows_dir = Path(project_path) / ".github" / "workflows"
        pre_commit_path = Path(project_path) / ".pre-commit-config.yaml"

        # save pypi dependencies
        self.save_pypi_dependencies(ppt=ppt, workflows_dir=workflows_dir)

        # save github dependencies
        self.save_github_dependencies(
            workflows_dir=workflows_dir,
            pre_commit_path=pre_commit_path,
        )

    def save_pypi_dependencies(
        self,
        ppt: dict[str, Any],
        workflows_dir: Path,
    ) -> None:
        """_summary_.

        Args:
            ppt: _description_
            workflows_dir: _description_
        """
        # create list of pypi dependencies to add
        pypi_dependencies: list[dict[str, Any]] = []

        # base dependencies
        for dep in ppt["project"]["dependencies"]:
            # parse requirement
            req = parse_requirement(requirement=dep)
            pypi_dependencies.append(
                {
                    "package_name": req.name,
                    "specifier": req.specifier,
                    "extras": list(req.extras),
                    "base": True,
                    "extra": None,
                    "group": None,
                },
            )

        # optional dependencies
        opt_deps = ppt["project"].get("optional-dependencies")

        if opt_deps:
            for extra, deps in ppt["project"]["optional-dependencies"].items():
                for dep in deps:
                    req = parse_requirement(requirement=dep)
                    pypi_dependencies.append(
                        {
                            "package_name": req.name,
                            "specifier": req.specifier,
                            "extras": list(req.extras),
                            "base": False,
                            "extra": extra,
                            "group": None,
                        },
                    )

        # dependency groups
        dep_groups = ppt.get("dependency-groups")

        if dep_groups:
            for group, deps in ppt["dependency-groups"].items():
                for dep in deps:
                    req = parse_requirement(requirement=dep)
                    pypi_dependencies.append(
                        {
                            "package_name": req.name,
                            "specifier": req.specifier,
                            "extras": list(req.extras),
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
            uv_version = utils.extract_from_yml_directory(
                gha_path=workflows_dir,
                variable_name="UV_VERSION",
            )

            if len(uv_version) > 0:
                self.dependencies.append(
                    PyPIDependency(
                        package_name="uv",
                        specifier=SpecifierSet(f"=={uv_version[0]}"),
                        extras=[],
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
            github_actions = utils.extract_from_yml_directory(
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
            pre_commit_repos = utils.parse_pre_commit_config(file_path=pre_commit_path)

            for pc_repo in pre_commit_repos:
                url = pc_repo["repo"]
                owner = url.split("/")[-2]
                repo = url.split("/")[-1]
                v = Version(pc_repo["rev"])
                has_v = pc_repo["rev"][0] == "v"

                self.dependencies.append(
                    GitHubDependency(
                        package_name=f"{owner}/{repo}",
                        specifier=SpecifierSet(f"=={v}"),
                        action=False,
                        pre_commit=True,
                        has_v=has_v,
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
        )

    def github_dependency_data_async(self) -> None:
        """Synchronously fetches GitHub data for all dependency objects."""
        asyncio.run(self.fetch_all_github_data())

    def update_dependency(
        self,
        dependency: Dependency,
        version: str,
    ) -> None:
        """_summary_.

        Args:
            dependency: _description_
            version: _description_
        """
        # update pypi dependencies
        if isinstance(dependency, PyPIDependency):
            # handle special case uv, lives in github actions
            if dependency.package_name == "uv":
                workflows_dir = Path(self.project_path) / ".github" / "workflows"
                utils.update_uv(workflows_dir, version)
            else:
                # load pyproject.toml
                ppt_file_path = Path(self.project_path) / "pyproject.toml"

                with Path(ppt_file_path).open("r") as f:
                    ppt = tomlkit.load(fp=f)

                # find reference to dependency in the file and update the version
                if dependency.base:
                    deps: list[str] = ppt["project"]["dependencies"]  # pyright: ignore
                elif isinstance(dependency.extra, str):
                    deps: list[str] = ppt["project"]["optional-dependencies"][  # pyright: ignore
                        dependency.extra
                    ]
                elif isinstance(dependency.group, str):
                    deps: list[str] = ppt["dependency-groups"][dependency.group]  # pyright: ignore
                else:
                    msg = "Unknown dependency type."
                    raise RuntimeError(msg)

                for idx, dep in enumerate(deps):
                    req = parse_requirement(requirement=dep)

                    if req.name == dependency.package_name:
                        # build new requirement
                        new_req = build_new_requirement(
                            old_requirement=req,
                            new_version=version,
                        )
                        deps[idx] = new_req
                        break
                else:
                    msg = f"Cannot find {dependency}!"
                    raise RuntimeError(msg)

                # write new pyproject.toml file
                # temp_ppt = ppt_file_path.with_suffix(".temp")
                with Path(ppt_file_path).open("w") as temp_f:
                    tomlkit.dump(data=ppt, fp=temp_f)  # pyright: ignore
        # github dependencies
        elif isinstance(dependency, GitHubDependency):
            if dependency.action:
                # get workflows directory
                workflows_dir = Path(self.project_path) / ".github" / "workflows"

                # get major version release
                v = Version(version)

                # update dependency
                utils.update_github_workflows(
                    gha_path=workflows_dir,
                    dependency=dependency,
                    new_version=str(v.major),
                )
            elif dependency.pre_commit:
                # get pre-commit path
                pre_commit_path = Path(self.project_path) / ".pre-commit-config.yaml"

                # ensure x.x.x for version
                v = Version(version)

                # update dependency
                utils.update_pre_commit(
                    file_path=pre_commit_path,
                    dependency=dependency,
                    new_version=f"{v.major}.{v.minor}.{v.micro}",
                )

    def get_dependency(
        self,
        name: str,
    ) -> Dependency:
        """_summary_.

        Args:
            name: _description_

        Returns:
            _description_
        """
        for dependency in self.dependencies:
            if dependency.package_name == name:
                return dependency
        else:
            msg = "Cannot find {name} in the package!"
            raise RuntimeError(msg)

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


def build_new_requirement(
    old_requirement: Requirement,
    new_version: str,
) -> str:
    """_summary_.

    Args:
        old_requirement: _description_
        new_version: _description_

    Returns:
        _description_
    """
    name = old_requirement.name
    extras = list(old_requirement.extras)
    spec = sorted(old_requirement.specifier, key=str)[0].operator
    str_extras = f"[{",".join(extras)}]" if len(extras) > 0 else ""

    return f"{name}{str_extras}{spec}{new_version}"
