"""Script to create test orders for development."""

import argparse
import asyncio
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(__file__).rsplit("scripts", 1)[0])

from app.config import get_settings
from app.db.session import async_session_maker
from app.services.test_orders import (
    create_test_order,
    create_bulk_test_orders,
)

settings = get_settings()


async def create_single_order(
    customer_name: str,
    customer_email: str,
    spell_type: str,
    intention: str,
) -> None:
    """Create a single test order."""
    async with async_session_maker() as session:
        order = await create_test_order(
            db=session,
            customer_name=customer_name,
            customer_email=customer_email,
            spell_type=spell_type,
            intention=intention,
        )
        print(f"\nCreated test order:")
        print(f"  ID: {order.id}")
        print(f"  Receipt ID: {order.etsy_receipt_id}")
        print(f"  Customer: {order.customer_name} <{order.customer_email}>")
        print(f"  Spell Type: {order.raw_spell_type}")
        print(f"  Intention: {order.intention[:50]}...")
        print(f"  Status: {order.status.value}")


async def create_bulk_orders(count: int, spell_types: list[str] | None) -> None:
    """Create multiple test orders."""
    async with async_session_maker() as session:
        orders = await create_bulk_test_orders(
            db=session,
            count=count,
            spell_types=spell_types,
        )
        print(f"\nCreated {len(orders)} test orders:\n")
        for order in orders:
            print(f"  [{order.id}] {order.customer_name} - {order.raw_spell_type}")
        print(f"\nAll orders created with status: pending")


def main() -> None:
    """Main entry point."""
    # Safety check for production
    if settings.ENVIRONMENT == "production":
        print("ERROR: Cannot create test orders in production environment!")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Create test orders for development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/create_test_orders.py single --name "John Doe" --email "john@example.com" --type love
  python scripts/create_test_orders.py bulk --count 10
  python scripts/create_test_orders.py bulk --count 5 --types love protection healing
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Single order subcommand
    single_parser = subparsers.add_parser("single", help="Create a single test order")
    single_parser.add_argument("--name", required=True, help="Customer name")
    single_parser.add_argument("--email", required=True, help="Customer email")
    single_parser.add_argument(
        "--type",
        choices=["love", "prosperity", "protection", "healing"],
        default="love",
        help="Spell type (default: love)",
    )
    single_parser.add_argument(
        "--intention",
        default="For testing the spell fulfillment workflow",
        help="Customer intention",
    )

    # Bulk order subcommand
    bulk_parser = subparsers.add_parser(
        "bulk", help="Create multiple random test orders"
    )
    bulk_parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of orders to create (default: 5)",
    )
    bulk_parser.add_argument(
        "--types",
        nargs="+",
        choices=["love", "prosperity", "protection", "healing"],
        help="Spell types to cycle through (optional, random if not specified)",
    )

    args = parser.parse_args()

    if args.command == "single":
        asyncio.run(
            create_single_order(
                customer_name=args.name,
                customer_email=args.email,
                spell_type=args.type,
                intention=args.intention,
            )
        )
    elif args.command == "bulk":
        asyncio.run(create_bulk_orders(args.count, args.types))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
