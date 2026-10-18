"""Практические задания: чтение и отправка решения."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_role
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.submission import Submission
from app.models.task import Task
from app.models.user import User
from app.schemas.submission import SubmissionAccepted, SubmissionCreate
from app.schemas.task import TaskFull, TaskPublicForStudent, TaskUpdate
from app.services.task_service import run_ai_check

router = APIRouter()


def _public_task(task: Task) -> TaskPublicForStudent:
    return TaskPublicForStudent(
        id=task.id,
        title=task.title,
        description_md=task.description_md,
        task_type=task.task_type,
        language=task.language,
        requirements=task.requirements or [],
        hints=task.hints or [],
        passing_score=task.passing_score,
        max_attempts=task.max_attempts,
        max_solution_length=task.max_solution_length,
    )


@router.get("/tasks/{task_id}", response_model=TaskPublicForStudent, summary="Условие задания (для студента)")
async def get_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskPublicForStudent:
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Задание не найдено")
    return _public_task(task)


@router.get("/tasks/{task_id}/full", response_model=TaskFull, summary="Полное условие с эталоном (teacher/admin)")
async def get_task_full(
    task_id: int,
    _user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> TaskFull:
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Задание не найдено")
    return TaskFull.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskFull, summary="Обновить задание (teacher/admin)")
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> TaskFull:
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Задание не найдено")

    data = payload.model_dump(exclude_unset=True)
    if "check_criteria" in data and data["check_criteria"] is not None:
        data["check_criteria"] = [c.model_dump() if hasattr(c, "model_dump") else c for c in data["check_criteria"]]
    for k, v in data.items():
        setattr(task, k, v)
    await db.commit()
    await db.refresh(task)
    return TaskFull.model_validate(task)


@router.post(
    "/tasks/{task_id}/submissions",
    response_model=SubmissionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Сдать решение → запускает фоновую ИИ-проверку",
)
async def submit_solution(
    task_id: int,
    payload: SubmissionCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionAccepted:
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Задание не найдено")

    if len(payload.solution) > task.max_solution_length:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "SOLUTION_TOO_LONG",
                "message": f"Максимум {task.max_solution_length} символов",
            },
        )

    # Найти enrollment студента по курсу, к которому привязан этот task
    lesson = (
        await db.execute(select(Lesson).where(Lesson.task_id == task_id))
    ).scalar_one_or_none()
    if not lesson:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Задание не привязано к уроку")
    module = await db.get(Module, lesson.module_id)
    enr = (
        await db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user.id, Enrollment.course_id == module.course_id
            )
        )
    ).scalar_one_or_none()
    if not enr:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"code": "NOT_ENROLLED", "message": "Сначала запишитесь на курс"},
        )

    # Если ИИ-провайдер не настроен — submission создаётся СРАЗУ со статусом
    # error и понятным сообщением. Без поллинга, без зависания в pending.
    from app.ai.gigachat_provider import get_provider
    ai_configured = get_provider().is_configured()

    sub = Submission(
        user_id=user.id,
        task_id=task_id,
        enrollment_id=enr.id,
        solution=payload.solution,
        status="pending" if ai_configured else "error",
        error_message=None if ai_configured else (
            "ИИ-провайдер не настроен. Обратитесь к администратору, чтобы заполнить GIGACHAT_CREDENTIALS."
        ),
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)

    if ai_configured:
        background_tasks.add_task(run_ai_check, sub.id)
    return SubmissionAccepted(submission_id=sub.id, status=sub.status)
