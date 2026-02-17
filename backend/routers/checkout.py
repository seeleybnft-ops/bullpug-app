"""Checkout and product routes for Stripe integration."""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import uuid
import os
import logging
from datetime import datetime, timezone
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest
)

from utils.database import db


router = APIRouter(tags=["checkout"])
logger = logging.getLogger(__name__)

stripe_api_key = os.environ.get('STRIPE_API_KEY')

# Products configuration
PRODUCTS = {
    "guardian-plush": {
        "id": "guardian-plush",
        "name": "Bullpug Guardian Plushie",
        "description": "The ultimate cosmic guardian in plush form! Cape, bull horns, and glow-in-the-dark eyes.",
        "price": 29.99,
        "image_url": "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/7x0weeyi_download%20-%202026-02-17T063439.078.png",
        "category": "plushie"
    },
    "space-pug-plush": {
        "id": "space-pug-plush",
        "name": "Cyber Bullpug Plushie",
        "description": "Bullpug in full cyber armor! LED visor included. Ready to patrol the blockchain.",
        "price": 34.99,
        "image_url": "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/kynwxxke_image%20-%202026-02-17T063523.593.jpg",
        "category": "plushie"
    },
    "mini-pug-pack": {
        "id": "mini-pug-pack",
        "name": "Mini Bullpug Pack (Set of 3)",
        "description": "Three adorable mini Bullpugs: Guardian, Cosmic, and Golden Bull variants.",
        "price": 19.99,
        "image_url": "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/5w17pptk__eda5997e-289f-4f2c-916b-329017a171d6.jfif",
        "category": "plushie"
    },
    "cape-edition": {
        "id": "cape-edition",
        "name": "Bullpug Maid Edition (XL)",
        "description": "Deluxe oversized Bullpug in maid outfit. The ultimate collector's item with real fabric accessories.",
        "price": 49.99,
        "image_url": "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/2sae826h_25.10.2024_17.06.12_REC.png",
        "category": "plushie"
    }
}


class CheckoutRequest(BaseModel):
    product_id: str
    quantity: int = 1
    origin_url: str


@router.get("/products")
async def get_products():
    """Get all available products."""
    return {"products": list(PRODUCTS.values())}


@router.post("/checkout/session")
async def create_checkout_session(request: Request, data: CheckoutRequest):
    """Create a Stripe checkout session."""
    if data.product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    product = PRODUCTS[data.product_id]
    amount = product["price"] * data.quantity

    success_url = f"{data.origin_url}/shop?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{data.origin_url}/shop"

    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)

    checkout_req = CheckoutSessionRequest(
        amount=float(amount), currency="usd",
        success_url=success_url, cancel_url=cancel_url,
        metadata={"product_id": data.product_id, "product_name": product["name"], "quantity": str(data.quantity)}
    )
    session = await stripe_checkout.create_checkout_session(checkout_req)

    tx = {
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "amount": float(amount),
        "currency": "usd",
        "product_id": data.product_id,
        "quantity": data.quantity,
        "payment_status": "initiated",
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.payment_transactions.insert_one(tx)
    return {"url": session.url, "session_id": session.session_id}


@router.get("/checkout/status/{session_id}")
async def get_checkout_status(request: Request, session_id: str):
    """Get checkout session status."""
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    status = await stripe_checkout.get_checkout_status(session_id)
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {
            "payment_status": status.payment_status,
            "status": "completed" if status.payment_status == "paid" else status.status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    return {
        "status": status.status,
        "payment_status": status.payment_status,
        "amount_total": status.amount_total,
        "currency": status.currency
    }


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        if webhook_response and webhook_response.session_id:
            await db.payment_transactions.update_one(
                {"session_id": webhook_response.session_id},
                {"$set": {
                    "payment_status": webhook_response.payment_status,
                    "status": "completed" if webhook_response.payment_status == "paid" else "failed",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error"}
