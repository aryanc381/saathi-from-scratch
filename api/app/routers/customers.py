"""Responsible for listing customers and showing one customer, limited to what the agent may see."""
from fastapi import APIRouter

from app.deps import CurrentAgent, Db
from app.models.customer import CustomerDetail, CustomerListItem
from app.repos import customers as customer_repo
from app.services import audit, auth, policy

router = APIRouter()


# Lists the customers the agent may see. A supervisor sees all of them.
# req: token / res: [{ customer_id, name, language, consent, renewal_status }] / errors: 401
@router.get("/customers", response_model=list[CustomerListItem])
def list_customers(agent: CurrentAgent, db: Db):
    if agent.role == "supervisor":
        customers = customer_repo.list_all(db)
    else:
        customers = customer_repo.list_by_agent(db, agent.agent_id)
    items = []
    for customer in customers:
        policies = customer_repo.policies_for(db, customer["customer_id"])
        if auth.can_access(agent, customer, policies):
            items.append({**customer, "renewal_status": policy.customer_renewal_status(policies)})
    return items


# Returns one customer with their policies and interactions, and audits the view.
# req: token / res: { customer, policies, interactions } / errors: 401, 403, 404
@router.get("/customers/{customer_id}", response_model=CustomerDetail)
def get_customer(customer_id: str, agent: CurrentAgent, db: Db):
    customer, policies = auth.load_customer(db, agent, customer_id)
    audit.log(db, agent.agent_id, "customer_viewed", {"customer_id": customer_id})
    return {"customer": customer, "policies": policies, "interactions": customer_repo.interactions_for(db, customer_id)}
