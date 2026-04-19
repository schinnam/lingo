# CLI

The `lingo` command-line tool lets you look up, add, list, and export terms from your terminal.

---

## Installation

```bash
uv pip install -e .
```

This installs into the project virtualenv. Run commands via `uv run lingo` from the repo directory, or install globally with `uv tool install .` to get a bare `lingo` command anywhere in your shell.

---

## Configuration

Point the CLI at your Lingo server:

```bash
export LINGO_APP_URL=http://localhost:8000
```

**Authentication** — choose one:

=== "API token (production)"
    ```bash
    export LINGO_API_TOKEN=your-bearer-token
    ```

=== "Dev mode"
    ```bash
    export LINGO_DEV_USER_ID=00000000-0000-0000-0000-000000000001   # any UUID
    ```
    Only works when the server has `LINGO_DEV_MODE=true`.

---

## Commands

### `lingo define` — look up a term

```bash
lingo define API
```

Performs an exact case-insensitive lookup. Prints the term name, full name, definition, category, status, and vote count.

```bash
lingo define "SLA"
```

---

### `lingo add` — add a new term

```bash
lingo add "SLA" "Service Level Agreement"
```

Optional flags:

```bash
lingo add "SLA" "Service Level Agreement" \
  --full-name "Service Level Agreement" \
  --category ops
```

| Flag | Description |
|---|---|
| `--full-name TEXT` | Expanded form of the acronym |
| `--category TEXT` | Grouping label |

New terms are created with `pending` status.

---

### `lingo list` — list terms

```bash
lingo list
```

List all terms. Optional filters:

```bash
lingo list --status official
lingo list --category tech
lingo list --status community --category product
lingo list --limit 20
```

| Flag | Default | Description |
|---|---|---|
| `--status TEXT` | (all) | Filter by status: `suggested`, `pending`, `community`, `official` |
| `--category TEXT` | (all) | Filter by category |
| `--limit INT` | 50 | Maximum number of results |

---

### `lingo export` — export as Markdown

```bash
lingo export
```

Exports official terms as a Markdown glossary to stdout. Redirect to a file:

```bash
lingo export > glossary.md
```

Optional flags:

```bash
lingo export --status community --output glossary.md
```

| Flag | Default | Description |
|---|---|---|
| `--status TEXT` | `official` | Which terms to include |
| `--output PATH` | (stdout) | Write to a file instead of stdout |

---

## Help

```bash
lingo --help
lingo define --help
lingo add --help
lingo list --help
lingo export --help
```
