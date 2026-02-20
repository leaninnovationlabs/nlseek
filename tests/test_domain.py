"""Tests for the domain loader module."""

import json
from pathlib import Path

import pytest

from nlseek.domain import DomainLoader
from nlseek.domain.loader import DomainNotFoundError, TableNotFoundError


@pytest.fixture
def domains_path() -> Path:
    """Return path to the example domains directory."""
    return Path(__file__).parent.parent / "examples" / "domains"


@pytest.fixture
def loader(domains_path: Path) -> DomainLoader:
    """Create a DomainLoader instance with example domains."""
    return DomainLoader(domains_path)


class TestDomainLoader:
    """Tests for DomainLoader class."""

    def test_list_domains(self, loader: DomainLoader) -> None:
        """Test listing available domains."""
        domains = loader.list_domains()
        assert isinstance(domains, list)
        assert "ecommerce" in domains

    def test_list_domains_nonexistent_path(self, tmp_path: Path) -> None:
        """Test that listing domains from nonexistent path raises error."""
        loader = DomainLoader(tmp_path / "nonexistent")
        with pytest.raises(FileNotFoundError):
            loader.list_domains()

    def test_get_domain(self, loader: DomainLoader) -> None:
        """Test getting a domain as dictionary."""
        domain = loader.get_domain("ecommerce")

        assert isinstance(domain, dict)
        assert domain["name"] == "ecommerce"
        assert "tables" in domain
        assert "relationships" in domain
        assert "sample_sql" in domain
        assert "custom_instructions" in domain

    def test_get_domain_tables(self, loader: DomainLoader) -> None:
        """Test that domain contains expected tables."""
        domain = loader.get_domain("ecommerce")
        table_names = [t["name"] for t in domain["tables"]]

        assert "customers" in table_names
        assert "products" in table_names
        assert "orders" in table_names
        assert "order_items" in table_names

    def test_get_domain_not_found(self, loader: DomainLoader) -> None:
        """Test that getting nonexistent domain raises error."""
        with pytest.raises(DomainNotFoundError):
            loader.get_domain("nonexistent")

    def test_get_table(self, loader: DomainLoader) -> None:
        """Test getting a specific table from a domain."""
        table = loader.get_table("ecommerce", "customers")

        assert isinstance(table, dict)
        assert table["name"] == "customers"
        assert "columns" in table
        assert len(table["columns"]) > 0

    def test_get_table_columns(self, loader: DomainLoader) -> None:
        """Test that table contains expected columns."""
        table = loader.get_table("ecommerce", "customers")
        column_names = [c["name"] for c in table["columns"]]

        assert "id" in column_names
        assert "email" in column_names

    def test_get_table_column_properties(self, loader: DomainLoader) -> None:
        """Test that columns have expected properties."""
        table = loader.get_table("ecommerce", "customers")
        id_column = next(c for c in table["columns"] if c["name"] == "id")

        assert id_column["type"] == "integer"
        assert id_column["primary_key"] is True

    def test_get_table_not_found(self, loader: DomainLoader) -> None:
        """Test that getting nonexistent table raises error."""
        with pytest.raises(TableNotFoundError):
            loader.get_table("ecommerce", "nonexistent_table")

    def test_get_table_domain_not_found(self, loader: DomainLoader) -> None:
        """Test that getting table from nonexistent domain raises error."""
        with pytest.raises(DomainNotFoundError):
            loader.get_table("nonexistent", "customers")

    def test_domain_caching(self, loader: DomainLoader) -> None:
        """Test that domains are cached after first load."""
        # Load domain twice
        domain1 = loader.get_domain("ecommerce")
        domain2 = loader.get_domain("ecommerce")

        # Should return equivalent dictionaries
        assert domain1 == domain2

    def test_clear_cache(self, loader: DomainLoader) -> None:
        """Test clearing the domain cache."""
        loader.get_domain("ecommerce")
        assert len(loader._cache) > 0

        loader.clear_cache()
        assert len(loader._cache) == 0

    def test_domains_path_property(self, loader: DomainLoader, domains_path: Path) -> None:
        """Test that domains_path property returns correct path."""
        assert loader.domains_path == domains_path


class TestDomainRelationships:
    """Tests for domain relationships."""

    def test_relationships_exist(self, loader: DomainLoader) -> None:
        """Test that domain contains relationships."""
        domain = loader.get_domain("ecommerce")
        assert len(domain["relationships"]) > 0

    def test_relationship_structure(self, loader: DomainLoader) -> None:
        """Test relationship structure."""
        domain = loader.get_domain("ecommerce")
        relationship = domain["relationships"][0]

        assert "name" in relationship
        assert "from_table" in relationship
        assert "from_column" in relationship
        assert "to_table" in relationship
        assert "to_column" in relationship
        assert "type" in relationship


class TestDomainSampleSQL:
    """Tests for domain sample SQL."""

    def test_sample_sql_exists(self, loader: DomainLoader) -> None:
        """Test that domain contains sample SQL."""
        domain = loader.get_domain("ecommerce")
        assert len(domain["sample_sql"]) > 0

    def test_sample_sql_structure(self, loader: DomainLoader) -> None:
        """Test sample SQL structure."""
        domain = loader.get_domain("ecommerce")
        sample = domain["sample_sql"][0]

        assert "description" in sample
        assert "sql" in sample
        assert len(sample["sql"]) > 0


class TestDomainCustomInstructions:
    """Tests for domain custom instructions."""

    def test_custom_instructions_exist(self, loader: DomainLoader) -> None:
        """Test that domain contains custom instructions."""
        domain = loader.get_domain("ecommerce")
        assert len(domain["custom_instructions"]) > 0

    def test_custom_instructions_are_strings(self, loader: DomainLoader) -> None:
        """Test that custom instructions are strings."""
        domain = loader.get_domain("ecommerce")
        for instruction in domain["custom_instructions"]:
            assert isinstance(instruction, str)


class TestDomainDatabaseType:
    """Tests for domain database type."""

    def test_database_type_exists(self, loader: DomainLoader) -> None:
        """Test that domain contains database_type field."""
        domain = loader.get_domain("ecommerce")
        assert "database_type" in domain

    def test_database_type_value(self, loader: DomainLoader) -> None:
        """Test that database_type has expected value."""
        domain = loader.get_domain("ecommerce")
        assert domain["database_type"] == "postgres"

    def test_database_type_valid_values(self, loader: DomainLoader) -> None:
        """Test that database_type is one of the valid types."""
        domain = loader.get_domain("ecommerce")
        valid_types = ["ansi", "mysql", "postgres", "oracle"]
        assert domain["database_type"] in valid_types


class TestDomainLoaderJsonLoading:
    """Tests for JSON/dict domain loading functionality."""

    @pytest.fixture
    def sample_domain_dict(self) -> dict:
        """Return a sample domain as a dictionary."""
        return {
            "name": "testdb",
            "description": "Test database for unit tests",
            "version": "1.0",
            "database_type": "postgres",
            "tables": [
                {
                    "name": "users",
                    "description": "User accounts",
                    "columns": [
                        {"name": "id", "type": "integer", "primary_key": True},
                        {"name": "email", "type": "varchar(255)", "nullable": False},
                    ],
                }
            ],
            "relationships": [],
            "sample_sql": [],
            "custom_instructions": ["Test instruction"],
        }

    @pytest.fixture
    def sample_domain_json(self, sample_domain_dict: dict) -> str:
        """Return a sample domain as a JSON string."""
        return json.dumps(sample_domain_dict)

    def test_loader_without_path(self) -> None:
        """Test creating a DomainLoader without a domains path."""
        loader = DomainLoader()
        assert loader.domains_path is None
        assert loader.list_domains() == []

    def test_register_domain_from_dict(self, sample_domain_dict: dict) -> None:
        """Test registering a domain from a dictionary."""
        loader = DomainLoader()
        name = loader.register_domain_from_dict(sample_domain_dict)

        assert name == "testdb"
        assert "testdb" in loader.list_domains()

    def test_register_domain_from_json(self, sample_domain_json: str) -> None:
        """Test registering a domain from a JSON string."""
        loader = DomainLoader()
        name = loader.register_domain(sample_domain_json)

        assert name == "testdb"
        assert "testdb" in loader.list_domains()

    def test_get_registered_domain(self, sample_domain_json: str) -> None:
        """Test retrieving a registered domain."""
        loader = DomainLoader()
        loader.register_domain(sample_domain_json)
        domain = loader.get_domain("testdb")

        assert domain["name"] == "testdb"
        assert domain["description"] == "Test database for unit tests"
        assert len(domain["tables"]) == 1
        assert domain["tables"][0]["name"] == "users"

    def test_get_table_from_registered_domain(self, sample_domain_json: str) -> None:
        """Test retrieving a table from a registered domain."""
        loader = DomainLoader()
        loader.register_domain(sample_domain_json)
        table = loader.get_table("testdb", "users")

        assert table["name"] == "users"
        assert len(table["columns"]) == 2

    def test_mixed_file_and_registered_domains(self, domains_path: Path, sample_domain_json: str) -> None:
        """Test using both file-based and registered domains."""
        loader = DomainLoader(domains_path)
        loader.register_domain(sample_domain_json)

        domains = loader.list_domains()
        assert "ecommerce" in domains
        assert "testdb" in domains

    def test_register_domain_invalid_json(self) -> None:
        """Test that invalid JSON raises an error."""
        loader = DomainLoader()
        with pytest.raises(json.JSONDecodeError):
            loader.register_domain("not valid json")

    def test_register_domain_invalid_schema(self) -> None:
        """Test that invalid domain schema raises an error."""
        loader = DomainLoader()
        with pytest.raises(Exception):  # Pydantic ValidationError
            loader.register_domain('{"invalid": "schema"}')

    def test_domain_not_found_without_path(self) -> None:
        """Test that getting nonexistent domain without path raises error."""
        loader = DomainLoader()
        with pytest.raises(DomainNotFoundError) as exc_info:
            loader.get_domain("nonexistent")
        assert "no domains path configured" in str(exc_info.value)

    def test_clear_cache_removes_registered_domains(self, sample_domain_json: str) -> None:
        """Test that clearing cache removes registered domains."""
        loader = DomainLoader()
        loader.register_domain(sample_domain_json)
        assert "testdb" in loader.list_domains()

        loader.clear_cache()
        assert "testdb" not in loader.list_domains()

    def test_register_overwrites_existing(self, sample_domain_dict: dict) -> None:
        """Test that registering a domain with same name overwrites."""
        loader = DomainLoader()
        loader.register_domain_from_dict(sample_domain_dict)

        # Modify and re-register
        sample_domain_dict["description"] = "Updated description"
        loader.register_domain_from_dict(sample_domain_dict)

        domain = loader.get_domain("testdb")
        assert domain["description"] == "Updated description"
