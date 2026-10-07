from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.services.external_retrieval.multi_platform import MultiPlatformRetrievalService
from app.schemas.trend_report import (
    TrendReportCreate,
    TrendReportResponse,
    TrendReportRetrievalRequest,
)
from app.schemas.product_trust import (
    ProductTrustSummaryResponse,
    SourcePolicyResponse,
    SourcePolicyUpsert,
)
from app.services.trend_report_service import (
    create_trend_report_service,
    delete_trend_report_service,
    get_owned_trend_report,
    get_trend_report_service,
    list_trend_reports_service,
    persist_multi_platform_report,
)
from app.services.product_trust.report_service import (
    list_source_policies,
    persist_report_trust_snapshot,
    upsert_source_policy,
)


router = APIRouter(prefix="/trend-reports", tags=["Trend Radar"])

def get_multi_platform_retrieval_service() -> MultiPlatformRetrievalService:
    """Return the safe default; deployments inject configured collectors."""
    return MultiPlatformRetrievalService([])


@router.post("/retrieve", response_model=TrendReportResponse, status_code=201)
def retrieve_trend_report(
    data: TrendReportRetrievalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    retrieval_service: MultiPlatformRetrievalService = Depends(
        get_multi_platform_retrieval_service
    ),
):
    return persist_multi_platform_report(
        query=data.query,
        retrieval_service=retrieval_service,
        db=db,
        current_user=current_user,
        request_id=data.request_id,
        conversation_id=data.conversation_id,
        source_message_id=data.source_message_id,
        refresh=data.refresh,
        max_age_days=data.max_age_days,
    )




@router.post("", response_model=TrendReportResponse, status_code=201)
def create_trend_report(
    data: TrendReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_trend_report_service(data, db, current_user)


@router.get("", response_model=list[TrendReportResponse])
def list_trend_reports(
    source_message_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_trend_reports_service(
        db=db,
        current_user=current_user,
        source_message_id=source_message_id,
    )


def _serialize_source_policy(policy) -> SourcePolicyResponse:
    return SourcePolicyResponse(
        host=policy.host,
        decision=policy.decision,
        note=policy.note,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@router.delete("/{report_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trend_report(
    report_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_trend_report_service(report_key, db, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/source-policies', response_model=list[SourcePolicyResponse])
def get_source_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return [_serialize_source_policy(item) for item in list_source_policies(db, current_user)]


@router.put('/source-policies', response_model=SourcePolicyResponse)
def put_source_policy(
    data: SourcePolicyUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        policy = upsert_source_policy(data, db, current_user)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _serialize_source_policy(policy)


@router.get('/{report_key}/trust', response_model=ProductTrustSummaryResponse)
def get_product_trust_summary(
    report_key: str,
    mode: str = Query(default='all_evidence', pattern='^(all_evidence|verified_only)$'),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = get_owned_trend_report(report_key, db, current_user)
    summary = persist_report_trust_snapshot(
        report,
        db,
        current_user,
        mode=mode,
    )
    db.commit()
    return summary


@router.get("/{report_key}", response_model=TrendReportResponse)
def get_trend_report(
    report_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_trend_report_service(report_key, db, current_user)
