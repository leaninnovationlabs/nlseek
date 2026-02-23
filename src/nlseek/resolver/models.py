"""Data models for query resolver results."""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class FilterCondition(BaseModel):
    """A single filter condition extracted from the generated SQL WHERE clause."""

    table: str = Field(..., description="The table name (e.g. 'products')")
    attribute: str = Field(..., description="The column name (e.g. 'name')")
    operator: str = Field(..., description="The SQL operator (e.g. 'LIKE', '=', '>', 'IN', 'BETWEEN', 'IS NULL')")
    value: str = Field(..., description="The filter value (e.g. 'iphone', 'electronics')")


class SQLQueryResult(BaseModel):
    """Result of a natural language to SQL query conversion."""

    query_id: UUID = Field(default_factory=uuid4, description="Unique identifier for this query result")
    query: str = Field(..., description="The generated SQL query")
    explanation: str = Field(..., description="Brief explanation of what the query does")
    tables_used: list[str] = Field(default_factory=list, description="Tables referenced in the query")
    entities: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Entities identified from the user's query mapped to the database columns "
            "they were matched against. Keys are the entity values (e.g. 'iphone'), "
            "values are lists of fully qualified column names (e.g. ['products.name', 'products.description'])."
        ),
    )
    filters: list[FilterCondition] = Field(
        default_factory=list,
        description="Filter conditions extracted from the WHERE clause of the generated SQL query.",
    )
