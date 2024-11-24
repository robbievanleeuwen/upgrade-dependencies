"""Class for a python project dependency."""

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
        base: bool = True,
        extra: str | None = None,
        group: str | None = None,
    ) -> None:
        """_summary_.

        Args:
            package_name: _description_
            specifier: _description_
            base: _description_
            extra: _description_
            group: _description_
        """
        self.package_name = canonicalize_name(name=package_name)
        self.specifier = specifier
        self.base = base
        self.extra = extra
        self.group = group
        self.pypi_data: dict[str, Any] | None = None

    def get_latest_version(self) -> Version:
        """Gets the latest version of the dependency from PyPI.

        Returns:
            Latest dependency version
        """
        return Version(version=self.get_pypi_data()["info"]["version"])

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

    def get_pypi_data(self) -> dict[str, Any]:
        """_summary_.

        Returns:
            _description_
        """
        if self.pypi_data is None:
            msg = "Call Dependency.save_pypi_data() first!"
            raise RuntimeError(msg)

        return self.pypi_data

    def save_pypi_data(self) -> None:
        """_summary_."""
        url = "/".join(["https://pypi.org", "pypi", self.package_name, "json"])
        self.pypi_data = httpx.get(url=url).json()

    async def save_pypi_data_async(self) -> None:
        """_summary_."""
        url = "/".join(["https://pypi.org", "pypi", self.package_name, "json"])

        async with httpx.AsyncClient() as client:
            response = await client.get(url=url)
            response.raise_for_status()  # raise an error if the request failed
            self.pypi_data = response.json()

    def __repr__(self) -> str:
        """_summary_.

        Returns:
            _description_
        """
        if self.base:
            loc = "(base)"
        elif self.extra is not None:
            loc = f"({self.extra})"
        else:
            loc = f"({self.group})"

        return f"{self.package_name}: {self.specifier} {loc}"
