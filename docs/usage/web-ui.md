# Web UI

Lingo's web interface is a React single-page application served at `http://localhost:8000`. It provides search, filtering, voting, and term management without leaving your browser.

---

## Search

The search bar at the top of the page filters terms as you type. It matches against the term name, definition, full name, and category.

**Keyboard shortcut**: Press `/` or `Cmd+K` (Mac) / `Ctrl+K` (Linux/Windows) to focus the search bar from anywhere on the page.

---

## Status filters

Below the search bar, filter pills let you narrow terms by status:

| Status | Description |
|---|---|
| **All** | Show every term |
| **Suggested** | Discovered by auto-scan or added without votes |
| **Pending** | At least one community vote |
| **Community** | Reached the community vote threshold |
| **Official** | Editor-approved at the official vote threshold |

Each pill shows a live count of terms in that status.

---

## Term list

The main table shows terms matching your search and filter. Each row displays:

- **Name** — the term or acronym
- **Definition** — short description
- **Status** — color-coded badge
- **Category** — optional grouping label
- **Vote count**

Click any row to open the detail panel.

---

## Term detail panel

Clicking a term slides open a panel on the right with:

- Full definition and full name
- Category and status badge
- Vote count and your vote status
- Linked related terms (synonyms, antonyms, related)
- Edit history (who changed what and when)

### Voting

Click **Vote** to upvote a term. The vote count updates immediately. When enough votes accumulate, the term status advances automatically:

```
suggested → pending    (first vote)
pending   → community  (community_threshold votes, default: 3)
community → official   (editor action + official_threshold votes, default: 10)
```

### Disputing

Click **Dispute** to flag a term for review. This notifies the term owner and resets the vote tally.

---

## Adding a term

Click **Add term** (top-right) to open the form:

| Field | Required | Notes |
|---|---|---|
| **Name** | Yes | The acronym or term (e.g. `API`) |
| **Definition** | Yes | Clear, concise description |
| **Full name** | No | Expanded form (e.g. `Application Programming Interface`) |
| **Category** | No | Grouping label (e.g. `tech`, `ops`, `product`) |

New terms start as `suggested`. Submit the form and the term appears in the list immediately.

---

## Dev mode banner

When `LINGO_DEV_MODE=true`, a yellow banner appears at the top of the page as a reminder that authentication is disabled. This is read from a meta tag injected by the server — no extra API call required.

!!! warning
    If you see the dev mode banner in a non-development environment, set `LINGO_DEV_MODE=false` immediately.
