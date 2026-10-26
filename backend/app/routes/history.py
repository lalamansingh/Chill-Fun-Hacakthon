from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Analysis, Image, User
from app.schemas import DashboardStats, HistoryPage, TrendPoint, VerdictCounts
from app.services.serializers import history_item

router = APIRouter(prefix="/api", tags=["history"])

VERDICTS = ("authentic", "manipulated", "deepfake", "ai_generated")


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("/history", response_model=HistoryPage)
def history(
    q: Optional[str] = Query(default=None, max_length=255),
    verdict: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HistoryPage:
    conds = [Analysis.user_id == user.id]
    if q and q.strip():
        conds.append(Image.original_filename.ilike(f"%{_escape_like(q.strip())}%", escape="\\"))
    if verdict and verdict.strip() and verdict.strip().lower() != "all":
        v = verdict.strip().lower()
        if v not in VERDICTS:
            raise HTTPException(status_code=400, detail=f"verdict must be one of: {', '.join(VERDICTS)}")
        conds.append(Analysis.verdict == v)

    base = select(Analysis, Image).join(Image, Analysis.image_id == Image.id).where(*conds)
    total = db.scalar(
        select(func.count()).select_from(Analysis).join(Image, Analysis.image_id == Image.id).where(*conds)
    ) or 0
    rows = db.execute(
        base.order_by(Analysis.created_at.desc(), Analysis.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return HistoryPage(
        items=[history_item(a, i) for a, i in rows], total=total, page=page, page_size=page_size
    )


def _utc_date(dt: datetime):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date()


@router.get("/dashboard/stats", response_model=DashboardStats)
def dashboard_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DashboardStats:
    total_images = db.scalar(select(func.count(Image.id)).where(Image.user_id == user.id)) or 0
    total_analyses = db.scalar(select(func.count(Analysis.id)).where(Analysis.user_id == user.id)) or 0
    avg = db.scalar(select(func.avg(Analysis.authenticity_score)).where(Analysis.user_id == user.id))

    by_verdict = VerdictCounts()
    for v, n in db.execute(
        select(Analysis.verdict, func.count(Analysis.id)).where(Analysis.user_id == user.id).group_by(Analysis.verdict)
    ).all():
        if v in VERDICTS:
            setattr(by_verdict, v, int(n))

    # 7-day trend (today incl.), bucketed in Python so it works the same on SQLite and Postgres.
    today = datetime.now(timezone.utc).date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    buckets = {d: TrendPoint(date=d.isoformat()) for d in days}
    since = datetime.combine(days[0], datetime.min.time(), tzinfo=timezone.utc) - timedelta(days=1)
    for v, created in db.execute(
        select(Analysis.verdict, Analysis.created_at).where(
            Analysis.user_id == user.id, Analysis.created_at >= since
        )
    ).all():
        d = _utc_date(created)
        if d in buckets and v in VERDICTS:
            setattr(buckets[d], v, getattr(buckets[d], v) + 1)

    recent_rows = db.execute(
        select(Analysis, Image)
        .join(Image, Analysis.image_id == Image.id)
        .where(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
        .limit(5)
    ).all()

    return DashboardStats(
        total_images=total_images,
        total_analyses=total_analyses,
        avg_authenticity_score=round(float(avg), 2) if avg is not None else 0.0,
        by_verdict=by_verdict,
        trend=[buckets[d] for d in days],
        recent=[history_item(a, i) for a, i in recent_rows],
    )
