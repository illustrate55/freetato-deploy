"""Просмотр сдач (поллинг + история)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.submission import Submission
from app.models.user import User
from app.schemas.submission import SubmissionListResponse, SubmissionPublic

router = APIRouter()


@router.get("/submissions/{submission_id}", response_model=SubmissionPublic, summary="Состояние сдачи")
async def get_submission(
    submission_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionPublic:
    sub = await db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сдача не найдена")
    if sub.user_id != user.id and user.role not in ("teacher", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Чужая сдача")
    return SubmissionPublic.model_validate(sub)


@router.get("/submissions/my", response_model=SubmissionListResponse, summary="Мои сдачи")
async def my_submissions(
    task_id: int | None = None,
    submission_status: str | None = Query(default=None, alias="status"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionListResponse:
    q = select(Submission).where(Submission.user_id == user.id)
    if task_id:
        q = q.where(Submission.task_id == task_id)
    if submission_status:
        q = q.where(Submission.status == submission_status)
    rows = (await db.execute(q.order_by(Submission.submitted_at.desc()))).scalars().all()
    return SubmissionListResponse(
        items=[SubmissionPublic.model_validate(s) for s in rows],
        total=len(rows),
    )
