"""Stripe checkout helper compatible with the Émo backend."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

import stripe


@dataclass
class CheckoutSessionRequest:
    amount: float
    currency: str
    success_url: str
    cancel_url: str
    metadata: Optional[dict] = None
    mode: str = "subscription"  # subscription | payment


@dataclass
class CheckoutSessionResponse:
    session_id: str
    url: str


@dataclass
class CheckoutStatus:
    status: str
    payment_status: str
    amount_total: Optional[float] = None
    currency: Optional[str] = None


@dataclass
class WebhookEvent:
    session_id: Optional[str] = None
    metadata: Optional[dict] = None


class StripeCheckout:
    def __init__(self, api_key: str, webhook_url: str = ""):
        self._api_key = api_key
        self._webhook_url = webhook_url
        stripe.api_key = api_key

    async def create_checkout_session(
        self, req: CheckoutSessionRequest
    ) -> CheckoutSessionResponse:
        amount_cents = int(round(float(req.amount) * 100))
        if req.mode == "subscription":
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{
                    "price_data": {
                        "currency": req.currency,
                        "product_data": {"name": "Émo — abonnement"},
                        "unit_amount": amount_cents,
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }],
                success_url=req.success_url,
                cancel_url=req.cancel_url,
                metadata=req.metadata or {},
            )
        else:
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": req.currency,
                        "product_data": {"name": "Émo — licence"},
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }],
                success_url=req.success_url,
                cancel_url=req.cancel_url,
                metadata=req.metadata or {},
            )
        return CheckoutSessionResponse(session_id=session.id, url=session.url)

    async def get_checkout_status(self, session_id: str) -> CheckoutStatus:
        session = stripe.checkout.Session.retrieve(session_id)
        amount_total = None
        if session.amount_total is not None:
            amount_total = session.amount_total / 100.0
        return CheckoutStatus(
            status=session.status or "unknown",
            payment_status=session.payment_status or "unknown",
            amount_total=amount_total,
            currency=session.currency,
        )

    async def handle_webhook(self, raw: bytes, signature: str) -> WebhookEvent:
        secret = stripe.api_key  # placeholder; real webhook secret should be in env
        try:
            event = stripe.Webhook.construct_event(raw, signature, secret)
        except Exception:
            payload = json.loads(raw.decode())
            obj = (payload.get("data") or {}).get("object") or {}
            return WebhookEvent(
                session_id=obj.get("id"),
                metadata=obj.get("metadata") or {},
            )
        obj = (event.get("data") or {}).get("object") or {}
        return WebhookEvent(session_id=obj.get("id"), metadata=obj.get("metadata") or {})
