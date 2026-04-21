import requests

# Replace with your actual localhost URL if different
BASE_URL = "http://localhost:8000/api/v1"


def simulate_webhook(transaction_id, status="SUCCESS"):
    payload = {
        "transaction_id": transaction_id,
        "status": status,
        "amount": 5000,
        "currency": "XAF",
    }

    print(f"Simulating PayUnit webhook for transaction: {transaction_id} with status: {status}")
    response = requests.post(f"{BASE_URL}/payments/webhook", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")


if __name__ == "__main__":
    tx = input("Enter the transaction_id to simulate (from the UI or API): ")
    simulate_webhook(tx)
