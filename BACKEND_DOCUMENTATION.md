# 📦 StockFlow Backend Documentation

## 1. Architectural Overview
The backend is built with **FastAPI** (Python), using **MongoDB** as the primary database through the **Beanie ODM** (Object Document Mapper). 

The system follows a **Multi-Tenant (SaaS)** architecture where every piece of data (Products, Users, Warehouses) is isolated by an `organization_id`.

---

## 2. Core Data Flow (Step-by-Step)

### Step 1: The Organization & Multi-Tenancy Layer
The **Organization** is the root entity. 
*   **Process**: When a new company signs up, an `Organization` record is created.
*   **Isolation**: Every subsequent record created (Users, Products, etc.) includes an `organization_id`. The backend filters all queries by this ID to ensure one company never sees another company's data.

### Step 2: The Global Search System ("Google-like")
The backend provides a unified `/search/` endpoint that allows users to find data across the entire platform from a single query.
*   **Entities Searched**: Products (Name, Category, SKU, Description), Vendors (Name, Store Name), and Suppliers.
*   **Multi-tenancy**: Results are automatically filtered based on the user's `organization_id`.
*   **Internationalization**: The search is case-insensitive and supports Unicode, meaning it will correctly match text in English, French, Spanish, or any other language stored in your database.
*   **Relevance**: Results are sorted so that items starting with your search term appear first.

### Step 3: The Decoupled Location System
Unlike traditional systems where addresses are typed into every form, we use a standalone **Location** entity.
*   **Process**: Instead of saving `"123 Street"` inside a Product or Warehouse, we save a `location_id`.
*   **Benefit**: If a warehouse moves or an organization changes headquarters, you update **one** Location record, and every linked entity is automatically updated across the system.

### Step 3: Product & Variant Management
Products are managed with a "Base + Variant" logic.
*   **Base Product**: Stores common info (Category, Name, Description, Brand).
*   **Variants**: A nested list inside the product storing specific configurations (e.g., Laptop -> Color: Silver, RAM: 16GB). This is where the **SKU**, **Price**, and **Stock Levels** live.

### Step 4: The Procurement Flow (Purchase Orders)
When stock is needed:
1.  **Manager** creates a `PurchaseOrder` linked to a `Supplier`.
2.  The PO enters a `pending` state.
3.  Once **Approved**, the items are expected at a specific `Warehouse`.
4.  Upon **Receive**, the system automatically triggers a **Stock Movement**.

### Step 5: The Sales & Movement Audit Trail
Every time stock changes (Sale, Return, or Adjustment), the system **must** record a `StockMovement`.
*   **Entry**: Product ID, Quantity Change, Type (In/Out/Transfer), and Reason.
*   **Balance**: The Current Stock in the Product Variant is updated based on this movement. This creates a bulletproof audit trail for accountants.

---

## 3. Security & Authentication
*   **JWT Tokens**: Secure stateless authentication using OAuth2.
*   **Login Parameters**: The login endpoint (`/auth/login/access-token`) follows the OAuth2 standard. Here is what the parameters mean:
    *   `username` (**Required**): Your unique identifier (username or email).
    *   `password` (**Required**): Your secret password.
    *   `grant_type`: Set this to `password`. It tells the server you are using the password-based login flow.
    *   `scope`: (Optional) Used to request specific levels of access. Usually left blank in this application.
    *   `client_id`: (Optional) Used to identify which application is logging in (e.g., "Web-App" vs "Mobile-App").
    *   `client_secret`: (Optional) A secret key for the application itself, used alongside `client_id`.
*   **Role-Based Access Control (RBAC)**:
    *   `OWNER`: Full access to organization settings and billing.
    *   `ADMIN`: Manage users and organization-wide data.
    *   `MANAGER`: Manage inventory, warehouses, and orders.
    *   `STAFF`: Perform daily sales and stock-takes.
    *   `VENDOR`: Access only their specific store's sales and products.

---

## 4. Entity Relationship Summary

| Entity | Purpose | Key Relation |
| :--- | :--- | :--- |
| **User** | System Access | `organization_id` |
| **Location** | Geographical Data | (Referenced by many) |
| **Product** | Inventory Catalog | `location_id`, `organization_id` |
| **Warehouse**| Physical Storage | `location_id`, `organization_id` |
| **Vendor** | Store Owner | `user_id`, `organization_id` |
| **Alert** | Inventory Health | `product_id`, `organization_id` |

---

## 5. How to Interact with the API
The backend automatically generates an interactive documentation page. 
1.  **Start Server**: `uvicorn app.main:app --reload`
2.  **Access Docs**: Navigate to `http://localhost:8000/docs`
3.  **Explore**: You can test every endpoint (CRUD) directly from the browser using the **Try it out** button.

---

## 6. Development Status ✅
*   **Persistence**: Handled by MongoDB and Beanie ODM.
*   **Validation**: Handled by Pydantic (ensures data is clean before saving).
*   **Async Operations**: The backend is fully asynchronous, allowing it to handle thousands of concurrent stock updates.

**Note for Developers**: When creating new features, always ensure the `organization_id` is passed to the `beanie` query to maintain data privacy.
