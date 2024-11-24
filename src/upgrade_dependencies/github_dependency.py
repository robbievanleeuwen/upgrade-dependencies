"""Class for a python project github dependency."""

from typing import Any

import httpx
from packaging.specifiers import SpecifierSet
from packaging.version import Version


class GithubDependency:
    """_summary_."""

    def __init__(
        self,
        owner: str,
        repo: str,
        specifier: SpecifierSet,
        action: bool,
        pre_commit: bool,
    ) -> None:
        """_summary_.

        Args:
            owner: _description_
            repo: _description_
            specifier: _description_
            action: _description_
            pre_commit: _description_
        """
        self.owner = owner
        self.repo = repo
        self.specifier = specifier
        self.action = action
        self.pre_commit = pre_commit
        self.github_data: dict[str, Any] | None = None

    def get_latest_version(self) -> Version:
        """Gets the latest version of the dependency from GitHub.

        Returns:
            Latest dependency version
        """
        return Version(version=self.get_github_data().get("tag_name", ""))

    def needs_update(self) -> bool:
        """_summary_.

        Returns:
            _description_
        """
        # the below returns False is the latest version doesn't match the specifier,
        # otherwise it returns the latest version
        is_latest_ok = next(self.specifier.filter([self.get_latest_version()]), False)

        return not is_latest_ok

    def get_github_data(self) -> dict[str, Any]:
        """_summary_.

        Returns:
            _description_
        """
        if self.github_data is None:
            msg = "Call Dependency.save_pypi_data() first!"
            raise RuntimeError(msg)

        return self.github_data

    def save_github_data(self) -> None:
        """_summary_."""
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases/latest"
        self.github_data = httpx.get(url=url).json()

    def __repr__(self) -> str:
        """_summary_.

        Returns:
            _description_
        """
        loc = "(gha)" if self.action else "(pre-commit)"

        return f"{self.owner}/{self.repo}: {self.specifier} {loc}"
