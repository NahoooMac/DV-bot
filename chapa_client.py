import os
import logging
import httpx
from typing import Dict, Any, Optional
from config import CHAPA_SECRET_KEY, CHAPA_API_URL, DV_SERVICE_FEE, logger


async def initialize_chapa_transaction(
    user_id: int,
    email: str,
    first_name: str,
    last_name: str,
    phone_number: str = "",
    amount: int = DV_SERVICE_FEE,
    tx_ref: Optional[str] = None
) -> Dict[str, Any]:
    """
    Initializes a payment transaction with Chapa.
    Returns a dict with {"success": bool, "checkout_url": str, "tx_ref": str, "error": str}.
    """
    secret_key = os.environ.get("CHAPA_SECRET_KEY", CHAPA_SECRET_KEY).strip()
    if not secret_key:
        return {
            "success": False,
            "error": "CHAPA_SECRET_KEY is not configured."
        }

    if not tx_ref:
        import time
        tx_ref = f"dv-{user_id}-{int(time.time())}"

    # Sanitized customer information
    customer_email = email.strip() if (email and "@" in email and "." in email) else f"applicant_{user_id}@gmail.com"
    customer_first = first_name.strip() if first_name else "Applicant"
    customer_last = last_name.strip() if last_name else "DV"

    payload = {
        "amount": str(amount),
        "currency": "ETB",
        "email": customer_email,
        "first_name": customer_first,
        "last_name": customer_last,
        "tx_ref": tx_ref,
        "customization": {
            "title": "DV 2026 Application Fee",
            "description": f"Service fee for DV application submission (350 ETB)"
        }
    }

    if phone_number:
        clean_phone = phone_number.strip().replace(" ", "").replace("-", "")
        if clean_phone.startswith("+251"):
            clean_phone = "0" + clean_phone[4:]
        elif clean_phone.startswith("251"):
            clean_phone = "0" + clean_phone[3:]
        # Only attach if valid 10 digits starting with 09 or 07
        if len(clean_phone) == 10 and clean_phone.startswith(("09", "07")) and clean_phone.isdigit():
            payload["phone_number"] = clean_phone

    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json"
    }

    url = f"{CHAPA_API_URL}/transaction/initialize"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            res_json = resp.json()

            # If failed due to phone number, retry once without phone_number
            if (resp.status_code != 200 or res_json.get("status") != "success") and "phone" in str(res_json).lower() and "phone_number" in payload:
                payload.pop("phone_number", None)
                resp = await client.post(url, json=payload, headers=headers)
                res_json = resp.json()

            if resp.status_code == 200 and res_json.get("status") == "success":
                data = res_json.get("data", {})
                checkout_url = data.get("checkout_url")
                logger.info(f"Chapa transaction initialized for user {user_id}: {tx_ref}")
                return {
                    "success": True,
                    "checkout_url": checkout_url,
                    "tx_ref": tx_ref
                }
            else:
                err_msg = res_json.get("message") or f"HTTP {resp.status_code}"
                logger.error(f"Chapa initialization failed for user {user_id}: {err_msg}")
                return {
                    "success": False,
                    "error": str(err_msg)
                }
    except Exception as e:
        logger.error(f"Exception initializing Chapa transaction for {user_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


async def verify_chapa_transaction(tx_ref: str) -> Dict[str, Any]:
    """
    Verifies a transaction with Chapa by tx_ref.
    Returns {"success": bool, "status": str, "data": dict, "error": str}.
    """
    secret_key = os.environ.get("CHAPA_SECRET_KEY", CHAPA_SECRET_KEY).strip()
    if not secret_key:
        return {
            "success": False,
            "error": "CHAPA_SECRET_KEY is not configured."
        }

    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json"
    }

    url = f"{CHAPA_API_URL}/transaction/verify/{tx_ref}"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=headers)
            res_json = resp.json()

            if resp.status_code == 200 and res_json.get("status") == "success":
                data = res_json.get("data", {})
                # Chapa returns data.status which can be "success", "pending", or "failed"
                tx_status = data.get("status", "").lower()
                is_paid = (tx_status == "success")
                logger.info(f"Chapa verification for {tx_ref}: status={tx_status}")
                return {
                    "success": is_paid,
                    "status": tx_status,
                    "data": data
                }
            else:
                err_msg = res_json.get("message") or f"HTTP {resp.status_code}"
                logger.warning(f"Chapa verification failed for {tx_ref}: {err_msg}")
                return {
                    "success": False,
                    "status": "failed",
                    "error": str(err_msg)
                }
    except Exception as e:
        logger.error(f"Exception verifying Chapa transaction {tx_ref}: {e}", exc_info=True)
        return {
            "success": False,
            "status": "error",
            "error": str(e)
        }
