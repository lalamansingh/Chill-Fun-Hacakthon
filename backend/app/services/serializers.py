"""ORM -> response schema conversion. All file URLs are relative /api/... paths."""
from typing import Any

from app.models import Analysis, Image, Restoration, User
from app.schemas import AnalysisOut, HistoryItem, ImageOut, RestorationOut, UserOut
from app.services import storage

_STRIP_KEYS = ("heatmap_path", "ela_path")


def user_out(u: User) -> UserOut:
    return UserOut(id=u.id, name=u.name, email=u.email, created_at=u.created_at)


def image_out(img: Image) -> ImageOut:
    return ImageOut(
        id=img.id,
        original_filename=img.original_filename,
        mime_type=img.mime_type,
        size_bytes=img.size_bytes,
        width=img.width,
        height=img.height,
        uploaded_at=img.uploaded_at,
        url=f"/api/images/{img.id}/file",
    )


def restoration_out(r: Restoration) -> RestorationOut:
    return RestorationOut(
        id=r.id,
        analysis_id=r.analysis_id,
        method=r.method,
        note=r.note,
        created_at=r.created_at,
        url=f"/api/restorations/{r.id}/file",
    )


def public_result(result: dict[str, Any] | None) -> dict[str, Any]:
    return {k: v for k, v in (result or {}).items() if k not in _STRIP_KEYS}


def analysis_out(a: Analysis) -> AnalysisOut:
    return AnalysisOut(
        id=a.id,
        image_id=a.image_id,
        verdict=a.verdict,
        authenticity_score=a.authenticity_score,
        confidence=a.confidence,
        created_at=a.created_at,
        processing_ms=a.processing_ms,
        result=public_result(a.result_json),
        image=image_out(a.image),
        heatmap_url=f"/api/analyses/{a.id}/heatmap" if storage.existing(a.heatmap_path) else None,
        ela_url=f"/api/analyses/{a.id}/ela" if storage.existing(a.ela_path) else None,
        report_url=f"/api/reports/{a.id}/pdf",
        restorations=[restoration_out(r) for r in a.restorations],
    )


def history_item(a: Analysis, img: Image) -> HistoryItem:
    return HistoryItem(
        analysis_id=a.id,
        image_id=img.id,
        original_filename=img.original_filename,
        verdict=a.verdict,
        authenticity_score=a.authenticity_score,
        confidence=a.confidence,
        created_at=a.created_at,
        thumbnail_url=f"/api/images/{img.id}/file",
    )
