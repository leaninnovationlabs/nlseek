"""Query resolver for converting natural language questions to SQL queries."""

from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent

# Load environment variables from .env file
load_dotenv()


class SQLQueryResult(BaseModel):
    """Result of a natural language to SQL query conversion."""

    query: str = Field(..., description="The generated SQL query")
    explanation: str = Field(..., description="Brief explanation of what the query does")
    tables_used: list[str] = Field(default_factory=list, description="Tables referenced in the query")


def _get_database_hints(database_type: str) -> list[str]:
    """Get database-specific SQL syntax hints.

    Args:
        database_type: The target database type.

    Returns:
        List of syntax hints for the specific database.
    """
    hints: dict[str, list[str]] = {
        "ansi": [
            "Use ANSI SQL standard syntax",
            "Use standard string concatenation with || operator",
            "Use COALESCE for null handling",
            "Use standard CASE expressions",
        ],
        "mysql": [
            "Use MySQL-specific syntax",
            "Use CONCAT() for string concatenation",
            "Use IFNULL() or COALESCE() for null handling",
            "Use LIMIT for row limiting (e.g., LIMIT 10)",
            "Use backticks (`) for identifier quoting if needed",
            "Use NOW() for current timestamp",
            "Use DATE_SUB() and DATE_ADD() for date arithmetic",
        ],
        "postgres": [
            "Use PostgreSQL-specific syntax",
            "Use || for string concatenation",
            "Use COALESCE() for null handling",
            "Use LIMIT and OFFSET for pagination",
            'Use double quotes (") for identifier quoting if needed',
            "Use NOW() or CURRENT_TIMESTAMP for current timestamp",
            "Use INTERVAL for date arithmetic (e.g., NOW() - INTERVAL '7 days')",
            "Use :: for type casting (e.g., value::text)",
        ],
        "oracle": [
            "Use Oracle-specific syntax",
            "Use || for string concatenation",
            "Use NVL() or COALESCE() for null handling",
            "Use FETCH FIRST n ROWS ONLY for row limiting (Oracle 12c+)",
            "Or use ROWNUM in WHERE clause for older Oracle versions",
            'Use double quotes (") for identifier quoting if needed',
            "Use SYSDATE for current date, SYSTIMESTAMP for current timestamp",
            "Use ADD_MONTHS() and date arithmetic with numbers for date operations",
        ],
    }
    return hints.get(database_type, hints["ansi"])


def _build_system_prompt(domain: dict[str, Any]) -> str:
    """Build a system prompt from a domain model.

    Args:
        domain: The domain model dictionary containing tables, relationships,
                sample SQL, and custom instructions.

    Returns:
        A formatted system prompt string for the AI agent.
    """
    database_type = domain.get("database_type", "ansi")

    parts = [
        "You are an expert SQL query generator. Your task is to convert natural language "
        "questions into accurate SQL queries based on the provided database schema.",
        "",
        f"# Database: {domain.get('name', 'Unknown')}",
    ]

    if domain.get("description"):
        parts.append(f"Description: {domain['description']}")

    # Add database type information
    parts.append("")
    parts.append(f"## Target Database: {database_type.upper()}")
    parts.append("")
    parts.append("Database-specific syntax requirements:")
    for hint in _get_database_hints(database_type):
        parts.append(f"- {hint}")

    # Add table schemas
    parts.append("")
    parts.append("## Tables")
    parts.append("")

    for table in domain.get("tables", []):
        parts.append(f"### {table['name']}")
        if table.get("description"):
            parts.append(f"{table['description']}")
        parts.append("")
        parts.append("Columns:")

        for column in table.get("columns", []):
            col_parts = [f"  - {column['name']} ({column['type']})"]

            attrs = []
            if column.get("primary_key"):
                attrs.append("PRIMARY KEY")
            if column.get("nullable") is False:
                attrs.append("NOT NULL")

            if attrs:
                col_parts.append(f" [{', '.join(attrs)}]")

            if column.get("description"):
                col_parts.append(f" - {column['description']}")

            parts.append("".join(col_parts))

        parts.append("")

    # Add relationships
    if domain.get("relationships"):
        parts.append("## Relationships")
        parts.append("")

        for rel in domain["relationships"]:
            rel_type = rel.get("type", "unknown").replace("_", " ")
            parts.append(
                f"- {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']} ({rel_type})"
            )

        parts.append("")

    # Add sample SQL as few-shot examples
    if domain.get("sample_sql"):
        parts.append("## Example Queries")
        parts.append("")
        parts.append("Here are some example queries for reference:")
        parts.append("")

        for i, sample in enumerate(domain["sample_sql"], 1):
            parts.append(f"### Example {i}: {sample['description']}")
            parts.append("```sql")
            parts.append(sample["sql"].strip())
            parts.append("```")
            parts.append("")

    # Add custom instructions
    if domain.get("custom_instructions"):
        parts.append("## Important Instructions")
        parts.append("")

        for instruction in domain["custom_instructions"]:
            parts.append(f"- {instruction}")

        parts.append("")

    # Add output guidelines
    parts.extend(
        [
            "## Output Guidelines",
            "",
            "When generating SQL queries:",
            "- Use proper JOIN syntax when relating tables",
            "- Include appropriate WHERE clauses based on the question",
            "- Use table aliases for readability when joining multiple tables",
            "- Return only valid SQL that can be executed",
            "- List all tables that are used in the query",
        ]
    )

    return "\n".join(parts)


class QueryResolver:
    """Resolves natural language questions to SQL queries using AI.

    Args:
        domain: The domain model dictionary containing schema information.
        model: The AI model to use. Defaults to Claude Opus 4.5.

    Example:
        >>> from nl2query.domain import DomainLoader
        >>> loader = DomainLoader("/path/to/domains")
        >>> domain = loader.get_domain("ecommerce")
        >>> resolver = QueryResolver(domain)
        >>> result = resolver.resolve("Show me all orders from last week")
        >>> print(result.query)
    """

    def __init__(
        self,
        domain: dict[str, Any],
        model: str = "anthropic:claude-opus-4-20250514",
    ) -> None:
        self._domain = domain
        self._model = model
        self._system_prompt = _build_system_prompt(domain)
        self._agent = Agent(
            model,
            system_prompt=self._system_prompt,
            output_type=SQLQueryResult,
        )

    @property
    def domain(self) -> dict[str, Any]:
        """Return the domain model."""
        return self._domain

    @property
    def system_prompt(self) -> str:
        """Return the generated system prompt."""
        return self._system_prompt

    def resolve(self, question: str) -> SQLQueryResult:
        """Convert a natural language question to a SQL query.

        Args:
            question: The natural language question to convert.

        Returns:
            SQLQueryResult containing the generated query, explanation, and tables used.
        """
        result = self._agent.run_sync(question)
        return result.output

    async def resolve_async(self, question: str) -> SQLQueryResult:
        """Asynchronously convert a natural language question to a SQL query.

        Args:
            question: The natural language question to convert.

        Returns:
            SQLQueryResult containing the generated query, explanation, and tables used.
        """
        result = await self._agent.run(question)
        return result.output
