## Description

<!-- Summarize the change and the motivation behind it. Link to the relevant issue if applicable (e.g. Closes #123). -->

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor / internal improvement
- [ ] Documentation update

## Checklist

- [ ] Tests added or updated for changed logic
- [ ] `uv run pytest tests/` passes locally
- [ ] `uv run ruff check .` passes (no linting errors)
- [ ] **If database schema changed:** new Alembic migration generated (`uv run alembic revision --autogenerate -m "..."`) and tested with `uv run alembic upgrade head`
- [ ] **If API response shape changed:** API docs / schemas updated
- [ ] **If frontend changed:** `npm run build` run inside `frontend/` to update `src/lingo/static/`
- [ ] CHANGELOG.md updated (if user-facing change)
