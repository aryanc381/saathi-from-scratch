"""Responsible for the Renewal Radar worklist: which of the agent's customers are most likely to renew."""
from fastapi import APIRouter

from app.deps import AppSettings, CurrentAgent, Db
from app.models.radar import RadarRow
from app.services.customers import radar

router = APIRouter()


# Returns the top customers the agent may see who can still renew, best score first.
# req: token / res: [{ customer_id, name, days_to_renewal, score, top_factors, status }] / errors: 401, 503
@router.get("/radar/worklist", response_model=list[RadarRow])
def radar_worklist(agent: CurrentAgent, db: Db, settings: AppSettings):
    return radar.worklist(db, settings, agent)
