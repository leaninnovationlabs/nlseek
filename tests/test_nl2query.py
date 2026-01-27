"""Basic tests for nl2query package."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

import nl2query
from nl2query import DomainLoader, QueryResolver, SQLQueryResult

# Load environment variables from .env file
load_dotenv()


def test_version():
    """Test that version is defined."""
    print(nl2query.__version__)
    print('--------------------------------')
    assert nl2query.__version__ == "0.1.0"


@pytest.fixture
def ecommerce_domain() -> dict:
    """Load the example ecommerce domain."""
    domains_path = Path(__file__).parent.parent / "examples" / "domains"
    loader = DomainLoader(domains_path)
    return loader.get_domain("ecommerce")


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)

def test_simple_customer_query(ecommerce_domain: dict) -> None:
    """Test asking a simple question about customers."""
    resolver = QueryResolver(ecommerce_domain)
    print(resolver.system_prompt)
    print('--------------------------------')
    result = resolver.resolve("Show me all customers whose name start with 'John' and just get me minimal details")
    print(result)
    print('--------------------------------')

    assert isinstance(result, SQLQueryResult)
    assert result.query  # query should not be empty
    assert "customers" in result.query.lower()
    assert "customers" in result.tables_used
    assert result.explanation  # should have an explanation
