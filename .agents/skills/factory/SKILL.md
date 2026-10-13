---
name: factory
description: Run the software factory. Use when the user types /factory <feature>, /factory next, /factory approve <job-id>, /factory rework <job-id> <note>, or /factory retro <job-id>. The session that runs it becomes the orchestrator of the spec → build → review → approve loop.
---

# Factory

You are the orchestrator for one job. You run the loop below, spawn every agent,
and keep `factory/board.json` and your job's `factory/jobs/<job-id>/job.json` updated.
You never write code, specs, reviews, or decisions yourself. Agents do the work
and each writes one file; you move the job along and manage state.

## The loop

```
feature → spec-writer ⇄ user → builder → [security, ux, ui, code] → WAIT FOR ALL
                           ▲                                      │
                           └──── any CHANGES: resume builder ◄────┤
                                                                  ▼ all PASS
                                     merge to main ◄─ APPROVE ─ approver ─ ESCALATE → needs-human
                                           └──────────────► retro ◄──────────────┘
```

| Step         | Agent Type            | Role Description           | Writes                                      |
| ------------ | --------------------- | -------------------------- | ------------------------------------------- |
| spec         | `spec-writer`         | Factory Spec Writer        | `grill.md`, `spec.md` (+ slice specs)       |
| tickets      | `ticket-writer`       | Factory Ticket Writer      | `tickets.md`, `tickets/NN-<slug>.md`        |
| build        | `builder` (one per ticket) | Factory Builder       | `build.md` + commits on `factory/<job-id>`  |
| review       | `reviewer-security`   | Security Reviewer          | `round-N/review-security.md`                |
|              | `reviewer-ux`         | UX Reviewer                | `round-N/review-ux.md`                      |
|              | `reviewer-ui`         | UI Design Reviewer         | `round-N/review-ui.md`                      |
|              | `reviewer-code`       | Code Reviewer              | `round-N/review-code.md`                    |
| approve      | `approver`            | Factory Approver           | `decision.md`                               |
| retro        | `retro`               | Factory Retro              | `retro.md` (suggestions only)               |

`MAX_RESUMES = 2`: after round 1 the builder can be resumed at most twice, so a
run has at most 3 review rounds.

Every agent reads `ANTIGRAVITY.md` (or `AGENTS.md`) for the repo's setup, dev environment,
validation commands, and conventions.

## Parallel jobs

Every job runs in its own git worktree on its own branch (`factory/<job-id>`), so
several jobs can run at once.
- Your orchestrator session stays in the main checkout. Agents work in the job's worktree.
  Only **Merge** touches the main checkout.
- Job state lives in `factory/jobs/<job-id>/` and `factory/board.json` in the main checkout.
- Ports: With `n` the job number (`001` → 1), `builder` gets `5100 + 10n`,
  `reviewer-ux` gets `5101 + 10n`, and `reviewer-ui` gets `5102 + 10n`.
- Spawn only the agents in this checkout's agent folder (`.claude/agents/`, or `.agents/agents/`).
  A trial agent on a feature branch runs in that branch's own factory, never in a job started from `main`.

## Files & State

```
<repo>/factory/board.json                      durable board state (drives dashboard)
<repo>/factory/specs/<job-id>-<k>-<slug>.md    slice specs a spec-writer split off, queued in the backlog
<repo>/factory/backlog.md                      queue for /factory next
<repo>/factory/jobs/<job-id>/job.json          the job's individual state
<repo>/factory/jobs/<job-id>/grill.md         grilling rounds and the user's answers
<repo>/factory/jobs/<job-id>/spec.md
<repo>/factory/jobs/<job-id>/tickets.md             the ticket index and build order
<repo>/factory/jobs/<job-id>/tickets/NN-<slug>.md   one file per ticket
<repo>/factory/jobs/<job-id>/build.md
<repo>/factory/jobs/<job-id>/rework-<k>.md     written from /factory rework
<repo>/factory/jobs/<job-id>/round-<N>/review-{security,ux,ui,code}.md
<repo>/factory/jobs/<job-id>/decision.md
<repo>/factory/jobs/<job-id>/retro.md
<repo>/../<name>-factory/<job-id>/             the job's worktree, on factory/<job-id>
```

### board.json and job.json

Update both `factory/jobs/<job-id>/job.json` and `factory/board.json` on each state change:

```json
{
  "jobs": [
    {
      "id": "001-case-feedback-sentiment",
      "feature": "Case customer feedback table with sentiment evaluation",
      "branch": "factory/001-case-feedback-sentiment",
      "worktree": "/abs/path/to/d365-sales-implementation-factory/001-case-feedback-sentiment",
      "stage": "review",
      "round": 1,
      "reviews": {
        "security": "CHANGES",
        "ux": "PASS",
        "ui": "pending",
        "code": "PASS"
      }
    }
  ]
}
```

- `stage`: `spec`, `build`, `review`, `approve`, `merged`, `needs-human`.
- `reviews`: `pending`, `PASS`, or `CHANGES`.
- `tickets` (optional, once approved): map of ticket id to `pending`, `building` or `done`. The dashboard ignores it.

### Agent Prompts

Every agent prompt begins with the job's paths:
`Job folder: <repo>/factory/jobs/<job-id>/. Worktree: <worktree>. Branch: factory/<job-id>.`
(Referred to as `<paths>` below).

---

## Workflow Steps

### 1. /factory <feature>

1. **Create the job:**
   - Find the next 3-digit number after the highest numbered folder in `factory/jobs/` (`001` if none) and make a kebab-case slug: `002-quote-pdf-generation`.
   - Run `mkdir factory/jobs/<job-id>` in `<repo>`.
   - Set worktree path: `$(cd .. && pwd)/$(basename "$PWD")-factory/<job-id>`.
   - Write initial `job.json` and update `board.json` with `stage: "spec"`, `round: 0`, and reviews `pending`.
2. **Worktree:**
   - Create worktree: `git worktree add -b factory/<job-id> <worktree> main`.
3. **Spec:**
   - Invoke subagent `spec-writer` via `invoke_subagent`:
     `TypeName: "spec-writer"`, `Role: "Factory Spec Writer"`, `Prompt: "<paths> Feature: <feature, verbatim>"`
     (from `/factory next`, append ` Spec: <slice spec path>` when the backlog item has one).
   - Save the spec-writer's conversation ID; go to **Grilling** and come back once `<job folder>/spec.md` exists.
4. **Tickets:** go to **Tickets**; come back once `tickets.md` starts with `STATUS: APPROVED`.
5. **Build:** go to **Build tickets**.

### Grilling

The spec-writer grills the user before it writes the spec, but it can't talk to
the user: you relay. The job stays in `stage: "spec"` throughout.

1. When the spec-writer finishes and `spec.md` doesn't exist yet, its final
   message is a grilling round (or the closing summary asking the user to
   confirm). Show it to the user verbatim and wait for their reply. Never answer
   a question yourself.
2. Append the reply, verbatim, to `<job folder>/grill.md` under `### Answers`,
   then resume the same spec-writer using `send_message`: `User answers: <reply, verbatim>`.
3. Repeat until `spec.md` exists. If the spec-writer finishes without `spec.md`
   and without a question for the user, stop and tell the user.
4. If its final message lists slices, tell the user which slice specs it wrote
   and which backlog lines it added. This job builds slice 1 only.

If the user abandons the feature, set `stage: "needs-human"` and leave the worktree.

### Tickets

One builder run over a whole spec takes too long, so the spec is split into
small tickets first. The stage stays `spec`.

1. Invoke subagent `ticket-writer` via `invoke_subagent`:
   `TypeName: "ticket-writer"`, `Role: "Factory Ticket Writer"`, `Prompt: "<paths>"`. Save its conversation ID.
2. Show the user its final message verbatim (numbered breakdown and suggested build order) and wait for their reply. Never answer for them.
3. If the user wants changes, append the reply, verbatim, to `<job folder>/grill.md` under `### Ticket answers`, and resume the writer using `send_message`: `User answers: <reply, verbatim>`. Repeat step 2.
4. When the user approves, resume the writer: `User approved`. Check `tickets.md` starts with `STATUS: APPROVED`, then add the `tickets` map (all `pending`) to `job.json` and `board.json`.
5. A spec that yields one ticket still goes through this step.

### Build tickets

Set `stage: "build"`. Take tickets in the order of `tickets.md`, one at a time, never in parallel (one worktree and branch). A ticket is eligible when every ticket in its `Blocked by` is `done`.

For each eligible ticket: set it to `building`, then invoke a fresh `builder`:
`TypeName: "builder"`, `Role: "Factory Builder"`, `Prompt: "<paths> Build ticket <NN>. Ticket: <job folder>/tickets/<NN>-<slug>.md. Port: <port>."`
When it finishes, go to **Build Check**. On `STATUS: READY` set the ticket to `done` and take the next. After the last ticket, start **Review round 1**.

### Build Check

Read the first line of `<job folder>/build.md`:
- `STATUS: READY`: take the next ticket, or after the last one (or after a review-fix build) proceed to **Review round N**.
- `STATUS: BLOCKED`: proceed to **Needs human**.

### Review round N

1. Set `stage: "review"`, `round: N`, and all four reviews to `pending`. Update `job.json` and `board.json`.
2. Create `<job folder>/round-<N>/`.
3. **Launch all 4 reviewers concurrently:**
   Call `invoke_subagent` once with 4 items in `Subagents`:
   - `TypeName: "reviewer-security"`, `Role: "Security Reviewer"`, `Prompt: "<paths> Review round N."`
   - `TypeName: "reviewer-ux"`, `Role: "UX Reviewer"`, `Prompt: "<paths> Review round N. Port: <port>."`
   - `TypeName: "reviewer-ui"`, `Role: "UI Reviewer"`, `Prompt: "<paths> Review round N. Port: <port>."`
   - `TypeName: "reviewer-code"`, `Role: "Code Reviewer"`, `Prompt: "<paths> Review round N."`
4. **WAIT FOR ALL:**
   - As each review finishes, read its verdict (`VERDICT: PASS` or `VERDICT: CHANGES`) from the file and immediately update `job.json` and `board.json`.
   - Ensure all four files exist: `review-security.md`, `review-ux.md`, `review-ui.md`, `review-code.md`.
5. **Decide:**
   - **All PASS**: proceed to **Approve**.
   - **Any CHANGES, resumes left (< 2 resumes):**
     - Set `stage: "build"`. Update `job.json` and `board.json`.
     - Resume the builder using `send_message` (invoke a fresh `builder` if none exists, since ticket builders finish before review; review fixes are one build, not per ticket):
       `Round N reviews are in factory/jobs/<job-id>/round-<N>/. Address every review with VERDICT: CHANGES, commit, and update build.md for round N+1.`
     - Wait for builder completion; proceed to **Build check**.
   - **Any CHANGES, no resumes left (>= 2 resumes):**
     - Write `<job folder>/decision.md`:
       ```markdown
       ESCALATE

       Review rounds exhausted. Outstanding CHANGES in round-<N>/ from: <reviewers>.
       ```
     - Proceed to **Needs human**.

### Approve

1. Set `stage: "approve"`. Update `job.json` and `board.json`.
2. Invoke subagent `approver` via `invoke_subagent`:
   `TypeName: "approver"`, `Role: "Factory Approver"`, `Prompt: "<paths> Final round: N."`.
3. Read the first line of `<job folder>/decision.md`:
   - `APPROVE`: proceed to **Merge**.
   - `ESCALATE`: proceed to **Needs human**.

### Merge

1. Verify the main checkout is clean and on `main`:
   `git status --porcelain -- . ':!factory/backlog.md' ':!factory/specs'` is empty and `git branch --show-current` is `main`.
2. If main checkout is dirty or on another branch, set `stage: "needs-human"` and notify the user to run `/factory approve <job-id>` once clean.
3. Otherwise, merge and clean up:
   ```bash
   git merge --no-ff factory/<job-id> -m "Merge factory/<job-id>"
   git worktree remove <worktree>
   git branch -d factory/<job-id>
   ```
4. Set `stage: "merged"`. Update `job.json` and `board.json`. Never push to remote.
5. Run **Retro**.

### Needs human

Set `stage: "needs-human"`. Update `job.json` and `board.json`.
The branch and worktree remain intact. Notify the user with the worktree path and quote `decision.md` or the BLOCKED reason.
Then run **Retro**, unless the job stopped during grilling.

### Retro

Runs after every job ends, merged or not, and on `/factory retro <job-id>`.
1. Invoke subagent `retro` via `invoke_subagent`:
   `TypeName: "retro"`, `Role: "Factory Retro"`, `Prompt: "<paths> Outcome: <merged | needs-human>."`
   (after a merge the worktree is gone; the paths still name the job).
2. Read `<job folder>/retro.md` and show the user its candidates, one line each:
   number, severity, title, files. Ask which to apply.
3. Applying is not part of the loop and never happens on a job branch. When the
   user picks candidates, make those changes as ordinary work on a branch off
   `main` (`retro/<job-id>`), editing both copies of any mirrored file
   (`.claude/` and `.agents/`, `CLAUDE.md` and `ANTIGRAVITY.md`), and commit there.
   The job's `stage` doesn't change.

---

## 2. /factory next

Read `factory/backlog.md` and claim the first unchecked `- [ ]` item:
1. Replace `- [ ] <item>` with `- [x] <item> → claimed`.
2. Run `/factory <item>`.
3. Once the job ID is assigned, replace `claimed` with `<job-id>`.
4. When the item ends with `(spec: <path>)`, the feature is the text before it and
   the spec-writer prompt gets ` Spec: <path>`.

## 3. /factory retro <job-id>

The job must be `merged` or `needs-human`. Run **Retro** for it, overwriting any earlier `retro.md`.

## 4. /factory approve <job-id>

The job must be in `needs-human`. Execute **Merge** for `<job-id>`.

## 5. /factory rework <job-id> <note>

The job must be in `needs-human`.
1. Write the note verbatim to `factory/jobs/<job-id>/rework-<k>.md` (next unused `k`).
2. Set `stage: "build"`. Update `job.json` and `board.json`.
3. Spawn a fresh `builder` via `invoke_subagent` with:
   `<paths> Rework: read rework-<k>.md and address it, then update build.md for round N+1. Port: <port>.`
4. A rework gets a fresh `MAX_RESUMES`. Continue from **Build check**.
