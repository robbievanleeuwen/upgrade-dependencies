"""Class for a python project github dependency."""

from datetime import UTC, datetime
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

    def save_github_data(
        self,
        gh_pat: str | None = None,
    ) -> None:
        """_summary_.

        Args:
            gh_pat: _description_
        """
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases/latest"

        if gh_pat is None:
            response = httpx.get(url=url)
        else:
            headers = {"Authorization": f"Bearer {gh_pat}"}
            response = httpx.get(url=url, headers=headers)

        self.handle_response(response=response)

    async def save_github_data_async(
        self,
        gh_pat: str | None = None,
    ) -> None:
        """_summary_.

        Args:
            gh_pat: _description_
        """
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases/latest"

        async with httpx.AsyncClient() as client:
            if gh_pat is None:
                response = await client.get(url=url)
            else:
                headers = {"Authorization": f"Bearer {gh_pat}"}
                response = await client.get(url=url, headers=headers)

            self.handle_response(response=response)

    def handle_response(
        self,
        response: httpx.Response,
    ) -> None:
        """_summary_.

        Args:
            response: _description_
        """
        if response.status_code == 200:
            self.github_data = response.json()
        elif response.status_code in [401, 403, 404, 429]:
            reset_time = datetime.fromtimestamp(
                int(response.headers.get("x-ratelimit-reset")),
                UTC,
            )
            msg = f"{response.status_code} - {response.reason_phrase}."

            if response.reason_phrase == "rate limit exceeded":
                msg += f" Rate limit reset at {reset_time}."
            raise RuntimeError(msg)
        else:
            msg = "Github API Error."
            raise RuntimeError(msg)

    @property
    def package_name(self) -> str:
        """_summary_.

        Returns:
            _description_
        """
        return f"{self.owner}/{self.repo}"

    def __repr__(self) -> str:
        """_summary_.

        Returns:
            _description_
        """
        loc = "(gha)" if self.action else "(pre-commit)"

        return f"{self.package_name}: {self.specifier} {loc}"
