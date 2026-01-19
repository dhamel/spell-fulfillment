"""Script to create the admin operator user."""

import asyncio
import sys
from getpass import getpass

# Add parent directory to path for imports
sys.path.insert(0, str(__file__).rsplit("scripts", 1)[0])

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import async_session_maker
from app.models.operator import Operator


async def create_admin(username: str, password: str) -> None:
    """Create an admin operator user."""
    async with async_session_maker() as session:
        # Check if user already exists
        result = await session.execute(
            select(Operator).where(Operator.username == username)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"User '{username}' already exists.")
            update = input("Update password? (y/n): ").lower().strip()
            if update == "y":
                existing.password_hash = get_password_hash(password)
                await session.commit()
                print(f"Password updated for user '{username}'.")
            return

        # Create new operator
        operator = Operator(
            username=username,
            password_hash=get_password_hash(password),
            is_active=True,
        )
        session.add(operator)
        await session.commit()
        print(f"Admin user '{username}' created successfully!")


def main() -> None:
    """Main entry point."""
    print("=== Create Admin User ===\n")

    username = input("Username: ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)

    password = getpass("Password: ")
    if len(password) < 8:
        print("Password must be at least 8 characters.")
        sys.exit(1)

    password_confirm = getpass("Confirm password: ")
    if password != password_confirm:
        print("Passwords do not match.")
        sys.exit(1)

    asyncio.run(create_admin(username, password))


if __name__ == "__main__":
    main()
