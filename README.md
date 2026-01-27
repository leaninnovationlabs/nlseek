# nl2query

A natural language to SQL query converter.

## Installation

```bash
# Using uv
uv pip install nl2query

# Or install from source
uv pip install -e .
```

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/nl2query.git
cd nl2query

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src tests
ruff format src tests

# Type checking
mypy src
```

## Usage

### Load domain from file

```python
from nl2query import DomainLoader, QueryResolver

# Load a domain schema from YAML files
loader = DomainLoader("/path/to/domains")
domain = loader.get_domain("ecommerce")

# Create a query resolver
resolver = QueryResolver(domain)

# Convert natural language to SQL
result = resolver.resolve("Show me all orders from last week")
print(result.query)        # The generated SQL query
print(result.explanation)  # Explanation of the query
print(result.tables_used)  # Tables referenced
```

### Load domain from JSON string

```python
from nl2query import DomainLoader, QueryResolver

# Create a loader without a file path
loader = DomainLoader()

# Register a domain from a JSON string
loader.register_domain('''
{
    "name": "mydb",
    "database_type": "postgres",
    "tables": [
        {
            "name": "users",
            "columns": [
                {"name": "id", "type": "integer", "primary_key": true},
                {"name": "email", "type": "varchar(255)"}
            ]
        }
    ]
}
''')

# Use the registered domain
domain = loader.get_domain("mydb")
resolver = QueryResolver(domain)
result = resolver.resolve("List all users")
```

### Generate domain from Pydantic models

```python
from pydantic import BaseModel, Field
from nl2query import DomainLoader, QueryResolver

# Define your models (works with Pydantic, SQLModel, etc.)
class User(BaseModel):
    """User account information."""
    id: int
    email: str
    name: str | None = None

class Order(BaseModel):
    """Customer order."""
    id: int
    user_id: int  # Auto-detected as FK to users.id
    total: float = Field(description="Order total in USD")

# Generate domain from models
loader = DomainLoader()
loader.register_from_models(
    name="mydb",
    models=[User, Order],
    database_type="postgres",
)

# Use the generated domain
domain = loader.get_domain("mydb")
resolver = QueryResolver(domain)
result = resolver.resolve("Show orders for user with email john@example.com")
```

The generator automatically:
- Converts class names to table names (`User` -> `users`, `OrderItem` -> `order_items`)
- Maps Python types to SQL types (`int` -> `integer`, `str` -> `varchar(255)`, etc.)
- Detects primary keys (fields named `id`)
- Infers relationships from foreign key columns (`user_id` -> `users.id`)
- Extracts descriptions from docstrings and `Field(description=...)`

## Environment Setup

Create a `.env` file with your Anthropic API key:

```
ANTHROPIC_API_KEY=your-api-key-here
```

## License

MIT
