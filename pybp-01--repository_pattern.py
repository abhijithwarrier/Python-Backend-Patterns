"""
Programmer: python_scripts (Abhijith Warrier)

PYTHON BACKEND PATTERNS — REPOSITORY PATTERN

This script demonstrates the Repository Pattern by separating
data access logic from the application's business logic.
"""

# Import dataclass for defining the data model
from dataclasses import dataclass

# Import Optional for values that may not exist
from typing import Optional


# -----------------------------------------
# Step 1: Define the application data model
# -----------------------------------------
@dataclass
class User:
    id: int
    name: str
    email: str


# -----------------------------------------
# Step 2: Create the repository
# -----------------------------------------
class UserRepository:
    """Handles all user data access operations."""

    def __init__(self):
        # Use a dictionary as an in-memory data source
        self._users = {}

    def add(self, user: User) -> None:
        """Store a new user."""
        self._users[user.id] = user

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Retrieve a user by ID."""
        return self._users.get(user_id)

    def get_all(self) -> list[User]:
        """Retrieve all users."""
        return list(self._users.values())

    def delete(self, user_id: int) -> bool:
        """Delete a user if it exists."""
        if user_id not in self._users:
            return False

        del self._users[user_id]
        return True


# -----------------------------------------
# Step 3: Create the service layer
# -----------------------------------------
class UserService:
    """Contains application business logic."""

    def __init__(self, repository: UserRepository):
        # Depend on the repository instead of the data source
        self.repository = repository

    def register_user(self, user_id: int, name: str, email: str) -> User:
        """Register a new user."""

        # Prevent duplicate user IDs
        if self.repository.get_by_id(user_id):
            raise ValueError(f"User {user_id} already exists")

        user = User(
            id=user_id,
            name=name,
            email=email,
        )

        self.repository.add(user)

        return user

    def find_user(self, user_id: int) -> Optional[User]:
        """Find an existing user."""
        return self.repository.get_by_id(user_id)

    def list_users(self) -> list[User]:
        """Return all registered users."""
        return self.repository.get_all()

    def remove_user(self, user_id: int) -> bool:
        """Remove an existing user."""
        return self.repository.delete(user_id)


# -----------------------------------------
# Step 4: Configure application components
# -----------------------------------------
repository = UserRepository()
service = UserService(repository)


# -----------------------------------------
# Step 5: Execute application operations
# -----------------------------------------
service.register_user(1, "Alice", "alice@example.com")
service.register_user(2, "Bob", "bob@example.com")
service.register_user(3, "Charlie", "charlie@example.com")

print("Registered Users:")

for user in service.list_users():
    print(f"{user.id}: {user.name} ({user.email})")


# Retrieve a user through the service
user = service.find_user(2)

if user:
    print(f"\nFound User: {user.name}")


# Delete a user through the service
service.remove_user(1)

print("\nUsers After Deletion:")

for user in service.list_users():
    print(f"{user.id}: {user.name} ({user.email})")
