from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.executive_dashboard import (
    ExecutiveDashboardResponse,
)
from app.services.executive_dashboard_service import (
    build_executive_dashboard,
)


router = APIRouter(
    prefix="/api/executive-dashboard",
    tags=["Executive Dashboard"],
)


@router.get(
    "",
    response_model=ExecutiveDashboardResponse,
)
def get_executive_dashboard(
    database: Session = Depends(get_db),
):
    return build_executive_dashboard(
        database
    )
