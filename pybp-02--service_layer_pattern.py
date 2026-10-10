"""
Programmer: python_scripts (Abhijith Warrier)

PYTHON BACKEND PATTERNS — SERVICE LAYER PATTERN

This script demonstrates the Service Layer Pattern by moving business rules
into reusable services instead of keeping them inside controllers.
"""

# Import dataclass for defining the data model
from dataclasses import dataclass

# Import Decimal for accurate monetary calculations
from decimal import Decimal, InvalidOperation

# Import Optional for values that may not exist
from typing import Optional

# -----------------------------------------
# Step 1: Define the application data model
# -----------------------------------------
@dataclass
class Order:
    id: int
    customer: str
    amount: Decimal
    discount: Decimal
    final_amount: Decimal
    status: str = "PENDING"


# -----------------------------------------
# Step 2: Create the repository
# -----------------------------------------
class OrderRepository:
    """Handles all order data access operations."""

    def __init__(self):
        # Use a dictionary as an in-memory data source
        self._orders = {}

    def add(self, order: Order) -> None:
        """Store a new order."""
        self._orders[order.id] = order

    def get_by_id(self, order_id: int) -> Optional[Order]:
        """Retrieve an order by ID."""
        return self._orders.get(order_id)

    def get_all(self) -> list[Order]:
        """Retrieve all orders."""
        return list(self._orders.values())

    def update(self, order: Order) -> None:
        """Update an existing order."""
        self._orders[order.id] = order


# -----------------------------------------
# Step 3: Create the service layer
# -----------------------------------------
class OrderService:
    """Contains reusable order-processing business rules."""

    DISCOUNT_THRESHOLD = Decimal("1000.00")
    DISCOUNT_RATE = Decimal("0.10")

    def __init__(self, repository: OrderRepository):
        # Depend on the repository for data access
        self.repository = repository

    def create_order(
        self,
        order_id: int,
        customer: str,
        amount: Decimal,
    ) -> Order:
        """Validate and create a new order."""

        # Prevent duplicate order IDs
        if self.repository.get_by_id(order_id):
            raise ValueError(f"Order {order_id} already exists")

        # Validate customer information
        if not isinstance(customer, str) or not customer.strip():
            raise ValueError("Customer name cannot be empty")

        # Convert the amount into Decimal
        try:
            amount = Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("Invalid order amount")

        # Validate the order amount
        if not amount.is_finite() or amount <= 0:
            raise ValueError("Order amount must be positive")

        # Apply a 10% discount for qualifying orders
        discount = Decimal("0.00")

        if amount >= self.DISCOUNT_THRESHOLD:
            discount = amount * self.DISCOUNT_RATE

        final_amount = amount - discount

        # Create the order after applying business rules
        order = Order(
            id=order_id,
            customer=customer.strip(),
            amount=amount,
            discount=discount,
            final_amount=final_amount,
        )

        self.repository.add(order)

        return order

    def confirm_order(self, order_id: int) -> Order:
        """Confirm an existing pending order."""

        order = self.repository.get_by_id(order_id)

        if not order:
            raise ValueError(f"Order {order_id} does not exist")

        # Only pending orders can be confirmed
        if order.status != "PENDING":
            raise ValueError("Only pending orders can be confirmed")

        order.status = "CONFIRMED"

        self.repository.update(order)

        return order

    def find_order(self, order_id: int) -> Optional[Order]:
        """Find an existing order."""
        return self.repository.get_by_id(order_id)

    def list_orders(self) -> list[Order]:
        """Return all orders."""
        return self.repository.get_all()


# -----------------------------------------
# Step 4: Create the controller
# -----------------------------------------
class OrderController:
    """Handles requests by delegating business logic to services."""

    def __init__(self, service: OrderService):
        # The controller depends on the service layer
        self.service = service

    def create_order(
        self,
        order_id: int,
        customer: str,
        amount: Decimal,
    ) -> dict:
        """Handle an order creation request."""

        try:
            # Delegate validation and calculations to the service
            order = self.service.create_order(
                order_id,
                customer,
                amount,
            )

            return {
                "success": True,
                "message": "Order created successfully",
                "order_id": order.id,
                "final_amount": str(order.final_amount),
            }

        except ValueError as error:
            return {
                "success": False,
                "message": str(error),
            }

    def confirm_order(self, order_id: int) -> dict:
        """Handle an order confirmation request."""

        try:
            # Delegate order confirmation to the service
            order = self.service.confirm_order(order_id)

            return {
                "success": True,
                "message": "Order confirmed successfully",
                "status": order.status,
            }

        except ValueError as error:
            return {
                "success": False,
                "message": str(error),
            }


# -----------------------------------------
# Step 5: Configure application components
# -----------------------------------------
repository = OrderRepository()
service = OrderService(repository)
controller = OrderController(service)


# -----------------------------------------
# Step 6: Execute application operations
# -----------------------------------------
print("Creating Orders:")

# Create orders through the controller
response1 = controller.create_order(1, "Alice", "1500.00")
response2 = controller.create_order(2, "Bob", "500.00")
response3 = controller.create_order(3, "Charlie", "-100.00")

print("Alice:", response1)
print("Bob:", response2)
print("Charlie:", response3)

# Confirm an existing order
confirmation = controller.confirm_order(1)

print("\nOrder Confirmation:")
print(confirmation)


# -----------------------------------------
# Step 7: Reuse the service independently
# -----------------------------------------
# Business logic can also be used by background jobs,
# scheduled tasks, or other application components.

order = service.create_order(4, "David", "2000.00")

print("\nDirect Service Access:")
print(
    f"Customer: {order.customer} | "
    f"Amount: {order.amount} | "
    f"Discount: {order.discount} | "
    f"Final Amount: {order.final_amount}"
)


# -----------------------------------------
# Step 8: Display all orders
# -----------------------------------------
print("\nAll Orders:")

for order in service.list_orders():
    print(
        f"{order.id}: {order.customer} | "
        f"Amount: {order.final_amount} | "
        f"Status: {order.status}"
    )
