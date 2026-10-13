# nFactory Dataverse

Customizations for Dynamics 365 Customer Engagement (Dataverse), built through an
agent-driven "software factory" in Claude Code and Antigravity. Each feature goes
through spec → build → review → approve, on its own `factory/<job-id>` branch.

Project rules, conventions and environment details live in [`CLAUDE.md`](CLAUDE.md)
(and [`ANTIGRAVITY.md`](ANTIGRAVITY.md)). This README is the quick start.

## Set up

Open this folder in Claude Code and run `/factory-connect`. It installs and checks
the tools (macOS, Windows or Ubuntu), signs in, creates the solution in dev if missing,
and registers the MCP servers.

Manual install, with every link (base tools, .NET, PAC CLI, DevKit NuGet package, Dataverse CLI,
the `mattpocock-skills` and `dataverse` Claude Code plugins, sign-in, MCP, troubleshooting):
**[`docs/SETUP.md`](docs/SETUP.md)**.

**Order: install, validate, then configure.** The repo ships with placeholders, not real values:

| Placeholder | Meaning |
|---|---|
| `YOUR_ORG` / `https://YOUR_ORG.crm5.dynamics.com` | your dev environment (first label of the URL) |
| `YOUR_SOLUTION` / `Your Solution Display Name` | solution unique name and display name |
| `YOUR_PREFIX` | publisher prefix (2 to 8 lowercase letters) |
| `YOUR_PLUGINS` | plugin project name |

1. Install the tools and plugins, then validate them: steps 2 to 7 of [`docs/SETUP.md`](docs/SETUP.md).
2. Only after every check passes, configure your environment (step 8): run `/factory-connect`
   and enter your dev URL, solution and publisher. It replaces the placeholders everywhere,
   signs you in and registers the MCP servers.

Until then `/mcp` shows the two servers as failed; that is expected.

Never commit credentials, connection strings or `.env` files.

## Using the factory

| Command | What it does |
|---|---|
| `/factory <feature>` | Run a new job for a feature request (mention docs to grill with docs) |
| `/factory next` | Build the first unchecked item in `factory/backlog.md` |
| `/factory approve <job-id>` | Human approval of an escalated job |
| `/factory rework <job-id> <note>` | Send a job back to the builder with a note |
| `/factory retro <job-id>` | Rerun the retrospective for a finished job |
| `/factory-connect` | Set up a machine or switch dev environment |

Dashboard:

```sh
cd factory && python3 -m http.server 8000
# open http://localhost:8000/dashboard.html
```

## Safety rules

- Agents touch the **dev** environment only. Test and prod deploys are human-only.
- `dv-security`, `dv-admin` and any write outside dev are human-only.
- Commits go on the factory job branch; the approver gates merges to `main`.
