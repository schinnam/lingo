"""Tests for SQLAlchemy domain models.

These tests verify model structure, constraints, and defaults
without a live database — we inspect the ORM metadata.
"""
import uuid
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import DeclarativeBase

from lingo.models.base import Base
from lingo.models.user import User
from lingo.models.term import Term
from lingo.models.vote import Vote
from lingo.models.token import Token
from lingo.models.term_history import TermHistory
from lingo.models.term_relationship import TermRelationship, RelationshipType
from lingo.models.job import Job, JobType, JobStatus


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class TestBase:
    def test_base_is_declarative(self):
        assert issubclass(Base, DeclarativeBase)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class TestUserModel:
    def test_table_name(self):
        assert User.__tablename__ == "users"

    def test_columns_exist(self):
        cols = {c.name for c in User.__table__.columns}
        assert {"id", "email", "display_name", "slack_user_id",
                "role", "last_login_at", "is_active", "created_at"} <= cols

    def test_email_unique(self):
        email_col = User.__table__.c["email"]
        assert email_col.unique

    def test_is_active_default_true(self):
        assert User.__table__.c["is_active"].default.arg is True

    def test_role_default_member(self):
        assert User.__table__.c["role"].default.arg == "member"

    def test_id_is_uuid(self):
        id_col = User.__table__.c["id"]
        from sqlalchemy import Uuid
        assert isinstance(id_col.type, Uuid)

    def test_instantiation(self):
        u = User(email="alice@example.com", display_name="Alice")
        assert u.email == "alice@example.com"
        assert u.is_active is True
        assert u.role == "member"


# ---------------------------------------------------------------------------
# Term
# ---------------------------------------------------------------------------

class TestTermModel:
    def test_table_name(self):
        assert Term.__tablename__ == "terms"

    def test_required_columns(self):
        cols = {c.name for c in Term.__table__.columns}
        assert {
            "id", "name", "full_name", "definition", "category",
            "status", "source", "source_channel_id", "occurrences_count",
            "owner_id", "owned_at", "is_stale", "last_confirmed_at",
            "version", "created_by", "created_at", "updated_at",
        } <= cols

    def test_is_stale_default_false(self):
        assert Term.__table__.c["is_stale"].default.arg is False

    def test_version_default_one(self):
        assert Term.__table__.c["version"].default.arg == 1

    def test_status_not_nullable(self):
        assert not Term.__table__.c["status"].nullable

    def test_definition_max_length(self):
        defn_col = Term.__table__.c["definition"]
        # Our model uses a CheckConstraint or String(2000)
        assert defn_col.type.length == 2000

    def test_instantiation_defaults(self):
        t = Term(
            name="BART",
            definition="Business Arts Resource Tool",
            status="pending",
            source="user",
        )
        assert t.is_stale is False
        assert t.version == 1


# ---------------------------------------------------------------------------
# Vote
# ---------------------------------------------------------------------------

class TestVoteModel:
    def test_table_name(self):
        assert Vote.__tablename__ == "votes"

    def test_composite_pk(self):
        pk_cols = {c.name for c in Vote.__table__.primary_key.columns}
        assert pk_cols == {"term_id", "user_id"}

    def test_columns_exist(self):
        cols = {c.name for c in Vote.__table__.columns}
        assert {"term_id", "user_id", "created_at"} <= cols


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

class TestTokenModel:
    def test_table_name(self):
        assert Token.__tablename__ == "tokens"

    def test_columns_exist(self):
        cols = {c.name for c in Token.__table__.columns}
        assert {
            "id", "user_id", "name", "token_hash",
            "scopes", "created_at", "last_used_at", "revoked_at",
        } <= cols


# ---------------------------------------------------------------------------
# TermHistory
# ---------------------------------------------------------------------------

class TestTermHistoryModel:
    def test_table_name(self):
        assert TermHistory.__tablename__ == "term_history"

    def test_columns_exist(self):
        cols = {c.name for c in TermHistory.__table__.columns}
        assert {
            "id", "term_id", "definition", "full_name", "category",
            "owner_id", "status", "changed_by", "changed_at", "change_note",
        } <= cols

    def test_change_note_max_length(self):
        col = TermHistory.__table__.c["change_note"]
        assert col.type.length == 280


# ---------------------------------------------------------------------------
# TermRelationship
# ---------------------------------------------------------------------------

class TestTermRelationshipModel:
    def test_table_name(self):
        assert TermRelationship.__tablename__ == "term_relationships"

    def test_columns_exist(self):
        cols = {c.name for c in TermRelationship.__table__.columns}
        assert {
            "id", "term_id", "related_term_id",
            "relationship_type", "created_by", "created_at",
        } <= cols

    def test_relationship_type_enum(self):
        assert set(RelationshipType) == {
            RelationshipType.depends_on,
            RelationshipType.supersedes,
            RelationshipType.related_to,
        }


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

class TestJobModel:
    def test_table_name(self):
        assert Job.__tablename__ == "jobs"

    def test_columns_exist(self):
        cols = {c.name for c in Job.__table__.columns}
        assert {
            "id", "job_type", "status", "progress_json",
            "started_at", "completed_at", "error",
        } <= cols

    def test_job_type_enum(self):
        assert set(JobType) == {JobType.discovery, JobType.staleness}

    def test_job_status_enum(self):
        assert set(JobStatus) == {
            JobStatus.pending,
            JobStatus.running,
            JobStatus.completed,
            JobStatus.failed,
        }

    def test_status_default_pending(self):
        j = Job(job_type=JobType.discovery)
        assert j.status == JobStatus.pending
