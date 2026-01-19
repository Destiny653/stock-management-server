# Swagger API Setup Guide

This guide provides the necessary data and sequences to set up your environment from scratch using Swagger UI (usually at `http://localhost:8000/docs`).

## Step 1: Register a New Admin User
**Endpoint:** `POST /auth/register`

Use this to create your first administrative user.

```json
{
  "email": "admin@example.com",
  "username": "admin",
  "password": "strongpassword123",
  "first_name": "Admin",
  "last_name": "User",
  "role": "admin",
  "user_type": "admin"
}
```

---

## Step 2: Login to Get Access Token
**Endpoint:** `POST /auth/login/access-token`

In Swagger, click **"Try it out"**, enter your credentials in the form fields.
- **username**: `admin`
- **password**: `strongpassword123`

Copy the `access_token` from the response. 
**Note:** You can also click the **"Authorize"** button at the top of Swagger and paste the token there to authorize all subsequent requests.

---

## Step 3: Create an Organization
**Endpoint:** `POST /api/v1/organizations/`

*Requirement:* You must be logged in as an `admin` or `owner`.

```json
{
  "name": "Global Logistics Corp",
  "code": "GLC-001",
  "description": "Main logistics and inventory organization",
  "email": "contact@globallogistics.com",
  "website": "https://globallogistics.com",
  "subscription_plan": "business"
}
```

**IMPORTANT:** Take note of the `"id"` returned in the response (e.g., `65a...`). You will need this for the next step.

---

---

## Step 4: Create a Location
**Endpoint:** `POST /api/v1/locations/`

Create a location that will be linked to your vendor or warehouse.

```json
{
  "name": "Downtown Store Location",
  "address": "123 Business Ave",
  "city": "Yaoundé",
  "state": "Centre",
  "postal_code": "00000",
  "country": "Cameroon",
  "latitude": 3.848,
  "longitude": 11.502
}
```

**IMPORTANT:** Take note of the `"id"` returned (e.g., `65b...`). Use this as `location_id`.

---

## Step 5: Create a Vendor
**Endpoint:** `POST /api/v1/vendors/`

*Requirement:* Use the `organization_id` and `location_id`.

```json
{
  "organization_id": "REPLACE_WITH_ORGANIZATION_ID",
  "name": "Elite Supplies",
  "owner_name": "Samuel Jackson",
  "email": "sam@elitesupplies.com",
  "phone": "+237 600000000",
  "store_name": "Elite Downtown",
  "location_id": "REPLACE_WITH_LOCATION_ID",
  "status": "active",
  "subscription_plan": "standard"
}
```

---

## Step 6: Create a Warehouse
**Endpoint:** `POST /api/v1/warehouses/`

*Requirement:* Use the `organization_id` and optionally a `location_id`.

```json
{
  "organization_id": "REPLACE_WITH_ORGANIZATION_ID",
  "name": "Central Distribution Center",
  "code": "WH-CDC-01",
  "location_id": "REPLACE_WITH_LOCATION_ID",
  "manager": "John Doe",
  "capacity": 50000,
  "status": "active"
}
```

---

## Step 7: Verify Setup
**Endpoint:** `GET /api/v1/vendors/` or `GET /api/v1/warehouses/`

Query Parameters:
- **organization_id**: Your Organization ID
