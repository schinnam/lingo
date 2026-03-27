"""Tests for Phase 6: CLI commands via Typer + httpx.

Strategy:
  - CLI commands are thin wrappers over the REST API.
  - Tests mock httpx.Client to avoid needing a running server.
  - Each command is tested for: happy path, not-found, and error.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from lingo.cli.main import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _terms_envelope(items: list) -> dict:
    """Wrap a list of term dicts in the TermsListResponse envelope."""
    return {"items": items, "total": len(items), "offset": 0, "limit": 100, "counts_by_status": {}}


def _mock_response(json_data=None, status_code=200, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        from httpx import HTTPStatusError, Request, Response
        resp.raise_for_status.side_effect = HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock()
        )
    return resp


# ---------------------------------------------------------------------------
# lingo define <term>
# ---------------------------------------------------------------------------


class TestDefine:
    def test_define_found(self):
        terms = [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "name": "BART",
                "full_name": "Business Arts Resource Tool",
                "definition": "A centralized hub for resource allocation.",
                "category": "Operations",
                "status": "official",
                "vote_count": 12,
                "is_stale": False,
                "version": 1,
                "source": "user",
                "owner_id": None,
            }
        ]
        with patch("lingo.cli.main.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = _mock_response(_terms_envelope(terms))
            result = runner.invoke(app, ["define", "BART"])

        assert result.exit_code == 0
        assert "BART" in result.output
        assert "Business Arts Resource Tool" in result.output
        assert "A centralized hub for resource allocation." in result.output
        assert "official" in result.output.lower()

    def test_define_not_found(self):
        with patch("lingo.cli.main.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = _mock_response(_terms_envelope([]))
            result = runner.invoke(app, ["define", "UNKNWN"])

        assert result.exit_code != 0 or "not found" in result.output.lower()
        assert "UNKNWN" in result.output

    def test_define_case_insensitive(self):
        """Search is passed as-is; API handles case-insensitivity."""
        terms = [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "name": "BART",
                "full_name": None,
                "definition": "A hub.",
                "category": None,
                "status": "community",
                "vote_count": 4,
                "is_stale": False,
                "version": 1,
                "source": "user",
                "owner_id": None,
            }
        ]
        with patch("lingo.cli.main.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = _mock_response(_terms_envelope(terms))
            result = runner.invoke(app, ["define", "bart"])

        assert result.exit_code == 0
        assert "BART" in result.output


# ---------------------------------------------------------------------------
# lingo add <term> <definition>
# ---------------------------------------------------------------------------


class TestAdd:
    def test_add_success(self):
        created = {
            "id": "00000000-0000-0000-0000-000000000002",
            "name": "FMTL",
            "full_name": None,
            "definition": "Field Management Tool",
            "category": None,
            "status": "pending",
            "vote_count": 0,
            "is_stale": False,
            "version": 1,
            "source": "user",
            "owner_id": None,
        }
        with patch("lingo.cli.main.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.post.return_value = _mock_response(created, status_code=201)
            result = runner.invoke(app, ["add", "FMTL", "Field Management Tool"])

        assert result.exit_code == 0
        assert "FMTL" in result.output

    def test_add_with_full_name(self):
        created = {
            "id": "00000000-0000-0000-0000-000000000003",
            "name": "RESQ",
            "full_name": "Resource Queue",
            "definition": "Manages the resource queue.",
            "category": "Engineering",
            "status": "pending",
            "vote_count": 0,
            "is_stale": False,
            "version": 1,
            "source": "user",
            "owner_id": None,
        }
        with patch("lingo.cli.main.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.post.return_value = _mock_response(created, status_code=201)
            result = runner.invoke(
                app,
                ["add", "RESQ", "Manages the resource queue.",
                 "--full-name", "Resource Queue", "--category", "Engineering"],
            )

        assert result.exit_code == 0
        assert "RESQ" in result.output

    def test_add_missing_args(self):
        result = runner.invoke(app, ["add", "ONLY_TERM"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# lingo list
# ---------------------------------------------------------------------------


class TestList:
    def test_list_default(self):
        terms = [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "name": "ALPHA",
                "full_name": "Alpha System",
                "definition": "The first system.",
                "category": "Eng",
                "status": "official",
                "vote_count": 10,
                "is_stale": False,
                "version": 1,
                "source": "user",
                "owner_id": None,
            },
            {
                "id": "00000000-0000-0000-0000-000000000002",
                "name": "BETA",
                "full_name": None,
                "definition": "The second system.",
                "category": None,
                "status": "community",
                "vote_count": 5,
                "is_stale": False,
                "version": 1,
                "source": "user",
                "owner_id": None,
            },
        ]
        with patch("lingo.cli.main.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = _mock_response(_terms_envelope(terms))
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "ALPHA" in result.output
        assert "BETA" in result.output

    def test_list_with_status_filter(self):
        with patch("lingo.cli.main.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = _mock_response(_terms_envelope([]))
            result = runner.invoke(app, ["list", "--status", "official"])

        assert result.exit_code == 0
        # Verify the status param was passed
        call_kwargs = mock_client.get.call_args
        assert "official" in str(call_kwargs)

    def test_list_empty(self):
        with patch("lingo.cli.main.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = _mock_response(_terms_envelope([]))
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "no terms" in result.output.lower() or result.output.strip() != ""


# ---------------------------------------------------------------------------
# HTTP error paths
# ---------------------------------------------------------------------------


class TestApiErrors:
    """HTTP error paths for all commands."""

    def test_define_api_error(self):
        with patch("lingo.cli.main.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = _mock_response(status_code=500)
            result = runner.invoke(app, ["define", "BART"])
        assert result.exit_code != 0

    def test_add_api_error(self):
        with patch("lingo.cli.main.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.post.return_value = _mock_response(status_code=409)
            result = runner.invoke(app, ["add", "DUP", "Duplicate term"])
        assert result.exit_code != 0

    def test_list_api_error(self):
        with patch("lingo.cli.main.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = _mock_response(status_code=403)
            result = runner.invoke(app, ["list"])
        assert result.exit_code != 0

    def test_export_api_error(self):
        with patch("lingo.cli.main.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = _mock_response(status_code=401)
            result = runner.invoke(app, ["export"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# lingo export
# ---------------------------------------------------------------------------


class TestExport:
    def test_export_prints_markdown(self):
        markdown = "# Lingo Glossary\n\n## BART\n**Business Arts Resource Tool**\n\nA hub.\n"
        with patch("lingo.cli.main.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = _mock_response(text=markdown)
            mock_client.get.return_value.text = markdown
            result = runner.invoke(app, ["export"])

        assert result.exit_code == 0
        assert "Lingo Glossary" in result.output

    def test_export_to_file(self, tmp_path):
        markdown = "# Lingo Glossary\n\n## BART\nA hub.\n"
        out_file = tmp_path / "glossary.md"
        with patch("lingo.cli.main.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = _mock_response(text=markdown)
            mock_client.get.return_value.text = markdown
            result = runner.invoke(app, ["export", "--output", str(out_file)])

        assert result.exit_code == 0
        assert out_file.exists()
        assert "Lingo Glossary" in out_file.read_text()

    def test_export_with_status_filter(self):
        markdown = "# Lingo Glossary\n"
        with patch("lingo.cli.main.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = _mock_response(text=markdown)
            mock_client.get.return_value.text = markdown
            result = runner.invoke(app, ["export", "--status", "community"])

        assert result.exit_code == 0
        call_kwargs = mock_client.get.call_args
        assert "community" in str(call_kwargs)
