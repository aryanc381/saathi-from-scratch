"""Responsible for the customer, policy and interaction shapes returned by the customer routes."""
from datetime import date

from pydantic import BaseModel


# A customer's own details.
class Customer(BaseModel):
    customer_id: str
    name: str
    phone: str
    language: str
    consent: bool


# One policy of a customer.
class Policy(BaseModel):
    policy_id: str
    customer_id: str
    product: str
    tier: str
    annual_premium_inr: int
    renewal_date: date
    status: str


# One past conversation with a customer.
class Interaction(BaseModel):
    interaction_id: str
    customer_id: str
    date: date
    channel: str
    text: str


# One row of GET /customers.
class CustomerListItem(BaseModel):
    customer_id: str
    name: str
    language: str
    consent: bool
    renewal_status: str


# Response of GET /customers/{id}.
class CustomerDetail(BaseModel):
    customer: Customer
    policies: list[Policy]
    interactions: list[Interaction]
