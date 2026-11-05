"""Responsible for listing customers and showing one customer, limited to what the agent may see."""
from fastapi import APIRouter

from app.deps import CurrentAgent, Db
from app.models.customer import CustomerDetail, CustomerListItem
from app.repos import customers as customer_repo
from app.services.access import audit, auth
from app.services.customers import renewal

router = APIRouter()


# Lists the customers the agent may see. A supervisor sees all of them.
# req: token / res: [{ customer_id, name, language, consent, renewal_status }] / errors: 401
@router.get("/customers", response_model=list[CustomerListItem])
def list_customers(agent: CurrentAgent, db: Db):
    # Each customer comes with the renewal state of the policies this agent may see.
    return [
        {**customer, "renewal_status": renewal.customer_renewal_status(policies)}
        for customer, policies in auth.visible_customers(db, agent)
    ]


# Returns one customer with their policies and interactions, and audits the view.
# req: token / res: { customer, policies, interactions } / errors: 401, 403, 404
@router.get("/customers/{customer_id}", response_model=CustomerDetail)
def get_customer(customer_id: str, agent: CurrentAgent, db: Db):
    customer, policies = auth.load_customer(db, agent, customer_id)
    audit.log(db, agent.agent_id, "customer_viewed", {"customer_id": customer_id})
    return {"customer": customer, "policies": policies, "interactions": customer_repo.interactions_for(db, customer_id)}
