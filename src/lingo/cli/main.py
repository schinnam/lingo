"""Lingo CLI — thin client over the REST API.

Entry point: `lingo` (configured in pyproject.toml [project.scripts])

Configuration via environment variables:
  LINGO_APP_URL    — base URL of the Lingo server (default: http://localhost:8000)
  LINGO_API_TOKEN  — bearer token for authentication (optional in dev mode)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="lingo",
    help="Lingo — company glossary CLI",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True, style="bold red")

_DEFAULT_TIMEOUT = 30.0


def _base_url() -> str:
    url = os.environ.get("LINGO_APP_URL", "http://localhost:8000")
    # Ensure base_url ends with "/" so httpx appends paths correctly
    return url if url.endswith("/") else url + "/"


def _headers() -> dict:
    token = os.environ.get("LINGO_API_TOKEN", "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    # Dev mode: use a dummy user ID header
    dev_user = os.environ.get("LINGO_DEV_USER_ID", "")
    if dev_user:
        return {"X-User-Id": dev_user}
    return {}


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=_base_url(),
        headers=_headers(),
        timeout=_DEFAULT_TIMEOUT,
    )


# ---------------------------------------------------------------------------
# define
# ---------------------------------------------------------------------------


@app.command()
def define(
    term: str = typer.Argument(..., help="Term name to look up"),
):
    """Look up a term by name and display its definition."""
    with _client() as client:
        try:
            resp = client.get("api/v1/terms", params={"q": term, "limit": 10})
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            err_console.print(f"API error: {exc.response.status_code}")
            raise typer.Exit(1)

    terms = resp.json()
    # Prefer exact case-insensitive match; fall back to first fuzzy result
    exact = [t for t in terms if t["name"].lower() == term.lower()]
    match = exact[0] if exact else (terms[0] if terms else None)

    if match is None:
        err_console.print(f'Error: no term found for "{term}"')
        raise typer.Exit(1)

    if not exact and terms:
        console.print(f'[dim]No exact match for "{term}" — showing closest result.[/dim]')

    _print_term(match)


def _print_term(term: dict) -> None:
    name = term.get("name", "?")
    definition = term.get("definition", "(no definition)")
    status = term.get("status", "unknown")
    votes = term.get("vote_count", 0)
    console.print(f"\n┌─ [bold]{name}[/bold]")
    if term.get("full_name"):
        console.print(f"├─ {term['full_name']}")
    console.print(f"├─ Definition: {definition}")
    console.print(f"├─ Status: {status} ({votes} votes)")
    if term.get("category"):
        console.print(f"├─ Category: {term['category']}")
    console.print("└")


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


@app.command()
def add(
    term: str = typer.Argument(..., help="Term name (e.g. BART)"),
    definition: str = typer.Argument(..., help="Term definition"),
    full_name: Optional[str] = typer.Option(None, "--full-name", "-f", help="Full expanded name"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Category"),
):
    """Add a new term to the glossary."""
    payload: dict = {"name": term, "definition": definition}
    if full_name:
        payload["full_name"] = full_name
    if category:
        payload["category"] = category

    with _client() as client:
        try:
            resp = client.post("api/v1/terms", json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            err_console.print(f"API error: {exc.response.status_code}")
            try:
                detail = exc.response.json().get("detail", "")
                if detail:
                    err_console.print(detail)
            except Exception:
                pass
            raise typer.Exit(1)

    created = resp.json()
    console.print(f"[green]Added:[/green] {created['name']} (status: {created['status']})")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@app.command(name="list")
def list_terms(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max results"),
):
    """List glossary terms."""
    params: dict = {"limit": limit}
    if status:
        params["status"] = status
    if category:
        params["category"] = category

    with _client() as client:
        try:
            resp = client.get("api/v1/terms", params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            err_console.print(f"API error: {exc.response.status_code}")
            raise typer.Exit(1)

    terms = resp.json()

    if not terms:
        console.print("No terms found.")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", style="bold")
    table.add_column("Status")
    table.add_column("Votes", justify="right")
    table.add_column("Definition", max_width=60, no_wrap=False)

    for t in terms:
        table.add_row(t["name"], t["status"], str(t.get("vote_count", 0)), t["definition"])

    console.print(table)


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


@app.command()
def export(
    status: str = typer.Option("official", "--status", "-s", help="Status filter"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Export glossary terms as Markdown."""
    params = {"status": status, "format": "markdown"}

    with _client() as client:
        try:
            resp = client.get("api/v1/export", params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            err_console.print(f"API error: {exc.response.status_code}")
            raise typer.Exit(1)

    content = resp.text

    if output:
        out_path = Path(output)
        if not out_path.parent.exists():
            err_console.print(f"Error: directory does not exist: {out_path.parent}")
            raise typer.Exit(1)
        out_path.write_text(content)
        console.print(f"[green]Exported to {output}[/green]")
    else:
        console.print(content)
