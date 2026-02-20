"""Tests for the query resolver module."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nlseek.domain import DomainLoader
from nlseek.resolver import QueryResolver, SQLQueryResult
from nlseek.resolver.query_resolver import _build_system_prompt, _get_database_hints


@pytest.fixture
def sample_domain() -> dict[str, Any]:
    """Return a minimal sample domain for testing."""
    return {
        "name": "test_db",
        "description": "Test database",
        "version": "1.0",
        "tables": [
            {
                "name": "users",
                "description": "User accounts",
                "columns": [
                    {
                        "name": "id",
                        "type": "integer",
                        "primary_key": True,
                        "nullable": False,
                        "description": "User ID",
                    },
                    {
                        "name": "email",
                        "type": "varchar(255)",
                        "primary_key": False,
                        "nullable": False,
                        "description": "User email",
                    },
                ],
            },
            {
                "name": "posts",
                "description": "User posts",
                "columns": [
                    {
                        "name": "id",
                        "type": "integer",
                        "primary_key": True,
                        "nullable": False,
                        "description": "Post ID",
                    },
                    {
                        "name": "user_id",
                        "type": "integer",
                        "primary_key": False,
                        "nullable": False,
                        "description": "Author user ID",
                    },
                    {
                        "name": "title",
                        "type": "varchar(255)",
                        "primary_key": False,
                        "nullable": False,
                        "description": "Post title",
                    },
                ],
            },
        ],
        "relationships": [
            {
                "name": "user_posts",
                "from_table": "posts",
                "from_column": "user_id",
                "to_table": "users",
                "to_column": "id",
                "type": "many_to_one",
            }
        ],
        "sample_sql": [
            {
                "description": "Get all posts by a user",
                "sql": "SELECT * FROM posts WHERE user_id = ?",
            }
        ],
        "custom_instructions": [
            "Use email for user lookups when possible",
        ],
    }


@pytest.fixture
def ecommerce_domain() -> dict[str, Any]:
    """Load the ecommerce domain from examples."""
    domains_path = Path(__file__).parent.parent / "examples" / "domains"
    loader = DomainLoader(domains_path)
    return loader.get_domain("ecommerce")


class TestSQLQueryResult:
    """Tests for SQLQueryResult model."""

    def test_sql_query_result_creation(self) -> None:
        """Test creating an SQLQueryResult instance."""
        result = SQLQueryResult(
            query="SELECT * FROM users",
            explanation="Retrieves all users",
            tables_used=["users"],
        )
        print(result)
        assert result.query == "SELECT * FROM users"
        assert result.explanation == "Retrieves all users"
        assert result.tables_used == ["users"]

    def test_sql_query_result_default_tables(self) -> None:
        """Test SQLQueryResult with default empty tables list."""
        result = SQLQueryResult(
            query="SELECT 1",
            explanation="Test query",
        )
        assert result.tables_used == []


class TestBuildSystemPrompt:
    """Tests for system prompt building."""

    def test_prompt_contains_database_name(self, sample_domain: dict[str, Any]) -> None:
        """Test that prompt contains database name."""
        prompt = _build_system_prompt(sample_domain)
        assert "test_db" in prompt

    def test_prompt_contains_tables(self, sample_domain: dict[str, Any]) -> None:
        """Test that prompt contains table information."""
        prompt = _build_system_prompt(sample_domain)
        assert "users" in prompt
        assert "posts" in prompt

    def test_prompt_contains_columns(self, sample_domain: dict[str, Any]) -> None:
        """Test that prompt contains column information."""
        prompt = _build_system_prompt(sample_domain)
        assert "email" in prompt
        assert "varchar(255)" in prompt

    def test_prompt_contains_relationships(self, sample_domain: dict[str, Any]) -> None:
        """Test that prompt contains relationship information."""
        prompt = _build_system_prompt(sample_domain)
        assert "posts.user_id" in prompt
        assert "users.id" in prompt
        assert "many to one" in prompt

    def test_prompt_contains_sample_sql(self, sample_domain: dict[str, Any]) -> None:
        """Test that prompt contains sample SQL."""
        prompt = _build_system_prompt(sample_domain)
        assert "SELECT * FROM posts WHERE user_id = ?" in prompt

    def test_prompt_contains_custom_instructions(self, sample_domain: dict[str, Any]) -> None:
        """Test that prompt contains custom instructions."""
        prompt = _build_system_prompt(sample_domain)
        assert "Use email for user lookups" in prompt

    def test_prompt_with_ecommerce_domain(self, ecommerce_domain: dict[str, Any]) -> None:
        """Test prompt building with full ecommerce domain."""
        prompt = _build_system_prompt(ecommerce_domain)

        # Check key tables
        assert "customers" in prompt
        assert "orders" in prompt
        assert "products" in prompt

        # Check relationships
        assert "customer_id" in prompt

        # Check custom instructions
        assert "email" in prompt.lower()


class TestDatabaseTypeInPrompt:
    """Tests for database type handling in system prompt."""

    def test_prompt_includes_database_type(self, sample_domain: dict[str, Any]) -> None:
        """Test that prompt includes database type section."""
        sample_domain["database_type"] = "postgres"
        prompt = _build_system_prompt(sample_domain)
        assert "Target Database: POSTGRES" in prompt

    def test_prompt_default_database_type(self, sample_domain: dict[str, Any]) -> None:
        """Test that prompt defaults to ANSI when database_type not specified."""
        # sample_domain doesn't have database_type, should default to ansi
        prompt = _build_system_prompt(sample_domain)
        assert "Target Database: ANSI" in prompt

    def test_prompt_mysql_hints(self, sample_domain: dict[str, Any]) -> None:
        """Test that MySQL-specific hints are included."""
        sample_domain["database_type"] = "mysql"
        prompt = _build_system_prompt(sample_domain)
        assert "CONCAT()" in prompt
        assert "LIMIT" in prompt

    def test_prompt_postgres_hints(self, sample_domain: dict[str, Any]) -> None:
        """Test that PostgreSQL-specific hints are included."""
        sample_domain["database_type"] = "postgres"
        prompt = _build_system_prompt(sample_domain)
        assert "INTERVAL" in prompt
        assert "::" in prompt  # Type casting hint

    def test_prompt_oracle_hints(self, sample_domain: dict[str, Any]) -> None:
        """Test that Oracle-specific hints are included."""
        sample_domain["database_type"] = "oracle"
        prompt = _build_system_prompt(sample_domain)
        assert "FETCH FIRST" in prompt or "ROWNUM" in prompt
        assert "SYSDATE" in prompt

    def test_prompt_ansi_hints(self, sample_domain: dict[str, Any]) -> None:
        """Test that ANSI SQL hints are included."""
        sample_domain["database_type"] = "ansi"
        prompt = _build_system_prompt(sample_domain)
        assert "ANSI SQL standard" in prompt

    def test_get_database_hints_returns_list(self) -> None:
        """Test that _get_database_hints returns a list of hints."""
        for db_type in ["ansi", "mysql", "postgres", "oracle"]:
            hints = _get_database_hints(db_type)
            assert isinstance(hints, list)
            assert len(hints) > 0

    def test_get_database_hints_unknown_type(self) -> None:
        """Test that unknown database type falls back to ANSI hints."""
        hints = _get_database_hints("unknown")
        ansi_hints = _get_database_hints("ansi")
        assert hints == ansi_hints

    def test_ecommerce_domain_has_postgres_hints(self, ecommerce_domain: dict[str, Any]) -> None:
        """Test that ecommerce domain prompt includes PostgreSQL hints."""
        prompt = _build_system_prompt(ecommerce_domain)
        assert "Target Database: POSTGRES" in prompt
        assert "INTERVAL" in prompt


class TestQueryResolver:
    """Tests for QueryResolver class."""

    @patch("nlseek.resolver.query_resolver.Agent")
    def test_resolver_initialization(self, mock_agent_class: MagicMock, sample_domain: dict[str, Any]) -> None:
        """Test QueryResolver initialization."""
        resolver = QueryResolver(sample_domain)
        assert resolver.domain == sample_domain
        assert "test_db" in resolver.system_prompt

    @patch("nlseek.resolver.query_resolver.Agent")
    def test_resolver_custom_model(self, mock_agent_class: MagicMock, sample_domain: dict[str, Any]) -> None:
        """Test QueryResolver with custom model."""
        resolver = QueryResolver(sample_domain, model="anthropic:claude-sonnet-4-20250514")
        assert resolver._model == "anthropic:claude-sonnet-4-20250514"

    @patch("nlseek.resolver.query_resolver.Agent")
    def test_resolve_sync(self, mock_agent_class: MagicMock, sample_domain: dict[str, Any]) -> None:
        """Test synchronous query resolution."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.data = SQLQueryResult(
            query="SELECT * FROM users WHERE email = 'test@example.com'",
            explanation="Finds user by email",
            tables_used=["users"],
        )
        mock_agent = MagicMock()
        mock_agent.run_sync.return_value = mock_result
        mock_agent_class.return_value = mock_agent

        # Test
        resolver = QueryResolver(sample_domain)
        result = resolver.resolve("Find user with email test@example.com")

        # Verify
        assert result.query == "SELECT * FROM users WHERE email = 'test@example.com'"
        assert result.tables_used == ["users"]
        mock_agent.run_sync.assert_called_once_with("Find user with email test@example.com")

    @patch("nlseek.resolver.query_resolver.Agent")
    @pytest.mark.asyncio
    async def test_resolve_async(self, mock_agent_class: MagicMock, sample_domain: dict[str, Any]) -> None:
        """Test asynchronous query resolution."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.data = SQLQueryResult(
            query="SELECT p.* FROM posts p JOIN users u ON p.user_id = u.id",
            explanation="Gets all posts with user info",
            tables_used=["posts", "users"],
        )
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent

        # Test
        resolver = QueryResolver(sample_domain)
        result = await resolver.resolve_async("Get all posts with author info")

        # Verify
        assert "posts" in result.query
        assert "users" in result.tables_used
        mock_agent.run.assert_called_once_with("Get all posts with author info")


class TestQueryResolverWithEcommerceDomain:
    """Tests using the ecommerce domain."""

    @patch("nlseek.resolver.query_resolver.Agent")
    def test_resolver_with_ecommerce_domain(
        self, mock_agent_class: MagicMock, ecommerce_domain: dict[str, Any]
    ) -> None:
        """Test resolver initialization with ecommerce domain."""
        resolver = QueryResolver(ecommerce_domain)

        # Verify system prompt contains ecommerce schema
        assert "ecommerce" in resolver.system_prompt
        assert "customers" in resolver.system_prompt
        assert "orders" in resolver.system_prompt

    @patch("nlseek.resolver.query_resolver.Agent")
    def test_ecommerce_query(self, mock_agent_class: MagicMock, ecommerce_domain: dict[str, Any]) -> None:
        """Test query resolution with ecommerce domain."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.data = SQLQueryResult(
            query="""
                SELECT o.* FROM orders o
                JOIN customers c ON o.customer_id = c.id
                WHERE c.email = 'customer@example.com'
            """,
            explanation="Gets all orders for a customer by email",
            tables_used=["orders", "customers"],
        )
        mock_agent = MagicMock()
        mock_agent.run_sync.return_value = mock_result
        mock_agent_class.return_value = mock_agent

        # Test
        resolver = QueryResolver(ecommerce_domain)
        result = resolver.resolve("Show orders for customer@example.com")

        # Verify
        assert "orders" in result.query
        assert "customers" in result.tables_used
