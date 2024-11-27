"""Class for a python project dependency."""

from datetime import UTC, datetime
from typing import Any

import httpx
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version


class Dependency:
    """_summary_."""

    def __init__(
        self,
        package_name: str,
        specifier: SpecifierSet,
    ) -> None:
        """_summary_.

        Args:
            package_name: _description_
            specifier: _description_
        """
        self.package_name = package_name
        self.specifier = specifier
        self.data: dict[str, Any] | None = None

    def get_latest_version(self) -> Version:
        """Gets the latest version of the dependency from PyPI.

        Returns:
            Latest dependency version
        """
        raise NotImplementedError

    def is_specifier_latest(self) -> bool:
        """_summary_.

        Returns:
            _description_
        """
        latest = self.get_latest_version()

        for spec in sorted(self.specifier, key=str):
            if Version(spec.version) == latest:
                return True

        return False

    def needs_update(self) -> bool:
        """_summary_.

        Returns:
            _description_
        """
        # the below returns False is the latest version doesn't match the specifier,
        # otherwise it returns the latest version
        is_latest_ok = next(self.specifier.filter([self.get_latest_version()]), False)

        return not is_latest_ok

    def get_data(self) -> dict[str, Any]:
        """_summary_.

        Returns:
            _description_
        """
        if self.data is None:
            msg = "Call Dependency.save_data() first!"
            raise RuntimeError(msg)

        return self.data

    async def save_data(self) -> None:
        """_summary_."""
        raise NotImplementedError

    @property
    def loc(self) -> str:
        """_summary_.

        Returns:
            _description_
        """
        raise NotImplementedError

    @property
    def short_name(self) -> str:
        """_summary_.

        Returns:
            _description_
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        """_summary_.

        Returns:
            _description_
        """
        try:
            loc = self.loc
        except NotImplementedError:
            loc = ""

        return f"{self.package_name}{self.specifier}{loc}"


class PyPIDependency(Dependency):
    """Class for a dependency from the PyPI."""

    def __init__(
        self,
        package_name: str,
        specifier: SpecifierSet,
        extras: list[str],
        base: bool = True,
        extra: str | None = None,
        group: str | None = None,
    ) -> None:
        """_summary_.

        Args:
            package_name: _description_
            specifier: _description_
            extras: _description_
            base: _description_. Defaults to True.
            extra: _description_. Defaults to None.
            group: _description_. Defaults to None.
        """
        super().__init__(
            package_name=canonicalize_name(package_name),
            specifier=specifier,
        )
        self.extras = extras
        self.base = base
        self.extra = extra
        self.group = group

    def get_latest_version(self) -> Version:
        """Gets the latest version of the dependency from PyPI.

        Returns:
            Latest dependency version
        """
        return Version(version=self.get_data()["info"]["version"])

    async def save_data(self) -> None:
        """_summary_."""
        url = "/".join(["https://pypi.org", "pypi", self.package_name, "json"])

        async with httpx.AsyncClient() as client:
            response = await client.get(url=url)
            response.raise_for_status()  # raise an error if the request failed
            self.data = response.json()

    @property
    def loc(self) -> str:
        """_summary_.

        Returns:
            _description_
        """
        if self.base:
            return " (base)"
        elif self.extra is not None:
            return f" ({self.extra})"
        else:
            return f" ({self.group})"

    @property
    def short_name(self) -> str:
        """_summary_.

        Returns:
            _description_
        """
        return self.package_name

    @property
    def package_plus_extras(self) -> str:
        """_summary_.

        Returns:
            _description_
        """
        str_extras = f"[{",".join(self.extras)}]" if len(self.extras) > 0 else ""

        return f"{self.package_name}{str_extras}"


class GitHubDependency(Dependency):
    """_summary_."""

    def __init__(
        self,
        package_name: str,
        specifier: SpecifierSet,
        action: bool,
        pre_commit: bool,
        full_version: str | None = None,
        has_v: bool = True,
    ) -> None:
        """_summary_.

        Args:
            package_name: _description_
            specifier: _description_
            action: _description_
            pre_commit: _description_
            full_version: _description_
            has_v: _description_
        """
        super().__init__(package_name=package_name, specifier=specifier)

        # get owner & repo from package name
        owner, repo = package_name.split("/", maxsplit=1)
        # handle additional "/"" e.g. pandoc/actions/setup@v1
        if "/" in repo:
            repo = repo.split("/")[0]

        self.owner = owner
        self.repo = repo
        self.action = action
        self.pre_commit = pre_commit
        self.full_version = full_version
        self.has_v = has_v

    def get_latest_version(self) -> Version:
        """Gets the latest version of the dependency from GitHub.

        Returns:
            Latest dependency version
        """
        return Version(version=self.get_data().get("tag_name", ""))

    async def save_data(
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
            self.data = response.json()
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
    def loc(self) -> str:
        """_summary_.

        Returns:
            _description_
        """
        return " (gha)" if self.action else " (pre-commit)"

    @property
    def short_name(self) -> str:
        """_summary_.

        Returns:
            _description_
        """
        return self.repo
