"""Pydantic models for domain schema definitions."""

from typing import Literal

from pydantic import BaseModel, Field

# Supported database types for SQL generation
DatabaseType = Literal["ansi", "mysql", "postgres", "oracle"]


class Column(BaseModel):
    """Represents a column in a database table."""

    name: str = Field(..., description="Column name")
    type: str = Field(..., description="Column data type (e.g., integer, varchar(255))")
    primary_key: bool = Field(default=False, description="Whether this column is a primary key")
    nullable: bool = Field(default=True, description="Whether this column allows NULL values")
    description: str | None = Field(default=None, description="Human-readable column description")


class Table(BaseModel):
    """Represents a database table with its columns."""

    name: str = Field(..., description="Table name")
    description: str | None = Field(default=None, description="Human-readable table description")
    columns: list[Column] = Field(default_factory=list, description="List of columns in the table")


class Relationship(BaseModel):
    """Represents a relationship between two tables."""

    name: str = Field(..., description="Relationship name")
    from_table: str = Field(..., description="Source table name")
    from_column: str = Field(..., description="Source column name")
    to_table: str = Field(..., description="Target table name")
    to_column: str = Field(..., description="Target column name")
    type: Literal["one_to_one", "one_to_many", "many_to_one", "many_to_many"] = Field(
        ..., description="Relationship type"
    )


class SampleSQL(BaseModel):
    """Represents a sample SQL query for the domain."""

    description: str = Field(..., description="Description of what the query does")
    sql: str = Field(..., description="The SQL query")


class Domain(BaseModel):
    """Represents a complete domain schema definition."""

    name: str = Field(..., description="Domain name")
    description: str | None = Field(default=None, description="Human-readable domain description")
    version: str = Field(default="1.0", description="Schema version")
    database_type: DatabaseType = Field(
        default="ansi",
        description="Target database type (ansi, mysql, postgres, oracle)",
    )
    tables: list[Table] = Field(default_factory=list, description="List of tables in the domain")
    relationships: list[Relationship] = Field(
        default_factory=list, description="List of relationships between tables"
    )
    sample_sql: list[SampleSQL] = Field(
        default_factory=list, description="Sample SQL queries for this domain"
    )
    custom_instructions: list[str] = Field(
        default_factory=list, description="Custom instructions for NL2SQL conversion"
    )
