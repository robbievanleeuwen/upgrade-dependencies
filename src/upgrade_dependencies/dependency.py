"""Class for a python project dependency."""

from typing import Any

import httpx
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version


class Dependency:
    """_summary_."""

    pypi_data: dict[str, Any]

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
        self.pypi_data = self.get_pypi_data()

    def get_pypi_data(self) -> dict[str, Any]:
        """_summary_.

        Returns:
            _description_
        """
        # TODO: error handling
        # TODO: async
        url = "/".join(["https://pypi.org", "pypi", self.package_name, "json"])
        return httpx.get(url=url).json()

    def get_latest_version(self) -> Version:
        """Gets the latest version of the dependency from PyPI.

        Returns:
            Latest dependency version
        """
        return Version(version=self.pypi_data["info"]["version"])

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