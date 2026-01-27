"""nl2query - A natural language to SQL query converter."""

from nl2query.domain import DomainLoader, generate_domain
from nl2query.resolver import QueryResolver, SQLQueryResult

__version__ = "0.1.0"

__all__ = [
    "DomainLoader",
    "QueryResolver",
    "SQLQueryResult",
    "__version__",
    "generate_domain",
]
