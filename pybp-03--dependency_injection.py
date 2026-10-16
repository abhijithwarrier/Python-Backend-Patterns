"""
Programmer: python_scripts (Abhijith Warrier)

PYTHON BACKEND PATTERNS — DEPENDENCY INJECTION

This script demonstrates Dependency Injection by passing repositories
and services into application components instead of creating them internally.
"""

# Import dataclass for defining the data model
from dataclasses import dataclass

# Import Protocol for defining repository contracts
from typing import Protocol, Optional


# -----------------------------------------
# Step 1: Define the application data model
# -----------------------------------------
@dataclass
class User:
    id: int
    name: str
    email: str


# -----------------------------------------
# Step 2: Define the repository contract
# -----------------------------------------
class UserRepository(Protocol):
    """Defines the operations required by the service."""

    def add(self, user: User) -> None:
        """Store a user."""
        ...

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Retrieve a user by ID."""
        ...


# -----------------------------------------
# Step 3: Create the repository implementation
# -----------------------------------------
class InMemoryUserRepository:
    """Stores users in an in-memory dictionary."""

    def __init__(self):
        # Use a dictionary as the data source
        self._users = {}

    def add(self, user: User) -> None:
        """Store a new user."""
        self._users[user.id] = user

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Retrieve a user by ID."""
        return self._users.get(user_id)


# -----------------------------------------
# Step 4: Create the service layer
# -----------------------------------------
class UserService:
    """Handles user-related business operations."""

    def __init__(self, repository: UserRepository):
        # Receive the repository instead of creating it
        self.repository = repository

    def register_user(
        self,
        user_id: int,
        name: str,
        email: str,
    ) -> User:
        """Register a user after validation."""

        # Prevent duplicate user IDs
        if self.repository.get_by_id(user_id):
            raise ValueError(f"User {user_id} already exists")

        # Validate user information
        if not name.strip() or not email.strip():
            raise ValueError("Name and email cannot be empty")

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


# -----------------------------------------
# Step 5: Create the controller
# -----------------------------------------
class UserController:
    """Handles requests by delegating operations to the service."""

    def __init__(self, service: UserService):
        # Receive the service instead of creating it
        self.service = service

    def create_user(
        self,
        user_id: int,
        name: str,
        email: str,
    ) -> dict:
        """Handle a user registration request."""

        try:
            user = self.service.register_user(
                user_id,
                name,
                email,
            )

            return {
                "success": True,
                "message": "User registered successfully",
                "user_id": user.id,
            }

        except ValueError as error:
            return {
                "success": False,
                "message": str(error),
            }

    def get_user(self, user_id: int) -> dict:
        """Handle a user retrieval request."""

        user = self.service.find_user(user_id)

        if not user:
            return {
                "success": False,
                "message": "User not found",
            }

        return {
            "success": True,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
            },
        }


# -----------------------------------------
# Step 6: Configure application dependencies
# -----------------------------------------
# Create dependencies outside the application classes
repository = InMemoryUserRepository()

# Inject the repository into the service
service = UserService(repository)

# Inject the service into the controller
controller = UserController(service)


# -----------------------------------------
# Step 7: Execute application operations
# -----------------------------------------
print("Registering Users:")

print(controller.create_user(1, "Alice", "alice@example.com"))
print(controller.create_user(2, "Bob", "bob@example.com"))

# Attempt to register an existing user
print(controller.create_user(1, "Charlie", "charlie@example.com"))

# Retrieve an existing user
print("\nRetrieving User:")
print(controller.get_user(2))


# -----------------------------------------
# Step 8: Create a fake repository for testing
# -----------------------------------------
class FakeUserRepository:
    """Provides a lightweight repository for testing."""

    def __init__(self):
        # Store test users independently
        self._users = {}

    def add(self, user: User) -> None:
        """Store a test user."""
        self._users[user.id] = user

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Retrieve a test user."""
        return self._users.get(user_id)


# -----------------------------------------
# Step 9: Test with injected dependencies
# -----------------------------------------
# Replace the repository without changing UserService
fake_repository = FakeUserRepository()
test_service = UserService(fake_repository)

# Register a user through the test service
test_user = test_service.register_user(
    101,
    "Test User",
    "test@example.com",
)

# Verify that the fake repository received the user
assert fake_repository.get_by_id(101) == test_user

# Verify that duplicate IDs are rejected
try:
    test_service.register_user(
        101,
        "Duplicate User",
        "duplicate@example.com",
    )

    raise AssertionError("Duplicate registration was not rejected")

except ValueError:
    pass

print("\nDependency Injection Test Passed!")
