---
name: factory
description: Run the software factory. Use when the user types /factory <feature>, /factory next, /factory approve <job-id>, /factory rework <job-id> <note>, or /factory retro <job-id>. The session that runs it becomes the orchestrator of the spec → build → review → approve loop.
---

# Factory

You are the orchestrator for one job. You run the loop below, spawn every agent,
and are the only writer of `factory/board.json` and your job's `job.json`. You
never write code, specs, reviews or decisions yourself. Agents do the work and
each writes one file; you move the job along and keep both current.

## The loop

```
feature → spec-writer ⇄ user → ticket-writer ⇄ user → builder (per ticket) → [security, ux, ui, code] → WAIT FOR ALL
                           ▲                                      │
                           └──── any CHANGES: resume builder ◄────┤
                                                                  ▼ all PASS
                                     merge to main ◄─ APPROVE ─ approver ─ ESCALATE → needs-human
                                           └──────────────► retro ◄──────────────┘
```

| Step         | Agent (`subagent_type`) | Writes                                      |
| ------------ | ----------------------- | ------------------------------------------- |
| spec         | `spec-writer`           | `grill.md`, `spec.md` (+ slice specs)       |
| tickets      | `ticket-writer`         | `tickets.md`, `tickets/NN-<slug>.md`        |
| build        | `builder` (one per ticket) | `build.md` + commits on `factory/<job-id>` |
| review       | `reviewer-security`     | `round-N/review-security.md`                |
|              | `reviewer-ux`           | `round-N/review-ux.md`                      |
|              | `reviewer-ui`           | `round-N/review-ui.md`                      |
|              | `reviewer-code`         | `round-N/review-code.md`                    |
| approve      | `approver`              | `decision.md`                               |
| retro        | `retro`                 | `retro.md` (suggestions only)               |

`MAX_RESUMES = 2`: after round 1 the builder can be resumed at most twice, so a
run has at most 3 review rounds. To change the factory, edit this file and the
agent files in `.claude/agents/`.

Every agent reads `AGENTS.md` (or `CLAUDE.md`) for the repo's setup, dev server,
validation commands and conventions. Nothing repo-specific lives in these files.

## Parallel jobs

Every job runs in its own git worktree on its own branch, so several jobs can run
at once, one per Claude session. To run three features, open three sessions in
this repo and start `/factory` in each. Your session orchestrates only the job it
started or was handed.

- Your session stays in the main checkout. Agents work in the job's worktree.
  The main checkout is the user's, and it may be dirty or on another branch.
  Only **Merge** touches it.
- Job state lives in `factory/jobs/<job-id>/` in the main checkout, never in a
  worktree. Each job has its own `job.json`, so sessions never write the same
  file.
- Each job gets its own dev server ports and agent-browser sessions (see
  **Prompts**), so reviewers of different jobs never see each other's pages.
- Spawn only the agents in this checkout's agent folder (`.claude/agents/`, or `.agents/agents/`).
  A trial agent on a feature branch runs in that branch's own factory, never in a job started from `main`.

## Files

`<repo>` is the main checkout (`git rev-parse --show-toplevel` from your
session) and `<name>` is its folder name. `factory/jobs/` is gitignored runtime
state that never lands in a commit.

```
<repo>/factory/board.json                      durable board state, one entry per job (drives the dashboard)
<repo>/factory/backlog.md                      queue for /factory next
<repo>/factory/specs/<job-id>-<k>-<slug>.md    slice specs a spec-writer split off, queued in the backlog
<repo>/factory/jobs/<job-id>/job.json          the job's state (you write it, the dashboard reads it)
<repo>/factory/jobs/<job-id>/grill.md         grilling rounds and the user's answers
<repo>/factory/jobs/<job-id>/spec.md
<repo>/factory/jobs/<job-id>/tickets.md             the ticket index and build order
<repo>/factory/jobs/<job-id>/tickets/NN-<slug>.md   one file per ticket
<repo>/factory/jobs/<job-id>/build.md
<repo>/factory/jobs/<job-id>/rework-<k>.md     written by you, from /factory rework
<repo>/factory/jobs/<job-id>/round-<N>/review-{security,ux,ui,code}.md
<repo>/factory/jobs/<job-id>/decision.md
<repo>/factory/jobs/<job-id>/retro.md
<repo>/../<name>-factory/<job-id>/             the job's worktree, on factory/<job-id>
```

### job.json

```json
{ "id": "003-rate-limiting", "feature": "Rate limit the signup form",
  "branch": "factory/003-rate-limiting",
  "worktree": "/Users/you/code/my-app-factory/003-rate-limiting",
  "stage": "review", "round": 2,
  "reviews": { "security": "CHANGES", "ux": "PASS", "ui": "pending", "code": "PASS" },
  "tickets": { "01-setup-data": "done", "02-routing": "building", "03-priority": "pending" } }
```

- `stage` is one of `spec`, `build`, `review`, `approve`, `merged`,
  `needs-human`. Worktree setup counts as `spec`.
- `tickets` is optional and appears once tickets are approved. Each value is
  `pending`, `building` or `done`. The dashboard ignores it.
- `round` is the current review round (0 until the first round starts).
- `reviews` holds the current round only. Each value is `pending`, `PASS` or
  `CHANGES`. Earlier rounds live in their `round-<N>/` folders, which the
  dashboard reads directly.
- Rewrite the whole file on every change. `worktree` is always an absolute path.
- `factory/board.json` is `{ "jobs": [ <job.json contents>, ... ] }`. On every
  `job.json` change, also upsert that job's entry (matched by `id`) in
  `board.json`, re-reading the file first so you never overwrite another
  session's entries. The dashboard reads `board.json` for history and lets each
  live `job.json` override its entry.

### Prompts

Every agent prompt starts with the job's absolute paths:
`Job folder: <repo>/factory/jobs/<job-id>/. Worktree: <worktree>. Branch: factory/<job-id>.`
Below, `<paths>` stands for that sentence.

Agents that open pages also get a port. With `n` the job number (`003` → 3),
the builder gets `5100 + 10n`, `reviewer-ux` gets `5101 + 10n` and `reviewer-ui`
gets `5102 + 10n`, appended as ` Port: <port>.`

## /factory <feature>

1. **Create the job.** `mkdir -p factory/jobs`, then pick the next 3-digit number
   after the highest numbered folder in `factory/jobs/` (`001` if there are
   none) and a 2–4 word kebab-case slug of the feature: `004-blog-reading-time`.
   Claim it with `mkdir factory/jobs/<job-id>` (no `-p`). If that fails because
   another session took the number, pick the next number and try again.
   The worktree path is `$(cd .. && pwd)/$(basename "$PWD")-factory/<job-id>`,
   run from `<repo>`. Write `job.json` with that `worktree`, `stage: "spec"`,
   `round: 0` and all reviews `pending`.
2. **Worktree.** Create the branch and its worktree from `main`:
   ```bash
   git worktree add -b factory/<job-id> <worktree> main
   ```
   Then, in the worktree, run the setup AGENTS.md gives for a fresh checkout
   (installing dependencies, for example). If any of it fails, stop and tell
   the user.
3. **Spec.** Spawn `spec-writer` **with the name `spec-writer-<job-id>`** and
   the prompt `<paths> Feature: <feature, verbatim>` (from `/factory next`,
   add ` Spec: <slice spec path>` when the backlog item has one). Then go to
   **Grilling**; come back once `spec.md` exists.
4. **Tickets.** Go to **Tickets**; come back once `tickets.md` starts with
   `STATUS: APPROVED`.
5. **Build.** Go to **Build tickets**.

### Grilling

The spec-writer grills the user before it writes the spec, but it can't talk to
the user: you relay. The job stays in `stage: "spec"` throughout.

1. When the spec-writer finishes and `spec.md` doesn't exist yet, its final
   message is a grilling round (or the closing summary asking the user to
   confirm). Show it to the user verbatim and wait for their reply. Never answer
   a question yourself, even when the recommended answer looks obvious.
2. Append the reply, verbatim, to `factory/jobs/<job-id>/grill.md` under
   `### Answers`, then resume the same spec-writer with `SendMessage` to
   `spec-writer-<job-id>`: `User answers: <reply, verbatim>`.
3. Repeat until `spec.md` exists. If the spec-writer finishes without
   `spec.md` and without a question for the user, stop and tell the user.
4. If its final message lists slices, tell the user which slice specs it wrote
   and which backlog lines it added. This job builds slice 1 only.

If the user abandons the feature, set `stage: "needs-human"` and leave the
worktree for them.

### Tickets

One builder run over a whole spec takes too long, so the spec is split into
small tickets first. The stage stays `spec`. Spawn `ticket-writer` **with the
name `ticket-writer-<job-id>`** and the prompt `<paths>`.

1. When it finishes, show the user its final message verbatim: the numbered
   breakdown with the suggested build order. Wait for their reply. Never answer
   for them.
2. If the user wants changes, append the reply, verbatim, to
   `factory/jobs/<job-id>/grill.md` under `### Ticket answers` and resume the
   writer with `SendMessage`: `User answers: <reply, verbatim>`. Repeat step 1.
3. When the user approves the breakdown and order, resume the writer with
   `User approved`, then check that `tickets.md` starts with `STATUS: APPROVED`.
   Add the `tickets` map to `job.json` (all `pending`).
4. A job whose spec yields one ticket still goes through this step.

### Build tickets

Set `stage: "build"`. Take the tickets in the order of `tickets.md`, one at a
time, never in parallel (they share one worktree and branch). A ticket is
eligible when every ticket in its `Blocked by` is `done`.

For each eligible ticket, set it to `building` in `job.json`, then spawn a fresh
`builder` **named `builder-<job-id>-<NN>`** with the prompt
`<paths> Build ticket <NN>. Ticket: factory/jobs/<job-id>/tickets/<NN>-<slug>.md. Port: <port>.`
When it finishes, go to **Build check**. On `STATUS: READY` set the ticket to
`done` and take the next. After the last ticket, start **Review round 1**.

### Build check

Read the first line of `build.md`.

- `STATUS: READY`: take the next ticket, or after the last one (or after a review-fix build) start the next review round.
- `STATUS: BLOCKED`: go to **Needs human**.

### Review round N

1. Set `stage: "review"`, `round: N` and all four reviews to `pending`. Create
   `factory/jobs/<job-id>/round-<N>/`.
2. Spawn all four reviewers **in one message**, so they run in parallel. Each
   gets the prompt `<paths> Review round N.`, plus its port for `reviewer-ux`
   and `reviewer-ui`.
3. **WAIT FOR ALL.** Each time a reviewer finishes, read the first line of its
   file (`VERDICT: PASS` or `VERDICT: CHANGES`) and write that verdict to
   `job.json` straight away, so the dashboard chips fill in as they land. The
   round is done only when all four `review-*.md` files exist in `round-<N>/`.
   Never resume the builder mid-round. If a reviewer finishes without writing
   its file, or writes a first line that isn't a verdict, stop and tell the user.
4. Decide:
   - **All PASS**: go to **Approve**.
   - **Any CHANGES, resumes left**: set `stage: "build"`, then resume
     `builder-<job-id>` with `SendMessage` (spawn a fresh `builder` of that name if
     none exists, since ticket builders finish before review; review fixes are one
     build, not per ticket):
     `Round N reviews are in factory/jobs/<job-id>/round-<N>/. Address every review with VERDICT: CHANGES, commit, and update build.md for round N+1.`
     Wait for it to finish, then go to **Build check**.
   - **Any CHANGES, no resumes left**: write `decision.md` yourself, reading
     `ESCALATE`, then a blank line, then
     `Review rounds exhausted. Outstanding CHANGES in round-<N>/ from: <reviewers>.`
     Go to **Needs human**.

### Approve

Set `stage: "approve"`. Spawn `approver` with the prompt `<paths> Final round: N.`
When it finishes, read the first line of `decision.md`:

- `APPROVE`: go to **Merge**.
- `ESCALATE`: go to **Needs human**.

### Merge

The merge happens in the main checkout, so it must be clean and on `main`:
`git status --porcelain -- . ':!factory/backlog.md' ':!factory/specs' ':!factory/board.json'`
prints nothing and `git branch --show-current` prints `main`. `factory/backlog.md`,
`factory/specs/` and `factory/board.json` are exempt: `/factory next`, spec-writers
and the orchestrator edit them, and job
branches never touch them, so they cannot conflict with the merge. If not, set `stage: "needs-human"` and tell the
user the job is approved but the main checkout is busy; they run
`/factory approve <job-id>` once it is clean. Otherwise:

```bash
git merge --no-ff factory/<job-id> -m "Merge factory/<job-id>"
git worktree remove <worktree>
git branch -d factory/<job-id>
```

Set `stage: "merged"`. If the merge fails, run `git merge --abort` (when a merge
is in progress), set `stage: "needs-human"` and tell the user why. If removing the
worktree fails, the job is still merged: tell the user what `git worktree remove`
printed. Never push. Then run **Retro**.

### Needs human

Set `stage: "needs-human"`. The branch and its worktree stay for the human to
inspect. Tell the user which job is waiting, give the worktree path, and quote
`decision.md` (or the BLOCKED reason from `build.md`). Then run **Retro**,
unless the job stopped during grilling.

### Retro

Runs after every job ends, merged or not, and on `/factory retro <job-id>`.
Spawn `retro` with the prompt `<paths> Outcome: <merged | needs-human>.`
(after a merge the worktree is gone; the paths still name the job). When it
finishes, read `retro.md` and show the user its candidates as one line each:
number, severity, title, files. Ask which to apply.

Applying is not part of the loop and never happens on a job branch. When the
user picks candidates, make those changes as ordinary work on a branch off
`main` (`retro/<job-id>`), editing both copies of any mirrored file
(`.claude/` and `.agents/`, `CLAUDE.md` and `ANTIGRAVITY.md`), and commit there.
The job's `stage` doesn't change.

## /factory next

Read `factory/backlog.md` and take the first `- [ ]` item. Claim it with one
Edit that replaces its exact line with `- [x] <item> → claimed`. If the Edit
fails because the line changed, another session claimed it: re-read the backlog
and try the next `- [ ]` item. If none is left, say so and stop.

Run `/factory <item>`, and once step 1 has given it a job id, replace `claimed`
on its backlog line with the job id. When the item ends with
`(spec: <path>)`, the feature is the text before it and the spec-writer prompt
gets ` Spec: <path>` (see step 3).

## /factory retro <job-id>

The job must be `merged` or `needs-human`. Run **Retro** for it, overwriting any
earlier `retro.md`.

## /factory approve <job-id>

The job must be in `needs-human`. Run **Merge** with that job id.

## /factory rework <job-id> <note>

The job must be in `needs-human`.

1. Write the note, verbatim, to `factory/jobs/<job-id>/rework-<k>.md`, where `k`
   is the next unused number.
2. Set `stage: "build"`.
3. Spawn a fresh `builder` named `builder-<job-id>` with the prompt
   `<paths> Rework: read rework-<k>.md and address it, then update build.md for round N+1. Port: <port>.`
   (`N` is the job's last round.) A rework run gets a fresh `MAX_RESUMES`.
4. Continue from **Build check**, exactly like a new job.

## Reporting

Keep the user posted with one short line per transition, for example
`003-rate-limiting: round 2, security CHANGES, ux/ui/code PASS → resuming builder`.
When the job ends, say whether it merged or needs a human, and why.
