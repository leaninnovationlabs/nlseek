"""Tests for the domain generator module."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from nlseek.domain import DomainLoader, generate_domain


class User(BaseModel):
    """User account information."""

    id: int
    email: str
    name: str | None = None
    created_at: datetime


class Product(BaseModel):
    """Product in the catalog."""

    id: int
    name: str = Field(description="Product name")
    price: Decimal
    category_id: int
    in_stock: bool = True


class Order(BaseModel):
    """Customer order."""

    id: int
    user_id: int
    total: float
    order_date: date


class OrderItem(BaseModel):
    """Individual item in an order."""

    id: int
    order_id: int
    product_id: int
    quantity: int


class TestGenerateDomain:
    """Tests for generate_domain function."""

    def test_basic_domain_generation(self) -> None:
        """Test generating a domain from a single model."""
        domain = generate_domain("testdb", [User])

        assert domain.name == "testdb"
        assert len(domain.tables) == 1
        assert domain.tables[0].name == "users"

    def test_domain_with_description(self) -> None:
        """Test domain description is set correctly."""
        domain = generate_domain("testdb", [User], description="Test database")

        assert domain.description == "Test database"

    def test_domain_database_type(self) -> None:
        """Test database type is set correctly."""
        domain = generate_domain("testdb", [User], database_type="postgres")

        assert domain.database_type == "postgres"

    def test_table_name_pluralization(self) -> None:
        """Test that table names are pluralized correctly."""
        domain = generate_domain("testdb", [User, Product, Order, OrderItem])
        table_names = [t.name for t in domain.tables]

        assert "users" in table_names
        assert "products" in table_names
        assert "orders" in table_names
        assert "order_items" in table_names

    def test_table_description_from_docstring(self) -> None:
        """Test that table descriptions come from model docstrings."""
        domain = generate_domain("testdb", [User])

        assert domain.tables[0].description == "User account information."

    def test_column_extraction(self) -> None:
        """Test that columns are extracted from model fields."""
        domain = generate_domain("testdb", [User])
        columns = domain.tables[0].columns
        column_names = [c.name for c in columns]

        assert "id" in column_names
        assert "email" in column_names
        assert "name" in column_names
        assert "created_at" in column_names

    def test_column_types(self) -> None:
        """Test that column types are mapped correctly."""
        domain = generate_domain("testdb", [User, Product])

        # Find users table
        users_table = next(t for t in domain.tables if t.name == "users")
        columns_by_name = {c.name: c for c in users_table.columns}

        assert columns_by_name["id"].type == "integer"
        assert columns_by_name["email"].type == "varchar(255)"
        assert columns_by_name["created_at"].type == "timestamp"

        # Find products table
        products_table = next(t for t in domain.tables if t.name == "products")
        products_by_name = {c.name: c for c in products_table.columns}

        assert products_by_name["price"].type == "decimal(10,2)"
        assert products_by_name["in_stock"].type == "boolean"

    def test_primary_key_detection(self) -> None:
        """Test that id fields are detected as primary keys."""
        domain = generate_domain("testdb", [User])
        users_table = domain.tables[0]
        id_column = next(c for c in users_table.columns if c.name == "id")

        assert id_column.primary_key is True

    def test_nullable_detection(self) -> None:
        """Test that nullable fields are detected correctly."""
        domain = generate_domain("testdb", [User])
        users_table = domain.tables[0]
        columns_by_name = {c.name: c for c in users_table.columns}

        assert columns_by_name["name"].nullable is True
        assert columns_by_name["email"].nullable is False

    def test_field_description(self) -> None:
        """Test that field descriptions are extracted."""
        domain = generate_domain("testdb", [Product])
        products_table = domain.tables[0]
        name_column = next(c for c in products_table.columns if c.name == "name")

        assert name_column.description == "Product name"

    def test_relationship_inference(self) -> None:
        """Test that relationships are inferred from foreign key columns."""
        domain = generate_domain("testdb", [User, Order])

        assert len(domain.relationships) >= 1
        # Find the user_id relationship
        user_rel = next((r for r in domain.relationships if r.from_column == "user_id"), None)
        assert user_rel is not None
        assert user_rel.from_table == "orders"
        assert user_rel.to_table == "users"
        assert user_rel.to_column == "id"
        assert user_rel.type == "many_to_one"

    def test_multiple_relationships(self) -> None:
        """Test inferring multiple relationships."""
        domain = generate_domain("testdb", [User, Product, Order, OrderItem])

        # Should have relationships for: user_id, order_id, product_id, category_id
        assert len(domain.relationships) >= 3

        rel_columns = [r.from_column for r in domain.relationships]
        assert "user_id" in rel_columns
        assert "order_id" in rel_columns
        assert "product_id" in rel_columns


class TestDomainLoaderRegisterFromModels:
    """Tests for DomainLoader.register_from_models method."""

    def test_register_from_models_basic(self) -> None:
        """Test basic registration from models."""
        loader = DomainLoader()
        name = loader.register_from_models("testdb", [User])

        assert name == "testdb"
        assert "testdb" in loader.list_domains()

    def test_register_from_models_get_domain(self) -> None:
        """Test that registered domain can be retrieved."""
        loader = DomainLoader()
        loader.register_from_models("testdb", [User, Order])
        domain = loader.get_domain("testdb")

        assert domain["name"] == "testdb"
        assert len(domain["tables"]) == 2

    def test_register_from_models_get_table(self) -> None:
        """Test that tables can be retrieved from registered domain."""
        loader = DomainLoader()
        loader.register_from_models("testdb", [User])
        table = loader.get_table("testdb", "users")

        assert table["name"] == "users"
        assert len(table["columns"]) == 4

    def test_register_from_models_with_options(self) -> None:
        """Test registration with database_type and description."""
        loader = DomainLoader()
        loader.register_from_models(
            "testdb",
            [User],
            database_type="postgres",
            description="Test database",
        )
        domain = loader.get_domain("testdb")

        assert domain["database_type"] == "postgres"
        assert domain["description"] == "Test database"


class TestTypeMapping:
    """Tests for Python to SQL type mapping."""

    def test_uuid_type(self) -> None:
        """Test UUID type mapping."""

        class ModelWithUUID(BaseModel):
            id: UUID

        domain = generate_domain("testdb", [ModelWithUUID])
        id_col = domain.tables[0].columns[0]
        assert id_col.type == "uuid"

    def test_date_type(self) -> None:
        """Test date type mapping."""

        class ModelWithDate(BaseModel):
            created: date

        domain = generate_domain("testdb", [ModelWithDate])
        col = domain.tables[0].columns[0]
        assert col.type == "date"

    def test_bytes_type(self) -> None:
        """Test bytes type mapping."""

        class ModelWithBytes(BaseModel):
            data: bytes

        domain = generate_domain("testdb", [ModelWithBytes])
        col = domain.tables[0].columns[0]
        assert col.type == "bytea"

    def test_unknown_type_defaults_to_text(self) -> None:
        """Test that unknown types default to text."""

        class CustomType:
            pass

        class ModelWithCustom(BaseModel):
            data: CustomType  # type: ignore

            class Config:
                arbitrary_types_allowed = True

        domain = generate_domain("testdb", [ModelWithCustom])
        col = domain.tables[0].columns[0]
        assert col.type == "text"


class TestTableNameConversions:
    """Tests for class name to table name conversion."""

    def test_simple_name(self) -> None:
        """Test simple class name conversion."""

        class Item(BaseModel):
            id: int

        domain = generate_domain("testdb", [Item])
        assert domain.tables[0].name == "items"

    def test_camel_case_name(self) -> None:
        """Test CamelCase class name conversion."""

        class ShoppingCart(BaseModel):
            id: int

        domain = generate_domain("testdb", [ShoppingCart])
        assert domain.tables[0].name == "shopping_carts"

    def test_name_ending_in_y(self) -> None:
        """Test class names ending in 'y' are pluralized correctly."""

        class Category(BaseModel):
            id: int

        domain = generate_domain("testdb", [Category])
        assert domain.tables[0].name == "categories"

    def test_name_ending_in_s(self) -> None:
        """Test class names ending in 's' are pluralized correctly."""

        class Address(BaseModel):
            id: int

        domain = generate_domain("testdb", [Address])
        assert domain.tables[0].name == "addresses"

    def test_custom_tablename(self) -> None:
        """Test that __tablename__ attribute is respected."""

        class MyModel(BaseModel):
            __tablename__ = "custom_table"
            id: int

        domain = generate_domain("testdb", [MyModel])
        assert domain.tables[0].name == "custom_table"
