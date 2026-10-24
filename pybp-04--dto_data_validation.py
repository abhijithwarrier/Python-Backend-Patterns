"""
Programmer: python_scripts (Abhijith Warrier)

PYTHON BACKEND PATTERNS — DTO & DATA VALIDATION

Validate incoming data at the application boundary, then transfer a
structured DTO to the service layer for business-rule checks.

Requirements: Python 3.10+ and Pydantic v2
Install: python -m pip install "pydantic>=2,<3"
Run: python dto_data_validation.py
"""

# Import Pydantic tools for defining and validating the data contract
from pydantic import BaseModel, ConfigDict, Field, ValidationError


# -----------------------------------------
# Step 1: Define the data transfer object
# -----------------------------------------
class OrderDTO(BaseModel):
    """Defines the accepted structure of an incoming order request."""

    # Reject type coercion and unexpected fields
    model_config = ConfigDict(strict=True, extra="forbid")

    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=10)


# -----------------------------------------
# Step 2: Create the service layer
# -----------------------------------------
class OrderService:
    """Checks business rules after the request passes DTO validation."""

    def __init__(self, stock: dict[int, int]):
        self.stock = stock

    def create_order(self, dto: OrderDTO, *, can_order: bool) -> dict:
        """Accept a demo order after permission and inventory checks."""

        # Permission comes from trusted application context, not the payload
        if not can_order:
            raise PermissionError("You do not have permission to place orders")

        if dto.product_id not in self.stock:
            raise ValueError("Product not found")

        if dto.quantity > self.stock[dto.product_id]:
            raise ValueError("Insufficient stock")

        # Demonstration only: no database write or inventory reservation
        return dto.model_dump()


# -----------------------------------------
# Step 3: Validate at the application boundary
# -----------------------------------------
class OrderController:
    """Validates input before calling the service."""

    def __init__(self, service: OrderService):
        self.service = service

    def create_order(self, data: dict, *, can_order: bool) -> dict:
        """Handle an order request and return a structured result."""

        try:
            dto = OrderDTO.model_validate(data)
        except ValidationError as error:
            # Report useful field errors without echoing the submitted payload
            return {
                "success": False,
                "error_type": "validation",
                "errors": [
                    {
                        "field": ".".join(str(part) for part in item["loc"]),
                        "message": item["msg"],
                        "type": item["type"],
                    }
                    for item in error.errors(include_input=False, include_url=False)
                ],
            }

        try:
            order = self.service.create_order(dto, can_order=can_order)
        except PermissionError as error:
            return {"success": False, "error_type": "permission", "message": str(error)}
        except ValueError as error:
            return {"success": False, "error_type": "business_rule", "message": str(error)}

        return {"success": True, "message": "Demo order accepted", "order": order}


# -----------------------------------------
# Step 4: Configure and demonstrate the flow
# -----------------------------------------
def main() -> None:
    service = OrderService(stock={42: 5})
    controller = OrderController(service)

    # Simulate a permission determined by an authentication/authorization layer
    can_order = True

    cases = [
        ("Valid request", {"product_id": 42, "quantity": 2}, None),
        ("String instead of integer", {"product_id": 42, "quantity": "2"}, "int_type"),
        ("Quantity below minimum", {"product_id": 42, "quantity": 0}, "greater_than_equal"),
        ("Quantity above maximum", {"product_id": 42, "quantity": 11}, "less_than_equal"),
        ("Invalid product ID", {"product_id": 0, "quantity": 2}, "greater_than"),
        ("Missing quantity", {"product_id": 42}, "missing"),
        ("Unexpected field", {"product_id": 42, "quantity": 2, "admin": True}, "extra_forbidden"),
    ]

    # -----------------------------------------
    # Step 5: Verify the validation contract
    # -----------------------------------------
    for label, payload, expected_error in cases:
        result = controller.create_order(payload, can_order=can_order)
        print(f"\n{label}:\n{result}")

        if expected_error is None:
            assert result["success"] is True
            assert result["order"] == payload
        else:
            assert result["success"] is False
            assert result["error_type"] == "validation"
            assert result["errors"][0]["type"] == expected_error

    # -----------------------------------------
    # Step 6: Verify separate business rules
    # -----------------------------------------
    # Eight satisfies the DTO's 1–10 range, but exceeds available stock (5)
    insufficient_stock = controller.create_order(
        {"product_id": 42, "quantity": 8}, can_order=True
    )
    assert insufficient_stock["error_type"] == "business_rule"
    assert insufficient_stock["message"] == "Insufficient stock"
    print(f"\nValid DTO, insufficient stock:\n{insufficient_stock}")

    denied = controller.create_order(
        {"product_id": 42, "quantity": 2}, can_order=False
    )
    assert denied["error_type"] == "permission"
    print(f"\nValid DTO, permission denied:\n{denied}")

    print("\nDTO & Data Validation Tests Passed!")


if __name__ == "__main__":
    main()
