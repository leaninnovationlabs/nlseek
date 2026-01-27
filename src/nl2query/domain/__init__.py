"""Domain module for loading and managing database schema definitions."""

from nl2query.domain.generator import generate_domain
from nl2query.domain.loader import DomainLoader
from nl2query.domain.models import (
    Column,
    DatabaseType,
    Domain,
    Relationship,
    SampleSQL,
    Table,
)

__all__ = [
    "Column",
    "DatabaseType",
    "Domain",
    "DomainLoader",
    "Relationship",
    "SampleSQL",
    "Table",
    "generate_domain",
]
