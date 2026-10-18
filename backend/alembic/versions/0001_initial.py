"""initial schema: 13 tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-01 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # categories
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("slug", sa.String(length=120), nullable=False, unique=True),
        sa.Column("icon_name", sa.String(length=50), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("position", sa.String(length=150), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="student"),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("directions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("current_level", sa.String(length=20), nullable=True),
        sa.Column("target_level", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("role IN ('student','teacher','admin')", name="users_role_check"),
        sa.CheckConstraint(
            "current_level IS NULL OR current_level IN ('beginner','junior','middle')",
            name="users_current_level_check",
        ),
        sa.CheckConstraint(
            "target_level IS NULL OR target_level IN ('junior','middle','senior')",
            name="users_target_level_check",
        ),
    )
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_directions", "users", ["directions"], postgresql_using="gin")

    # courses
    op.create_table(
        "courses",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False, unique=True),
        sa.Column("short_description", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("author_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("level", sa.String(length=20), nullable=False, server_default="junior"),
        sa.Column("target_role", sa.String(length=50), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("enrollment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating_avg", sa.Numeric(precision=3, scale=2), nullable=False, server_default="0"),
        sa.Column("passing_score", sa.Integer(), nullable=False, server_default="70"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("level IN ('beginner','junior','middle','senior')", name="courses_level_check"),
        sa.CheckConstraint("status IN ('draft','published','archived')", name="courses_status_check"),
    )
    op.create_index("ix_courses_status", "courses", ["status"])
    op.create_index("ix_courses_category_level", "courses", ["category_id", "level"])
    op.create_index("ix_courses_author", "courses", ["author_id"])

    # modules
    op.create_table(
        "modules",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("course_id", sa.BigInteger(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_modules_course_sort", "modules", ["course_id", "sort_order"])

    # quizzes
    op.create_table(
        "quizzes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("passing_score", sa.Integer(), nullable=False, server_default="70"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("shuffle_questions", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("show_correct_after", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # tasks
    op.create_table(
        "tasks",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description_md", sa.Text(), nullable=False),
        sa.Column("task_type", sa.String(length=20), nullable=False, server_default="code"),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("hints", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("check_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("reference_solution", sa.Text(), nullable=True),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("passing_score", sa.Integer(), nullable=False, server_default="70"),
        sa.Column("max_solution_length", sa.Integer(), nullable=False, server_default="10000"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("task_type IN ('code','theory','mixed')", name="tasks_task_type_check"),
    )

    # lessons
    op.create_table(
        "lessons",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("module_id", sa.BigInteger(), sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("content_markdown", sa.Text(), nullable=True),
        sa.Column("quiz_id", sa.BigInteger(), sa.ForeignKey("quizzes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("task_id", sa.BigInteger(), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("type IN ('text','quiz','task')", name="lessons_type_check"),
    )
    op.create_index("ix_lessons_module_sort", "lessons", ["module_id", "sort_order"])

    # enrollments
    op.create_table(
        "enrollments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.BigInteger(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_lesson_id", sa.BigInteger(), sa.ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("user_id", "course_id", name="enrollments_user_course_uniq"),
        sa.CheckConstraint("status IN ('active','completed','dropped')", name="enrollments_status_check"),
    )
    op.create_index("ix_enrollments_user_status", "enrollments", ["user_id", "status"])
    op.create_index("ix_enrollments_course", "enrollments", ["course_id"])

    # lesson_progress
    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_id", sa.BigInteger(), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enrollment_id", sa.BigInteger(), sa.ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="not_started"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "lesson_id", name="lesson_progress_user_lesson_uniq"),
        sa.CheckConstraint(
            "status IN ('not_started','in_progress','completed')", name="lesson_progress_status_check"
        ),
    )
    op.create_index("ix_lesson_progress_enrollment", "lesson_progress", ["enrollment_id"])

    # quiz_questions
    op.create_table(
        "quiz_questions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("quiz_id", sa.BigInteger(), sa.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_text", sa.Text(), nullable=True),
        sa.CheckConstraint("type IN ('single','multiple','text_short')", name="quiz_questions_type_check"),
    )
    op.create_index("ix_quiz_questions_quiz", "quiz_questions", ["quiz_id", "sort_order"])

    # quiz_answers
    op.create_table(
        "quiz_answers",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "question_id",
            sa.BigInteger(),
            sa.ForeignKey("quiz_questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    # quiz_attempts
    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quiz_id", sa.BigInteger(), sa.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "enrollment_id",
            sa.BigInteger(),
            sa.ForeignKey("enrollments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="in_progress"),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('in_progress','submitted')", name="quiz_attempts_status_check"),
    )
    op.create_index("ix_quiz_attempts_user_quiz", "quiz_attempts", ["user_id", "quiz_id"])

    # attempt_answers
    op.create_table(
        "attempt_answers",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.BigInteger(),
            sa.ForeignKey("quiz_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.BigInteger(),
            sa.ForeignKey("quiz_questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column(
            "selected_answer_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("points_awarded", sa.Integer(), nullable=False, server_default="0"),
    )

    # submissions
    op.create_table(
        "submissions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.BigInteger(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "enrollment_id",
            sa.BigInteger(),
            sa.ForeignKey("enrollments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("solution", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("score_percent", sa.Integer(), nullable=True),
        sa.Column("is_passed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("ai_per_criterion", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ai_improvement_tips", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','checking','checked','error')", name="submissions_status_check"
        ),
    )
    op.create_index("ix_submissions_user_status", "submissions", ["user_id", "status"])
    op.create_index("ix_submissions_task", "submissions", ["task_id"])

    # ai_usage
    op.create_table(
        "ai_usage",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scenario", sa.String(length=20), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("scenario IN ('lesson_package','task_check')", name="ai_usage_scenario_check"),
    )
    op.create_index("ix_ai_usage_user_scenario_date", "ai_usage", ["user_id", "scenario", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_usage_user_scenario_date", table_name="ai_usage")
    op.drop_table("ai_usage")
    op.drop_index("ix_submissions_task", table_name="submissions")
    op.drop_index("ix_submissions_user_status", table_name="submissions")
    op.drop_table("submissions")
    op.drop_table("attempt_answers")
    op.drop_index("ix_quiz_attempts_user_quiz", table_name="quiz_attempts")
    op.drop_table("quiz_attempts")
    op.drop_table("quiz_answers")
    op.drop_index("ix_quiz_questions_quiz", table_name="quiz_questions")
    op.drop_table("quiz_questions")
    op.drop_index("ix_lesson_progress_enrollment", table_name="lesson_progress")
    op.drop_table("lesson_progress")
    op.drop_index("ix_enrollments_course", table_name="enrollments")
    op.drop_index("ix_enrollments_user_status", table_name="enrollments")
    op.drop_table("enrollments")
    op.drop_index("ix_lessons_module_sort", table_name="lessons")
    op.drop_table("lessons")
    op.drop_table("tasks")
    op.drop_table("quizzes")
    op.drop_index("ix_modules_course_sort", table_name="modules")
    op.drop_table("modules")
    op.drop_index("ix_courses_author", table_name="courses")
    op.drop_index("ix_courses_category_level", table_name="courses")
    op.drop_index("ix_courses_status", table_name="courses")
    op.drop_table("courses")
    op.drop_index("ix_users_directions", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_table("users")
    op.drop_table("categories")
