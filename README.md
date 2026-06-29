# 🛒 E-Commerce Microservices Platform

A production-ready, cloud-native e-commerce backend built with a **microservices architecture** using **FastAPI** and **AWS DynamoDB**. Each service is independently deployable, follows clean architecture principles, and communicates via synchronous REST APIs.

---

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Services Summary](#services-summary)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Data Models](#data-models)
- [API Reference](#api-reference)
  - [Product Service](#1-product-service--port-8000)
  - [Inventory Service](#2-inventory-service--port-8001)
  - [Cart Service](#3-cart-service--port-8002)
  - [Payment Service](#4-payment-service--port-8003)
  - [Order Service](#5-order-service--port-8004)
  - [Search Service](#6-search-service--port-8005)
- [Inter-Service Communication](#inter-service-communication)
- [DynamoDB Schema](#dynamodb-schema)
- [Error Handling](#error-handling)
- [Getting Started](#getting-started)
- [Running the Services](#running-the-services)
- [Design Patterns](#design-patterns)

---

## Architecture Overview

This platform follows a **microservices architecture** where each domain is encapsulated in its own independently runnable service. Services communicate synchronously over HTTP, with each service owning its own DynamoDB table.

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT / FRONTEND                          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ HTTP Requests
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌────────────────┐    ┌────────────────────┐   ┌─────────────────┐
│ Product Service│    │   Search Service   │   │  Cart Service   │
│   :8000        │    │      :8005         │   │    :8002        │
└───────┬────────┘    └────────────────────┘   └────────┬────────┘
        │                       ▲                       │
        │ (initialize stock)    │ (index product)       │ (check stock)
        │                       │                       │
        ▼                       │                       ▼
┌────────────────────────────────────────────────────────────────────┐
│                       Inventory Service :8001                      │
└────────────────────────────────────────────────────────────────────┘
        ▲                                               ▲
        │ (reserve / deduct / release)                  │
        │                                               │
┌───────┴────────┐                           ┌──────────┴──────────┐
│  Order Service │                           │   Payment Service   │
│    :8004       │                           │       :8003         │
└────────────────┘                           └─────────────────────┘
        ▲
        │ (fetch cart, clear cart)
        │
┌───────┴────────┐
│  Cart Service  │
│    :8002       │
└────────────────┘
```

### Service Communication Flow (Happy Path)

```
User → Search Service     → Find product
User → Cart Service       → Add item (validates stock via Inventory Service)
User → Order Service      → Checkout (fetches Cart, reserves stock via Inventory Service)
User → Payment Service    → Initiate & verify payment
Admin → Order Service     → Update status to SHIPPED/COMPLETED → Inventory deducted permanently
```

---

## Services Summary

| Service | Port | Responsibility | DynamoDB Table |
|---|---|---|---|
| **Product Service** | 8000 | Product catalog CRUD, triggers inventory init & search indexing | `Products` |
| **Inventory Service** | 8001 | Stock tracking, atomic reserve/deduct/release operations | `Inventory` |
| **Cart Service** | 8002 | User shopping cart with TTL-based expiry | `Carts` |
| **Payment Service** | 8003 | Payment initiation, verification, and webhook processing | `Payments` |
| **Order Service** | 8004 | Order lifecycle management, orchestrates cart + inventory | `Orders` |
| **Search Service** | 8005 | Full-text product search with DynamoDB-backed index | `SearchIndex` |

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Framework** | FastAPI (Python) |
| **ASGI Server** | Uvicorn |
| **Database** | AWS DynamoDB (on-demand billing) |
| **AWS SDK** | Boto3 |
| **Validation** | Pydantic v2 |
| **Logging** | Python `logging` module (structured) |
| **HTTP Client** | `requests` (inter-service calls) |

---

## Project Structure

Each microservice follows an identical clean architecture layout:

```
E-Commerce/
├── product-service/
│   ├── setup_dynamo.py              # One-time DynamoDB table provisioning script
│   └── src/
│       ├── main.py                  # FastAPI app, router registration, exception handlers
│       ├── controllers/
│       │   └── product_controller.py  # Route definitions, HTTP layer
│       ├── services/
│       │   └── product_service.py     # Business logic, inter-service calls
│       ├── repositories/
│       │   └── product_repository.py  # DynamoDB data access layer
│       ├── models/
│       │   └── product.py             # Domain entity (Python dataclass)
│       ├── dto/
│       │   └── product_dto.py         # Pydantic request/response schemas
│       ├── exceptions/
│       │   └── app_exceptions.py      # Custom exception hierarchy
│       └── utils/
│           └── logger.py              # Centralized logger factory
│
├── inventory-service/     # (same structure, port 8001)
├── cart-service/          # (same structure, port 8002)
├── payment-service/       # (same structure, port 8003)
├── order-service/         # (same structure, port 8004)
└── search-service/        # (same structure, port 8005)
```

### Layer Responsibilities

| Layer | File | Role |
|---|---|---|
| **Controller** | `*_controller.py` | HTTP routing, status codes, request/response binding |
| **Service** | `*_service.py` | Business logic, inter-service orchestration |
| **Repository** | `*_repository.py` | All DynamoDB read/write operations |
| **Model** | `*.py` in `models/` | Pure Python domain entity (dataclass) |
| **DTO** | `*_dto.py` | Pydantic schemas for API validation and serialization |
| **Exception** | `app_exceptions.py` | Typed exceptions (`NotFoundError`, `ConflictError`, etc.) |

---

## Data Models

### Product
```python
product_id: str          # UUID
sku: str                 # Unique product SKU
name: str
description: str
category: str
brand: str
price: float
currency: str            # Default: "USD"
status: str              # "DRAFT" | "ACTIVE" | "INACTIVE"
images: List[str]        # List of image URLs
attributes: Dict[str, Any]  # Flexible key-value product specs
is_deleted: bool         # Soft delete flag
created_at: datetime
updated_at: datetime
```

### Inventory
```python
product_id: str
available_quantity: int   # Stock available for purchase
reserved_quantity: int    # Held for pending orders
updated_at: datetime
```

### Cart / CartItem
```python
# Cart
user_id: str
items: Dict[product_id, CartItem]
expires_at: int          # Unix timestamp; DynamoDB TTL (7 days)
updated_at: datetime

# CartItem
product_id: str
name: str
price: float
quantity: int
```

### Order / OrderItem
```python
# Order
order_id: str            # Format: "ord_<10 hex chars>"
user_id: str
items: List[OrderItem]
total_amount: float
currency: str
status: str              # PENDING_PAYMENT | PAID | CANCELLED | SHIPPED | COMPLETED
created_at: datetime
updated_at: datetime

# OrderItem
product_id: str
name: str
price: float
quantity: int
```

### Payment
```python
payment_id: str          # Format: "pay_<12 hex chars>"
order_id: str
user_id: str
amount: float
currency: str
status: str              # PENDING | SUCCESS | FAILED | REFUNDED
provider: str            # STRIPE | PAYPAL
provider_transaction_id: Optional[str]
created_at: datetime
updated_at: datetime
```

### SearchItem
```python
product_id: str
name: str
description: str
category: str
price: float
images: List[str]
search_tags: str         # Lowercase concatenation of name + description + category
```

---

## API Reference

All services return responses in a consistent envelope:

```json
// Success
{ "success": true, "data": { ... } }

// Error
{ "success": false, "error": "Human-readable error message" }
```

---

### 1. Product Service — Port 8000

Base URL: `http://localhost:8000/api/v1/products`

| Method | Endpoint | Description | Request Body |
|---|---|---|---|
| `POST` | `/` | Create a new product | `CreateProductDTO` |
| `GET` | `/` | List all products | — |
| `GET` | `/{product_id}` | Get a product by ID | — |
| `PATCH` | `/{product_id}` | Update product fields | `UpdateProductDTO` |
| `DELETE` | `/{product_id}` | Soft-delete a product | — |

#### `POST /` — Create Product

**Request Body:**
```json
{
  "sku": "LAPTOP-001",
  "name": "Pro Laptop 15",
  "description": "High-performance laptop for professionals",
  "category": "Electronics",
  "brand": "TechBrand",
  "price": 1299.99,
  "currency": "USD",
  "images": ["https://cdn.example.com/img1.jpg"],
  "attributes": {
    "ram": "16GB",
    "storage": "512GB SSD"
  }
}
```

**Response `201 Created`:**
```json
{
  "success": true,
  "data": {
    "product_id": "3f8a2c1d-...",
    "sku": "LAPTOP-001",
    "name": "Pro Laptop 15",
    "status": "DRAFT",
    "price": 1299.99,
    "currency": "USD",
    "created_at": "2026-06-24T10:00:00Z",
    "updated_at": "2026-06-24T10:00:00Z"
  }
}
```

> **Side Effects on Create:** Automatically triggers `POST /api/v1/inventory/initialize` on Inventory Service and `POST /api/v1/search/index` on Search Service. Both calls are fire-and-forget — a failure does not roll back product creation.

#### `PATCH /{product_id}` — Update Product

**Request Body** (all fields optional):
```json
{
  "name": "Updated Name",
  "description": "New description",
  "price": 999.99,
  "status": "ACTIVE"
}
```

---

### 2. Inventory Service — Port 8001

Base URL: `http://localhost:8001/api/v1/inventory`

| Method | Endpoint | Description | Request Body |
|---|---|---|---|
| `GET` | `/{product_id}` | Get stock levels for a product | — |
| `POST` | `/initialize` | Initialize stock at 0 (called by Product Service) | `InitializeInventoryDTO` |
| `POST` | `/restock` | Add available stock (verifies product exists first) | `InventoryTransactionDTO` |
| `POST` | `/reserve` | Move quantity from available → reserved | `InventoryTransactionDTO` |
| `POST` | `/release` | Move quantity from reserved → available (on cancel) | `InventoryTransactionDTO` |
| `POST` | `/deduct` | Permanently remove reserved stock (on ship/complete) | `InventoryTransactionDTO` |

#### `GET /{product_id}` — Get Inventory

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "product_id": "3f8a2c1d-...",
    "available_quantity": 45,
    "reserved_quantity": 5,
    "updated_at": "2026-06-24T11:00:00Z"
  }
}
```

#### `POST /reserve` — Reserve Stock

**Request Body:**
```json
{
  "product_id": "3f8a2c1d-...",
  "quantity": 2
}
```

> All quantity mutations (`reserve`, `release`, `deduct`, `restock`) use a **DynamoDB atomic conditional update** with `ConditionExpression` to prevent negative stock. A `ConflictError (409)` is raised if the condition fails.

---

### 3. Cart Service — Port 8002

Base URL: `http://localhost:8002/api/v1/cart`

> **Authentication:** All endpoints require the `X-User-Id` header to identify the user.

| Method | Endpoint | Description | Request Body | Header |
|---|---|---|---|---|
| `GET` | `/` | Get the current user's cart | — | `X-User-Id` |
| `POST` | `/items` | Add an item to the cart | `AddCartItemDTO` | `X-User-Id` |
| `PATCH` | `/items/{product_id}` | Update quantity of a cart item | `UpdateCartItemDTO` | `X-User-Id` |
| `DELETE` | `/items/{product_id}` | Remove a specific item from cart | — | `X-User-Id` |
| `DELETE` | `/` | Clear entire cart | — | `X-User-Id` |

#### `POST /items` — Add Item

**Request Body:**
```json
{
  "product_id": "3f8a2c1d-...",
  "quantity": 2
}
```

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "user_id": "user_123",
    "items": [
      {
        "product_id": "3f8a2c1d-...",
        "name": "Pro Laptop 15",
        "price": 1299.99,
        "quantity": 2,
        "item_total": 2599.98
      }
    ],
    "cart_total": 2599.98,
    "updated_at": "2026-06-24T11:30:00Z"
  }
}
```

> **Validation on Add:** Checks Inventory Service for available stock before adding. If requested quantity exceeds available stock, returns `400 Bad Request`. Product name and price are fetched live from Product Service and snapshotted into the cart.

> **Cart TTL:** Cart items automatically expire after **7 days** via DynamoDB TTL on the `expiresAt` attribute.

#### `PATCH /items/{product_id}` — Update Item Quantity

**Request Body:**
```json
{ "quantity": 3 }
```

> Setting `quantity` to `0` is equivalent to removing the item.

---

### 4. Payment Service — Port 8003

Base URL: `http://localhost:8003/api/v1/payments`

> **Authentication:** `POST /initiate` requires `X-User-Id` header.

| Method | Endpoint | Description | Request Body |
|---|---|---|---|
| `POST` | `/initiate` | Create a payment intent for an order | `InitiatePaymentDTO` |
| `POST` | `/verify` | Confirm payment success with provider transaction ID | `VerifyPaymentDTO` |
| `POST` | `/webhook` | Handle asynchronous callback from payment gateway | `WebhookPayloadDTO` |

#### `POST /initiate` — Initiate Payment

**Request Body:**
```json
{
  "order_id": "ord_a1b2c3d4e5",
  "amount": 2599.98,
  "currency": "USD",
  "provider": "STRIPE"
}
```

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "payment_id": "pay_abc123def456",
    "order_id": "ord_a1b2c3d4e5",
    "amount": 2599.98,
    "currency": "USD",
    "status": "PENDING",
    "provider": "STRIPE",
    "client_secret": "secret_<mock_token>",
    "created_at": "2026-06-24T12:00:00Z",
    "updated_at": "2026-06-24T12:00:00Z"
  }
}
```

> **Note:** The `client_secret` is a mock token. In production, this is the actual Stripe `PaymentIntent` client secret passed to the frontend SDK.

#### `POST /verify` — Verify Payment

**Request Body:**
```json
{
  "payment_id": "pay_abc123def456",
  "provider_transaction_id": "pi_stripe_xyz"
}
```

#### `POST /webhook` — Payment Gateway Webhook

**Request Body:**
```json
{
  "event_type": "payment_intent.succeeded",
  "provider_transaction_id": "pi_stripe_xyz",
  "status": "succeeded"
}
```

Supported `event_type` values: `payment_intent.succeeded`, `payment_intent.payment_failed`

---

### 5. Order Service — Port 8004

Base URL: `http://localhost:8004/api/v1/orders`

> **Authentication:** `POST /` requires `X-User-Id` header.

| Method | Endpoint | Description | Request Body |
|---|---|---|---|
| `POST` | `/` | Create order from cart (checkout) | — (reads cart via header) |
| `GET` | `/{order_id}` | Get order by ID | — |
| `GET` | `/user/{user_id}` | Get all orders for a user | — |
| `PATCH` | `/{order_id}/status` | Update order status | `OrderStatusUpdateDTO` |
| `PATCH` | `/{order_id}/cancel` | Cancel an order | — |

#### `POST /` — Create Order (Checkout)

No request body required. The service reads the user's cart automatically via the `X-User-Id` header.

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "order_id": "ord_a1b2c3d4e5",
    "user_id": "user_123",
    "items": [
      {
        "product_id": "3f8a2c1d-...",
        "name": "Pro Laptop 15",
        "price": 1299.99,
        "quantity": 2
      }
    ],
    "total_amount": 2599.98,
    "currency": "USD",
    "status": "PENDING_PAYMENT",
    "created_at": "2026-06-24T12:00:00Z",
    "updated_at": "2026-06-24T12:00:00Z"
  }
}
```

> **Checkout Flow:**
> 1. Fetch cart from Cart Service using `X-User-Id`
> 2. Reserve stock for every item via Inventory Service (atomic)
> 3. Persist the Order record with status `PENDING_PAYMENT`
> 4. Clear the user's cart
>
> If stock reservation fails for any item, a `409 Conflict` is returned. Note: partial reservations are not automatically rolled back in the current implementation (a Saga compensating transaction would be needed for full ACID guarantees).

#### `PATCH /{order_id}/status` — Update Status

**Request Body:**
```json
{ "status": "SHIPPED" }
```

Valid statuses: `PENDING_PAYMENT`, `PAID`, `CANCELLED`, `SHIPPED`, `COMPLETED`

> **Inventory side effect:** When status changes to `SHIPPED` or `COMPLETED`, the service calls `POST /deduct` on the Inventory Service to permanently remove the reserved quantity.

#### `PATCH /{order_id}/cancel` — Cancel Order

No request body required.

> Orders with status `SHIPPED` or `COMPLETED` cannot be cancelled (`400 Bad Request`). On successful cancellation, the Inventory Service's `/release` endpoint is called to restore reserved stock to available.

---

### 6. Search Service — Port 8005

Base URL: `http://localhost:8005/api/v1/search`

| Method | Endpoint | Description | Request Body |
|---|---|---|---|
| `GET` | `/` | Search products by keyword | `?q=<query>` (query param) |
| `POST` | `/index` | Index a product (internal, called by Product Service) | `IndexProductDTO` |

#### `GET /?q=laptop` — Search Products

**Response `200 OK`:**
```json
{
  "success": true,
  "data": [
    {
      "product_id": "3f8a2c1d-...",
      "name": "Pro Laptop 15",
      "category": "Electronics",
      "price": 1299.99,
      "image_url": "https://cdn.example.com/img1.jpg"
    }
  ]
}
```

**Response `404 Not Found`** (no results):
```json
{
  "success": false,
  "error": " Products Unavailable "
}
```

> **Search Implementation:** The search index stores a `searchTags` field which is a lowercase concatenation of `name + description + category`. Queries are matched using DynamoDB `Scan` with `FilterExpression contains`. This is suitable for development/small catalogs; production systems should replace this with OpenSearch or Elasticsearch.

#### `POST /index` — Index Product (Internal)

**Request Body:**
```json
{
  "product_id": "3f8a2c1d-...",
  "name": "Pro Laptop 15",
  "description": "High-performance laptop",
  "category": "Electronics",
  "price": 1299.99,
  "images": ["https://cdn.example.com/img1.jpg"]
}
```

> This endpoint is not intended to be called directly by end-users. It is invoked automatically by the Product Service during product creation.

---

## Inter-Service Communication

All inter-service calls are synchronous HTTP using the `requests` library with a 5-second timeout.

| Caller | Called Service | Trigger | Endpoint |
|---|---|---|---|
| Product Service | Inventory Service | Product created | `POST /api/v1/inventory/initialize` |
| Product Service | Search Service | Product created | `POST /api/v1/search/index` |
| Inventory Service | Product Service | Before restock | `GET /api/v1/products/{id}` (existence check) |
| Cart Service | Inventory Service | Add item to cart | `GET /api/v1/inventory/{id}` (stock check) |
| Cart Service | Product Service | Add item to cart | `GET /api/v1/products/{id}` (fetch name & price) |
| Order Service | Cart Service | Checkout | `GET /api/v1/cart/` |
| Order Service | Inventory Service | Checkout | `POST /api/v1/inventory/reserve` |
| Order Service | Inventory Service | Ship/Complete | `POST /api/v1/inventory/deduct` |
| Order Service | Inventory Service | Cancel | `POST /api/v1/inventory/release` |
| Order Service | Cart Service | After order creation | `DELETE /api/v1/cart/` |

### Resilience Strategy

- All inter-service calls are wrapped in `try/except` blocks.
- Product creation does **not** fail if Inventory or Search services are unavailable (fire-and-forget).
- Cart operations fail gracefully if Inventory is down (logs a warning and proceeds).
- Order creation fails explicitly if Cart or Inventory services are unreachable (`DatabaseError → 500`).

---

## DynamoDB Schema

### `Products` Table

| Attribute | Type | Key |
|---|---|---|
| `productId` | String | **Partition Key (PK)** |
| `sku` | String | — |
| `name` | String | — |
| `price` | Number (Decimal) | — |
| `status` | String | — |
| `is_deleted` | Boolean | — (soft delete flag) |
| `created_at` | String (ISO 8601) | — |
| `updated_at` | String (ISO 8601) | — |

### `Inventory` Table

| Attribute | Type | Key |
|---|---|---|
| `productId` | String | **Partition Key (PK)** |
| `availableQuantity` | Number | — |
| `reservedQuantity` | Number | — |
| `updated_at` | String (ISO 8601) | — |

### `Carts` Table

| Attribute | Type | Key |
|---|---|---|
| `userId` | String | **Partition Key (PK)** |
| `items` | Map | — (nested product map) |
| `updatedAt` | String (ISO 8601) | — |
| `expiresAt` | Number | — (**TTL attribute**, 7-day expiry) |

### `Orders` Table

| Attribute | Type | Key |
|---|---|---|
| `orderId` | String | **Partition Key (PK)** |
| `userId` | String | **GSI: `UserIdIndex` (PK)** |
| `items` | List | — |
| `totalAmount` | Number (Decimal) | — |
| `status` | String | — |
| `createdAt` | String (ISO 8601) | — |

### `Payments` Table

| Attribute | Type | Key |
|---|---|---|
| `paymentId` | String | **Partition Key (PK)** |
| `orderId` | String | **GSI: `OrderIdIndex` (PK)** |
| `status` | String | — |
| `provider` | String | — |
| `providerTxId` | String | — |
| `amount` | Number (Decimal) | — |

### `SearchIndex` Table

| Attribute | Type | Key |
|---|---|---|
| `productId` | String | **Partition Key (PK)** |
| `name` | String | — |
| `category` | String | — |
| `price` | Number (Decimal) | — |
| `searchTags` | String | — (lowercase full-text field for `contains` scan) |

---

## Error Handling

Each service uses a custom exception hierarchy that maps to standard HTTP status codes:

```python
AppError (base)
├── NotFoundError       → 404 Not Found
├── BadRequestError     → 400 Bad Request
├── ConflictError       → 409 Conflict
└── DatabaseError       → 500 Internal Server Error
```

All exceptions are caught by a global FastAPI `exception_handler` and returned in the standard error envelope:

```json
{ "success": false, "error": "Descriptive error message" }
```

Pydantic `RequestValidationError` is also caught globally and returns `422 Unprocessable Entity`.

---

## Getting Started

### Prerequisites

- Python 3.10+
- AWS account with DynamoDB access (or AWS CLI configured locally)
- `pip` package manager

### Installation

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd E-Commerce
   ```

2. Create and activate a virtual environment for each service (or a shared one):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies (each service uses the same core stack):
   ```bash
   pip install fastapi uvicorn boto3 requests pydantic
   ```

4. Configure AWS credentials:
   ```bash
   aws configure
   # Enter your AWS Access Key, Secret Key, and region (e.g., ap-south-1)
   ```

### Provision DynamoDB Tables

Run the `setup_dynamo.py` script inside each service directory. These are one-time setup scripts:

```bash
python product-service/setup_dynamo.py
python inventory-service/setup_dynamo.py
python cart-service/setup_dynamo.py       # Also enables TTL on Carts table
python order-service/setup_dynamo.py      # Creates Orders table with UserIdIndex GSI
python payment-service/setup_dynamo.py    # Creates Payments table with OrderIdIndex GSI
python search-service/setup_dynamo.py
```

---

## Running the Services

Each service must be started separately. Open a separate terminal for each:

```bash
# Terminal 1 — Product Service (port 8000)
cd product-service/src
python main.py

# Terminal 2 — Inventory Service (port 8001)
cd inventory-service/src
python main.py

# Terminal 3 — Cart Service (port 8002)
cd cart-service/src
python main.py

# Terminal 4 — Payment Service (port 8003)
cd payment-service/src
python main.py

# Terminal 5 — Order Service (port 8004)
cd order-service/src
python main.py

# Terminal 6 — Search Service (port 8005)
cd search-service/src
python main.py
```

### Interactive API Docs

Once a service is running, visit its auto-generated Swagger UI:

| Service | Swagger URL |
|---|---|
| Product | http://localhost:8000/docs |
| Inventory | http://localhost:8001/docs |
| Cart | http://localhost:8002/docs |
| Payment | http://localhost:8003/docs |
| Order | http://localhost:8004/docs |
| Search | http://localhost:8005/docs |

---

## Design Patterns

### Clean / Layered Architecture
Each service is structured as `Controller → Service → Repository → DynamoDB`. Business logic lives exclusively in the service layer; the controller only handles HTTP concerns; the repository only handles database I/O.

### Repository Pattern
All DynamoDB interactions are abstracted behind repository classes (`DynamoDB*Repository`). Domain models (dataclasses) are decoupled from the storage format via `_to_item()` and `_to_entity()` mapper methods.

### DTO Pattern
Pydantic models separate the external API contract (`*DTO`) from internal domain entities (`*` dataclasses), providing automatic validation, serialization, and OpenAPI schema generation.

### Soft Delete
Products are never physically removed from DynamoDB. Instead, an `is_deleted` flag is set to `True`. All read queries filter out deleted records at the repository layer.

### Atomic Inventory Updates
The Inventory Service uses DynamoDB's `UpdateExpression` with `ConditionExpression` to perform **atomic, race-condition-safe** stock operations. This prevents overselling without requiring distributed locks.

### TTL-based Cart Expiry
Shopping carts automatically expire after 7 days using DynamoDB's native **Time-To-Live (TTL)** feature, eliminating the need for a cleanup job.

### Fire-and-Forget Side Effects
When a product is created, initialization of inventory and search indexing are best-effort. A failure in a downstream service does not roll back the product creation, keeping the Product Service resilient.

### Saga Pattern (Partial)
The Order Service implements a partial Saga: it reserves inventory for all items before committing the order. On cancellation, it releases inventory back. A full compensating transaction (rolling back partial reservations mid-checkout) is noted in the code as a future improvement.

---

## Future Improvements

- **API Gateway / Reverse Proxy** — Unify all services behind a single entry point (e.g., AWS API Gateway, Nginx, or Kong) to handle routing, auth, and rate limiting.
- **Message Queue** — Replace synchronous inter-service calls with an event-driven approach (e.g., AWS SQS/SNS) for better decoupling and resilience.
- **Full-text Search Engine** — Replace the DynamoDB `Scan` approach in the Search Service with OpenSearch or Elasticsearch for scalable, relevance-ranked search.
- **Authentication & Authorization** — Implement JWT-based auth and replace the `X-User-Id` header with a proper token validation middleware.
- **Containerization** — Wrap each service in a Docker container and orchestrate with Docker Compose or Kubernetes.
- **Distributed Tracing** — Add correlation IDs and integrate with AWS X-Ray or OpenTelemetry for end-to-end request tracing across services.
- **Full Saga Compensation** — Implement rollback logic for partial inventory reservations during a failed checkout.
- **Webhook Security** — Add signature verification (e.g., Stripe webhook signature) before processing payment webhook events.

---

*Built with FastAPI · AWS DynamoDB · Python 3*
