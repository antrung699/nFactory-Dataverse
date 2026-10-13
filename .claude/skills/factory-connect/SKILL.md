---
name: factory-connect
description: Set up a machine and a Dataverse dev environment for D365 Customer Engagement development with the factory. Use when the user types /factory-connect, sets up a new or existing machine, switches the repo to another D365 environment, or the factory's tools, sign-ins or MCP servers are missing or broken.
---

# Factory connect

Gets a machine ready for D365 CE development with this repo's factory: tools,
sign-ins, MCP servers, the dev solution, and the repo files that name them.

Every step checks first and skips what is already done, so a rerun repairs
instead of reinstalling. Say what each step found and did, one line each.
Never print, log or commit secrets, tokens or `.env` values.

## 1. Ask how to run

Ask with AskUserQuestion, all three in one call. Detect the OS first
(`uname -s`: `Darwin` is macOS, `Linux` is Ubuntu when `/etc/os-release` says
`ID=ubuntu`; or `$env:OS` in PowerShell) and mark the detected one
"(Recommended)".

| Question | Options |
|---|---|
| Operating system | **macOS** · **Windows** · **Ubuntu** |
| Machine | **New machine**: install every missing tool. · **Same machine**: tools should be there; check them and offer to install only what is missing. |
| Scope | **Global**: tools, sign-in and MCP servers at user level, usable from any folder; touches no repo files. · **Project**: MCP servers in this repo's `.mcp.json`, plus `.env`, the solution baseline and the repo files that name the environment. · **New project folder**: create a new repo with the factory in it, then do Project setup there. |

Then read the install reference for the OS: [references/macos.md](references/macos.md),
[references/windows.md](references/windows.md) or
[references/ubuntu.md](references/ubuntu.md). Run shell commands in that
OS's shell (zsh on macOS, bash on Ubuntu, PowerShell on Windows).

## 2. Tools

Check every tool in the reference's table, then report all missing ones at
once. New machine: install them in the table's order (later tools depend on
earlier ones). Same machine: list what's missing and ask before installing.
A step that needs admin rights or a GUI installer (Rosetta, Xcode tools, a
`.pkg`/MSI, `sudo apt`) goes to the user: tell them the exact command and type `! <command>`
to run it here, then re-check.

Then the Claude Code plugins. Check with `/plugin` output or by looking for
the skills `dataverse:dv-connect` and `mattpocock-skills:grilling` in the
available skills. You can't install plugins yourself: when one is missing,
ask the user to run `/plugin` and install it (`dataverse` from the
`claude-plugins-official` marketplace; `mattpocock-skills` from their
claude.ai account or its marketplace), then restart the session.

Stop here if any required tool is still missing.

## 3. Environment

Now ask for the environment (AskUserQuestion, with the current values from
`.env`, `CLAUDE.md` or the user-level MCP config as the recommended options
when they exist):

- **Dev URL**, e.g. `https://<org>.crm5.dynamics.com`. Use the regional host
  (`crm5`, `crm4`, ...): the CLIs sometimes print `crm`, which may not resolve.
  Check it resolves (`curl -sI <url>` returns any HTTP status).
- **Solution**: unique name and display name.
- **Publisher**: unique name, display name, prefix (2–8 lowercase letters,
  not `mscrm`) and choice value prefix (10000–99999).

`<org>` below is the first label of the host (`YOUR_ORG`).

Only dev is ever touched. If the user gives a URL they call test or prod,
stop: those are human-only.

## New project folder

Only for that scope; do it after step 3, before step 4.

1. Ask for the folder path (default: a sibling of this repo) and a project
   title. The folder must not exist or must be empty.
2. Run the scaffold (Python 3 from step 2; on Windows `py -3.14`, on Ubuntu `python3.14`):

   ```
   python3 .claude/skills/factory-connect/scripts/scaffold.py --target <dir> \
     --title "<title>" --url <url> --solution <solution> \
     --solution-display "<display name>" --prefix <prefix>
   ```

   It copies the factory (agents, factory and factory-connect skills,
   dashboard, `scripts/auth.py`, `.gitignore`), renames this repo's
   solution, prefix, plugin project and `dataverse-<org>` server to the new
   ones, and writes `CLAUDE.md`, `ANTIGRAVITY.md` and `README.md` from
   `templates/`. It copies no solution files, code or job history.
3. `git init -b main` in `<dir>` and commit everything as the initial commit.
4. From here on, every step runs in `<dir>` (start each shell command with
   `cd <dir> && `), with Project scope. Step 7's environment switch is
   already done by the scaffold; skip it.

## 4. Sign in

Each sign-in opens a browser; tell the user before you start it. Skip one that
already matches the URL.

1. **PAC**: `pac auth list`; if no profile for the URL,
   `pac auth create --environment <url> --name <org>`, then
   `pac auth select --name <org>` and check `pac org who`. `pac` has one
   active profile per machine: tell the user that other projects on this
   machine need `pac auth select --name <their profile>` before their `pac`
   commands (`.env` `PAC_AUTH_PROFILE` names each project's profile).
2. **Dataverse CLI**: `dataverse auth who`; if no profile for the URL,
   `dataverse auth create --environment <url>`.
3. **DevKit** signs in interactively the first time its MCP server starts
   (step 6); nothing to do here.

## 5. Solution in dev

Check with the Dataverse CLI (`--target dataverse --environment <url>` on
every call; relative paths, no leading slash; quote `$` for the shell):

```
dataverse api request --target dataverse --environment <url> --path "api/data/v9.2/solutions?\$filter=uniquename eq '<solution>'&\$select=solutionid,version"
dataverse api request --target dataverse --environment <url> --path "api/data/v9.2/publishers?\$filter=customizationprefix eq '<prefix>'&\$select=publisherid,uniquename"
```

When the solution is missing, show the user exactly what you will create
(publisher if missing, then the solution) and ask before creating:

```
--method POST --path "api/data/v9.2/publishers"  --body {"uniquename","friendlyname","customizationprefix","customizationoptionvalueprefix"}
--method POST --path "api/data/v9.2/solutions"   --body {"uniquename","friendlyname","version":"1.0.0.0",
                                                       "publisherid@odata.bind":"/publishers(<publisherid>)"}
```

If a publisher with that prefix exists under another name, reuse it and say so.
Never create or change anything else, and never touch security roles.

## 6. MCP servers

Two servers, both pointed at dev. The names matter: agents' tool allowlists
use them.

| Server | Command |
|---|---|
| `devkit-dev` | `<devkit> mcp devkit-dev --auth Interactive --url <url>` |
| `dataverse-<org>` | `<dataverse> mcp <url>`, env `PATH` that includes the .NET and npm-global bins (see the OS reference) |

Use absolute paths for `<devkit>` and `<dataverse>` from the OS reference.

- **Project scope**: write both into `.mcp.json` (keep other servers in it).
- **Global scope**: `claude mcp add --scope user <name> -- <command...>`
  (add `-e PATH=...` for `dataverse-<org>`). Remove a stale same-named server
  first (`claude mcp remove --scope user <name>`).
- **Antigravity** (either scope, if `~/.gemini` exists): the same two servers
  in `~/.gemini/config/mcp_config.json`; keep its other servers. Antigravity
  has only this one global config: if a server with the same name points at
  another URL (e.g. `devkit-dev` for another project), ask before overwriting it.

Then tell the user to restart Claude Code (MCP servers load at start), and on
restart check with `mcp__devkit-dev__whoami` and a one-row
`mcp__dataverse-<org>__read_query`. DevKit's first start opens a browser
sign-in.

## 7. Project files (Project and New project folder scopes)

1. **`.env`** (gitignored): `DATAVERSE_URL`, `TENANT_ID` (from
   `pac org who` or `dataverse auth who`), `SOLUTION_NAME`, `PUBLISHER_PREFIX`,
   `PAC_AUTH_PROFILE`. Keep keys it already has (`MCP_CLIENT_ID`,
   `DATAVERSE_PLUGIN_*` belong to `dv-connect`). If `.env` is missing those,
   run `dataverse:dv-connect` for the Dataverse-only parts and skip its MCP
   step (step 6 already did it).
2. **Environment switch.** A fresh clone of the template carries the placeholders `YOUR_ORG`,
   `YOUR_SOLUTION`, `YOUR_PREFIX` and `YOUR_PLUGINS`: treat them as the old values below. When the URL, solution or prefix differ from what
   `CLAUDE.md` says, show the user the list of changes and ask, then:
   - Rename the old `dataverse-<oldorg>` server name to `dataverse-<org>` in
     every file that has it: `grep -rl "dataverse-<oldorg>" --exclude-dir=.git
     --exclude-dir=solution --exclude-dir=factory --exclude-dir=logs .`
     (agent `tools:` lists in `.claude/agents/`, `.agents/agents/`,
     `CLAUDE.md`, `ANTIGRAVITY.md`, `README.md`, `.claude/settings.local.json`).
   - Update the URL, solution and prefix in the Environments and Conventions
     sections of `CLAUDE.md` and `ANTIGRAVITY.md`.
   - Leave `logs/` and `factory/` history alone.
3. **Baseline.** If `solution/src/` is empty or missing, or holds a different
   solution, export and unpack (see `CLAUDE.md` Conventions):
   `pac solution export --name <solution> --path out/ --managed false`, then
   `pac solution unpack --zipfile out/<solution>.zip --folder solution/src`.
   If it holds the same solution, don't re-export (no churn).
4. **Build check**: `dotnet build` the `.sln` in `plugins/` when it exists.
5. Commit the repo changes on a branch `setup/<org>` (never `.env`), and ask
   before merging to `main`. In a new project folder, commit straight to `main`
   (there is nothing to review against yet).

## 8. Report

End with a table: each tool, sign-in, server and file, and its state
(`ok`, `installed`, `created`, `skipped`, `needs you`). Then the next step:
restart Claude Code if MCP config changed (for a new project folder: open
Claude Code in that folder), then `/factory <feature>`.
