"""6.5 identity, scoped roles and Entra-ready user mapping

Revision ID: 0007_identity_roles_entra_ready
Revises: 0006_reconcile_legacy_omr_schema
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0007_identity_roles_entra_ready"
down_revision = "0006_reconcile_legacy_omr_schema"
branch_labels = None
depends_on = None

VALID_ROLES = {"admin", "quality", "instructor", "program_head", "department_head", "faculty_admin"}


def _has_column(bind, table: str, column: str) -> bool:
    insp = inspect(bind)
    return insp.has_table(table) and column in {c["name"] for c in insp.get_columns(table)}


def _seed_and_import(bind) -> None:
    users = sa.table(
        "app_users",
        sa.column("id", sa.Integer), sa.column("email", sa.String), sa.column("display_name", sa.String),
        sa.column("external_object_id", sa.String), sa.column("tenant_id", sa.String), sa.column("auth_source", sa.String),
        sa.column("is_active", sa.Boolean), sa.column("created_at", sa.DateTime(timezone=True)),
    )
    roles = sa.table(
        "user_role_assignments",
        sa.column("user_id", sa.Integer), sa.column("role", sa.String), sa.column("program_id", sa.Integer),
        sa.column("course_id", sa.Integer), sa.column("scope_faculty", sa.String), sa.column("scope_department", sa.String),
        sa.column("scope_program", sa.String), sa.column("created_at", sa.DateTime(timezone=True)),
    )

    def ensure_user(email: str, name: str, source: str, active: bool = True) -> int:
        email = (email or "").strip().lower()
        if not email:
            raise ValueError("empty email")
        existing = bind.execute(sa.text("SELECT id FROM app_users WHERE lower(email)=:e"), {"e": email}).scalar()
        if existing:
            return int(existing)
        bind.execute(users.insert().values(
            email=email, display_name=(name or email).strip(), external_object_id=None, tenant_id=None,
            auth_source=source, is_active=bool(active), created_at=sa.func.current_timestamp(),
        ))
        return int(bind.execute(sa.text("SELECT id FROM app_users WHERE lower(email)=:e"), {"e": email}).scalar_one())

    def ensure_role(uid: int, role: str, faculty: str = "", department: str = "", program: str = "") -> None:
        role = role if role in VALID_ROLES else "instructor"
        exists = bind.execute(sa.text(
            "SELECT id FROM user_role_assignments WHERE user_id=:u AND role=:r "
            "AND scope_faculty=:f AND scope_department=:d AND scope_program=:p LIMIT 1"
        ), {"u": uid, "r": role, "f": faculty or "", "d": department or "", "p": program or ""}).scalar()
        if not exists:
            bind.execute(roles.insert().values(
                user_id=uid, role=role, program_id=None, course_id=None,
                scope_faculty=faculty or "", scope_department=department or "", scope_program=program or "",
                created_at=sa.func.current_timestamp(),
            ))

    pilot_id = ensure_user("pilot-admin@local", "Pilot Sistem Yöneticisi", "pilot", True)
    ensure_role(pilot_id, "admin")

    # Import v4 user identities if that legacy table still exists. Password hashes
    # are deliberately NOT copied; 6.5 no longer owns university passwords.
    insp = inspect(bind)
    if insp.has_table("users"):
        cols = {c["name"] for c in insp.get_columns("users")}
        required = {"email", "full_name", "role"}
        if required.issubset(cols):
            select_cols = ["email", "full_name", "role"]
            for optional in ("faculty", "department", "program", "is_active"):
                if optional in cols:
                    select_cols.append(optional)
            rows = bind.execute(sa.text(f"SELECT {', '.join(select_cols)} FROM users")).mappings().all()
            for row in rows:
                email = (row.get("email") or "").strip().lower()
                if not email:
                    continue
                uid = ensure_user(email, row.get("full_name") or email, "legacy", bool(row.get("is_active", True)))
                ensure_role(uid, row.get("role") or "instructor", row.get("faculty") or "", row.get("department") or "", row.get("program") or "")


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("app_users"):
        op.create_table(
            "app_users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(255), nullable=False, unique=True),
            sa.Column("display_name", sa.String(255), nullable=False),
            sa.Column("external_object_id", sa.String(64), nullable=True),
            sa.Column("tenant_id", sa.String(64), nullable=True),
            sa.Column("auth_source", sa.String(32), nullable=False, server_default="pilot"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        )
        op.create_index("ix_app_users_email", "app_users", ["email"], unique=True)
        op.create_index("ix_app_users_external_object_id", "app_users", ["external_object_id"])
        op.create_index("ix_app_users_tenant_id", "app_users", ["tenant_id"])

    if not inspect(bind).has_table("user_role_assignments"):
        op.create_table(
            "user_role_assignments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(40), nullable=False),
            sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=True),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=True),
            sa.Column("scope_faculty", sa.String(255), nullable=False, server_default=""),
            sa.Column("scope_department", sa.String(255), nullable=False, server_default=""),
            sa.Column("scope_program", sa.String(255), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
            sa.CheckConstraint("role IN ('admin','quality','instructor','program_head','department_head','faculty_admin')", name="ck_user_role_valid"),
        )
        op.create_index("ix_user_role_assignments_user_id", "user_role_assignments", ["user_id"])
        op.create_index("ix_user_role_assignments_role", "user_role_assignments", ["role"])
        op.create_index("ix_user_role_assignments_program_id", "user_role_assignments", ["program_id"])
        op.create_index("ix_user_role_assignments_course_id", "user_role_assignments", ["course_id"])

    if inspect(bind).has_table("audit_logs"):
        if not _has_column(bind, "audit_logs", "actor_user_id"):
            op.add_column("audit_logs", sa.Column("actor_user_id", sa.Integer(), nullable=True))
            op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
        if not _has_column(bind, "audit_logs", "actor_email"):
            op.add_column("audit_logs", sa.Column("actor_email", sa.String(255), nullable=False, server_default="system"))
        if not _has_column(bind, "audit_logs", "actor_roles"):
            op.add_column("audit_logs", sa.Column("actor_roles", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))

    _seed_and_import(bind)


def downgrade() -> None:
    # Intentionally non-destructive for pilot history and imported legacy identities.
    pass
