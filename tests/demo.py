#!/usr/bin/env python3
"""CLI demo script for nlseek — converts natural language to SQL."""

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOMAINS_DIR = PROJECT_ROOT / "examples" / "domains"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a natural language question to SQL using the ecommerce domain.",
    )
    parser.add_argument("query", help="Natural language question to convert to SQL")
    parser.add_argument(
        "--model",
        default="anthropic:claude-opus-4-20250514",
        help="AI model to use (default: anthropic:claude-opus-4-20250514)",
    )
    args = parser.parse_args()

    from nlseek import DomainLoader, QueryResolver

    loader = DomainLoader(DOMAINS_DIR)
    domain = loader.get_domain("ecommerce")

    resolver = QueryResolver(domain, model=args.model)
    result = resolver.resolve(args.query)

    print("\n--- SQL Query ---")
    print(f"Query ID: {result.query_id}")
    print(result.query)
    print("\n--- Explanation ---")
    print(result.explanation)
    print("\n--- Tables Used ---")
    print(", ".join(result.tables_used))
    print("\n--- Entities ---")
    print(result.entities)
    print("\n--- Filters ---")
    print(result.filters)


if __name__ == "__main__":
    main()
