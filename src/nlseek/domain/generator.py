"""Generate Domain schemas from Pydantic model classes."""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, get_args, get_origin
from uuid import UUID

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from nlseek.domain.models import Column, DatabaseType, Domain, Relationship, Table

# Mapping from Python types to SQL types
TYPE_MAPPING: dict[type, str] = {
    int: "integer",
    str: "varchar(255)",
    float: "decimal(10,2)",
    Decimal: "decimal(10,2)",
    bool: "boolean",
    datetime: "timestamp",
    date: "date",
    UUID: "uuid",
    bytes: "bytea",
}


def _camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case.

    Example:
        >>> _camel_to_snake("OrderItem")
        'order_item'
    """
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _get_table_name(model: type[BaseModel]) -> str:
    """Get table name from model class.

    Uses __tablename__ if defined, otherwise converts class name to snake_case
    and pluralizes.
    """
    if hasattr(model, "__tablename__"):
        return model.__tablename__  # type: ignore

    name = _camel_to_snake(model.__name__)
    # Simple pluralization
    if name.endswith("y"):
        return name[:-1] + "ies"
    elif name.endswith("s"):
        return name + "es"
    else:
        return name + "s"


def _get_sql_type(python_type: Any) -> str:
    """Convert a Python type annotation to SQL type string."""
    # Handle Optional/Union types
    origin = get_origin(python_type)
    if origin is not None:
        args = get_args(python_type)
        # Filter out NoneType for Optional types
        non_none_args = [arg for arg in args if arg is not type(None)]
        if non_none_args:
            return _get_sql_type(non_none_args[0])

    # Direct type lookup
    if python_type in TYPE_MAPPING:
        return TYPE_MAPPING[python_type]

    # Check for subclasses
    if isinstance(python_type, type):
        for base_type, sql_type in TYPE_MAPPING.items():
            if issubclass(python_type, base_type):
                return sql_type

    # Default fallback
    return "text"


def _is_nullable(field_info: FieldInfo, annotation: Any) -> bool:
    """Determine if a field is nullable."""
    # Check if the type is Optional (Union with None)
    origin = get_origin(annotation)
    if origin is not None:
        args = get_args(annotation)
        if type(None) in args:
            return True

    # Check if default is None
    if field_info.default is None and field_info.default_factory is None:
        return True

    return False


def _is_primary_key(field_name: str, field_info: FieldInfo) -> bool:
    """Determine if a field is a primary key."""
    # Check for primary_key in json_schema_extra
    extra = field_info.json_schema_extra
    if isinstance(extra, dict) and extra.get("primary_key"):
        return True

    # Convention: field named 'id' is usually primary key
    return field_name == "id"


def _extract_table(model: type[BaseModel]) -> Table:
    """Extract a Table definition from a Pydantic model."""
    table_name = _get_table_name(model)
    columns: list[Column] = []

    for field_name, field_info in model.model_fields.items():
        annotation = field_info.annotation

        # Get description from field
        description = field_info.description

        column = Column(
            name=field_name,
            type=_get_sql_type(annotation),
            primary_key=_is_primary_key(field_name, field_info),
            nullable=_is_nullable(field_info, annotation),
            description=description,
        )
        columns.append(column)

    return Table(
        name=table_name,
        description=model.__doc__,
        columns=columns,
    )


def _infer_relationships(tables: list[Table]) -> list[Relationship]:
    """Infer relationships from foreign key naming conventions.

    Looks for columns ending in '_id' and matches them to table names.
    """
    relationships: list[Relationship] = []
    table_names = {t.name for t in tables}

    for table in tables:
        for column in table.columns:
            if column.name.endswith("_id") and column.name != "id":
                # Extract potential referenced table name
                ref_table_singular = column.name[:-3]  # Remove '_id'

                # Try to find matching table (with pluralization)
                ref_table = None
                for candidate in table_names:
                    # Check if candidate matches the singular form
                    if candidate == ref_table_singular + "s":
                        ref_table = candidate
                        break
                    elif candidate == ref_table_singular + "es":
                        ref_table = candidate
                        break
                    elif candidate == ref_table_singular[:-1] + "ies" and ref_table_singular.endswith("y"):
                        ref_table = candidate
                        break
                    elif candidate == ref_table_singular:
                        ref_table = candidate
                        break

                if ref_table:
                    relationship = Relationship(
                        name=f"{table.name}_{ref_table}",
                        from_table=table.name,
                        from_column=column.name,
                        to_table=ref_table,
                        to_column="id",
                        type="many_to_one",
                    )
                    relationships.append(relationship)

    return relationships


def generate_domain(
    name: str,
    models: list[type[BaseModel]],
    database_type: DatabaseType = "ansi",
    description: str | None = None,
) -> Domain:
    """Generate a Domain schema from Pydantic model classes.

    Args:
        name: Name for the generated domain.
        models: List of Pydantic model classes to include.
        database_type: Target database type (ansi, mysql, postgres, oracle).
        description: Optional description for the domain.

    Returns:
        A Domain object representing the schema.

    Example:
        >>> from pydantic import BaseModel, Field
        >>> class User(BaseModel):
        ...     id: int
        ...     email: str
        ...     name: str | None = None
        >>> domain = generate_domain("mydb", [User])
        >>> domain.tables[0].name
        'users'
    """
    tables = [_extract_table(model) for model in models]
    relationships = _infer_relationships(tables)

    return Domain(
        name=name,
        description=description,
        database_type=database_type,
        tables=tables,
        relationships=relationships,
    )
