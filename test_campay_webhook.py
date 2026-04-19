import requests
import json

# Replace with your actual locahost URL if different
BASE_URL = "http://localhost:8000/api/v1"

def simulate_webhook(reference, status="SUCCESSFUL"):
    payload = {
        "reference": reference,
        "status": status,
        "amount": 29.0, # Match the plan price
        "currency": "XAF",
        "external_reference": "test_org_id"
    }
    
    print(f"Simulating webhook for reference: {reference} with status: {status}")
    response = requests.post(f"{BASE_URL}/campay/webhook", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    # You would need a valid reference from a real 'collect' call or just mock one
    ref = input("Enter the payment reference to simulate (from the UI or API): ")
    simulate_webhook(ref)
