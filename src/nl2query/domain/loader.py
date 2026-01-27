"""Domain loader for reading and managing domain schema files."""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from nl2query.domain.models import DatabaseType, Domain

if TYPE_CHECKING:
    from pydantic import BaseModel


class DomainNotFoundError(Exception):
    """Raised when a requested domain is not found."""

    pass


class TableNotFoundError(Exception):
    """Raised when a requested table is not found in a domain."""

    pass


class DomainLoader:
    """Loads and manages domain schema definitions from YAML files or JSON strings.

    Args:
        domains_path: Optional path to the directory containing domain YAML files.
            If not provided, only domains registered via register_domain methods
            will be available.

    Example:
        >>> # File-based loading
        >>> loader = DomainLoader("/path/to/domains")
        >>> loader.list_domains()
        ['ecommerce', 'inventory']
        >>> domain = loader.get_domain("ecommerce")
        >>> table = loader.get_table("ecommerce", "customers")

        >>> # JSON string loading
        >>> loader = DomainLoader()
        >>> loader.register_domain('{"name": "mydb", "tables": []}')
        'mydb'
        >>> domain = loader.get_domain("mydb")
    """

    def __init__(self, domains_path: str | Path | None = None) -> None:
        self._domains_path: Path | None = Path(domains_path) if domains_path else None
        self._cache: dict[str, Domain] = {}

    @property
    def domains_path(self) -> Path | None:
        """Return the path to the domains directory, or None if not set."""
        return self._domains_path

    def list_domains(self) -> list[str]:
        """Get a list of available domain names.

        Returns:
            List of domain names (from both files and registered domains).

        Raises:
            FileNotFoundError: If domains_path is set but the directory does not exist.
        """
        domain_names: set[str] = set(self._cache.keys())

        if self._domains_path is not None:
            if not self._domains_path.exists():
                raise FileNotFoundError(f"Domains directory not found: {self._domains_path}")

            file_domains = {f.stem for f in self._domains_path.glob("*.yaml") if f.is_file()}
            domain_names.update(file_domains)

        return sorted(domain_names)

    def get_domain(self, name: str) -> dict[str, Any]:
        """Get a domain schema as a JSON-serializable dictionary.

        Args:
            name: The domain name (without .yaml extension).

        Returns:
            Dictionary representation of the domain schema.

        Raises:
            DomainNotFoundError: If the domain file does not exist.
        """
        domain = self._load_domain(name)
        return domain.model_dump()

    def get_table(self, domain_name: str, table_name: str) -> dict[str, Any]:
        """Get metadata for a specific table in a domain.

        Args:
            domain_name: The domain name (without .yaml extension).
            table_name: The name of the table to retrieve.

        Returns:
            Dictionary representation of the table metadata.

        Raises:
            DomainNotFoundError: If the domain file does not exist.
            TableNotFoundError: If the table is not found in the domain.
        """
        domain = self._load_domain(domain_name)

        for table in domain.tables:
            if table.name == table_name:
                return table.model_dump()

        raise TableNotFoundError(f"Table '{table_name}' not found in domain '{domain_name}'")

    def _load_domain(self, name: str) -> Domain:
        """Load and cache a domain from its YAML file or return from cache.

        Args:
            name: The domain name (without .yaml extension).

        Returns:
            The parsed Domain object.

        Raises:
            DomainNotFoundError: If the domain is not found in cache or file system.
        """
        if name in self._cache:
            return self._cache[name]

        if self._domains_path is None:
            raise DomainNotFoundError(f"Domain '{name}' not found (no domains path configured)")

        domain_file = self._domains_path / f"{name}.yaml"

        if not domain_file.exists():
            raise DomainNotFoundError(f"Domain file not found: {domain_file}")

        with open(domain_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        domain = Domain.model_validate(data)
        self._cache[name] = domain

        return domain

    def clear_cache(self) -> None:
        """Clear the domain cache to force reloading from disk."""
        self._cache.clear()

    def register_domain_from_dict(self, data: dict[str, Any]) -> str:
        """Register a domain from a dictionary.

        Args:
            data: Dictionary containing domain schema data.

        Returns:
            The domain name extracted from the data.

        Raises:
            ValueError: If the data is invalid or missing required fields.
        """
        domain = Domain.model_validate(data)
        self._cache[domain.name] = domain
        return domain.name

    def register_domain(self, json_string: str) -> str:
        """Register a domain from a JSON string.

        Args:
            json_string: JSON string containing domain schema data.

        Returns:
            The domain name extracted from the JSON.

        Raises:
            json.JSONDecodeError: If the string is not valid JSON.
            ValueError: If the data is invalid or missing required fields.
        """
        data = json.loads(json_string)
        return self.register_domain_from_dict(data)

    def register_from_models(
        self,
        name: str,
        models: list[type["BaseModel"]],
        database_type: DatabaseType = "ansi",
        description: str | None = None,
    ) -> str:
        """Register a domain generated from Pydantic model classes.

        Args:
            name: Name for the generated domain.
            models: List of Pydantic model classes to include.
            database_type: Target database type (ansi, mysql, postgres, oracle).
            description: Optional description for the domain.

        Returns:
            The domain name.

        Example:
            >>> from pydantic import BaseModel
            >>> class User(BaseModel):
            ...     id: int
            ...     email: str
            >>> loader = DomainLoader()
            >>> loader.register_from_models("mydb", [User])
            'mydb'
        """
        from nl2query.domain.generator import generate_domain

        domain = generate_domain(
            name=name,
            models=models,
            database_type=database_type,
            description=description,
        )
        self._cache[domain.name] = domain
        return domain.name
