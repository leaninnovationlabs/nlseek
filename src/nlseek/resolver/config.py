"""Configuration for the query resolver."""

from pydantic import BaseModel, Field

DEFAULT_MODEL = "anthropic:claude-opus-4-20250514"


class ResolverConfig(BaseModel):
    """Configuration for the QueryResolver.

    Attributes:
        model: The pydantic-ai model identifier to use for query generation.
            Defaults to Claude Opus 4.
    """

    model: str = Field(
        default=DEFAULT_MODEL,
        description="The AI model identifier (e.g. 'anthropic:claude-sonnet-4-20250514')",
    )
