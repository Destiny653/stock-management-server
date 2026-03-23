import argparse
import asyncio
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


DEFAULT_STORAGE_CAPACITY_KB = 102400  # 100 MB
DEFAULT_CURRENCY = "XAF"


def build_trial_date() -> datetime:
    return datetime.utcnow() + timedelta(days=30)


def normalize_plan_code(org: Dict[str, Any]) -> Optional[str]:
    return org.get("subscription_plan") or org.get("subscription_plan_id")


def storage_by_plan(plan_code: Optional[str]) -> int:
    if plan_code == "enterprise":
        return 1048576  # 1 GB
    if plan_code in ("professional", "business"):
        return 512000  # 500 MB
    return DEFAULT_STORAGE_CAPACITY_KB


async def run_backfill(apply_changes: bool) -> None:
    load_dotenv(".env")

    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB_NAME", "stockflow_db")
    client = AsyncIOMotorClient(mongodb_url)
    db = client[db_name]

    organizations = db["organizations"]
    plans = db["subscription_plans"]

    org_updates = 0
    plan_updates = 0
    org_total = await organizations.count_documents({})
    plan_total = await plans.count_documents({})

    print(f"Mode: {'APPLY' if apply_changes else 'DRY-RUN'}")
    print(f"Database: {db_name}")
    print(f"Organizations found: {org_total}")
    print(f"Subscription plans found: {plan_total}")

    async for org in organizations.find({}):
        set_fields: Dict[str, Any] = {}
        unset_fields: Dict[str, Any] = {}

        plan_code = normalize_plan_code(org) or "starter"
        if not org.get("subscription_plan"):
            set_fields["subscription_plan"] = plan_code
        if not org.get("subscription_plan_id"):
            set_fields["subscription_plan_id"] = plan_code

        billing_cycle = org.get("billing_cycle") or org.get("subscription_interval") or "monthly"
        if not org.get("billing_cycle"):
            set_fields["billing_cycle"] = billing_cycle
        if not org.get("subscription_interval"):
            set_fields["subscription_interval"] = billing_cycle

        if org.get("storage_capacity_kb") in (None, 0):
            set_fields["storage_capacity_kb"] = storage_by_plan(plan_code)

        if org.get("trial_ends_at") is None:
            set_fields["trial_ends_at"] = build_trial_date()

        if "currency" in org:
            unset_fields["currency"] = ""

        if set_fields or unset_fields:
            org_updates += 1
            print(f"- org {org.get('_id')} -> set={list(set_fields.keys())} unset={list(unset_fields.keys())}")
            if apply_changes:
                update_doc: Dict[str, Any] = {"$set": {**set_fields, "updated_at": datetime.utcnow()}}
                if unset_fields:
                    update_doc["$unset"] = unset_fields
                await organizations.update_one({"_id": org["_id"]}, update_doc)

    async for plan in plans.find({}):
        set_fields: Dict[str, Any] = {}
        if not plan.get("currency"):
            set_fields["currency"] = DEFAULT_CURRENCY
        if plan.get("max_locations") in (None, 0):
            if plan.get("code") == "enterprise":
                set_fields["max_locations"] = 1000000
            elif plan.get("code") in ("professional", "business"):
                set_fields["max_locations"] = 5
            else:
                set_fields["max_locations"] = 1

        if set_fields:
            plan_updates += 1
            print(f"- plan {plan.get('_id')} ({plan.get('code')}) -> set={list(set_fields.keys())}")
            if apply_changes:
                await plans.update_one(
                    {"_id": plan["_id"]},
                    {"$set": {**set_fields, "updated_at": datetime.utcnow()}},
                )

    print(f"\nSummary: organizations to update={org_updates}, plans to update={plan_updates}")
    if not apply_changes:
        print("No data was changed. Re-run with --apply to persist updates.")

    client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill organization billing/subscription fields.")
    parser.add_argument("--apply", action="store_true", help="Persist updates to the database")
    args = parser.parse_args()

    asyncio.run(run_backfill(apply_changes=args.apply))


if __name__ == "__main__":
    main()
