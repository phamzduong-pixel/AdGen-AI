from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.content_tools import ContentEvaluationRequest
from app.schemas.content_tools import ContentEvaluationResponse
from app.schemas.content_tools import ContentVariantRequest
from app.schemas.content_tools import ContentVariantResponse
from app.services.content_evaluation_service import evaluate_content_service
from app.services.content_variant_service import generate_variants_service


router = APIRouter(prefix="/content", tags=["Content tools"])


@router.post("/evaluate", response_model=ContentEvaluationResponse)
def evaluate_content(
    data: ContentEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return evaluate_content_service(data=data, db=db, current_user=current_user)


@router.post("/generate-variants", response_model=ContentVariantResponse)
def generate_variants(
    data: ContentVariantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return generate_variants_service(data=data, db=db, current_user=current_user)
