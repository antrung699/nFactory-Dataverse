# {{TITLE}} — Antigravity Agent Guide

Customizations for Dynamics 365 Customer Engagement (Dataverse), developed and maintained by Antigravity and automated agent workflows.

---

## 1. What Gets Built

| Area | Path | Build / Test Commands |
|---|---|---|
| **Solution** (tables, forms, views, business rules, apps) | `solution/src/` (unpacked) | `pac solution pack --zipfile out/{{SOLUTION}}.zip --folder solution/src` |
| **C# Plugins** | `plugins/{{PLUGINS}}.sln`<br>• `plugins/{{PLUGINS}}/` (plugin)<br>• `plugins/{{PLUGINS}}.Tests/` (xUnit) | `cd plugins && dotnet build {{PLUGINS}}.sln`<br>`cd plugins && dotnet test {{PLUGINS}}.sln` |
| **PCF Controls** | `pcf/<ControlName>/` | `npm ci`, `npm run build`, `npm test` |
| **Web Resources** (JS / HTML) | `webresources/` | `npm run lint`, `npm test` |
| **Power Automate Flows** | `solution/src/Workflows/` | Edited as unpacked solution files |
| **Data Migration** | `migration/` | Scripts + mapping docs; **never run against prod without a human** |

> **Note**: Create folders as the first job needs them; do not scaffold empty directories.

---

## 2. Environment & Tooling Setup

Run the `factory-connect` skill (`.agents/skills/factory-connect/`) to set up a machine (macOS, Windows or Ubuntu) or switch to another dev environment; it installs and checks the tools, sign-ins and MCP servers. Install details per OS: `.claude/skills/factory-connect/references/`.

- **Security Rule**: Never commit credentials, connection strings, or `.env` files to git.

---

## 3. Environments & Boundaries

- **Dev Environment URL**: `{{URL}}`
- **Solution Name**: `{{SOLUTION}}` (Display name: "{{SOLUTION_DISPLAY}}")
- **Publisher Prefix**: `{{PREFIX}}` (use on all new schema names, entities, and attributes).
- **Environment Boundary**:
  - **Agents touch the DEV environment only.**
  - Test and production deployments are **strictly human-only**.

---

## 4. Development Conventions & Workflow

### Solution Packaging & Git Source of Truth
- **Source of truth is the unpacked solution in git** (`solution/src/`). Never hand-edit a packed `.zip`.
- **Syncing from Dev**:
  ```sh
  pac solution export --name {{SOLUTION}} --path out/ --managed false
  pac solution unpack --zipfile out/{{SOLUTION}}.zip --folder solution/src
  ```
  Review the diff carefully; keep it minimal and eliminate unrelated churn from re-export.
- `pac` is the **only** mechanism through which solution changes reach git or other environments.

### Dataverse Plugin Skills & Operations
- `dv-query`: Read-only queries.
- `dv-metadata` & `dv-data`: Write to **dev environment only**. Every schema change must be exported and unpacked to appear as a git diff.
- `dv-security`, `dv-admin`, and any write outside dev: **Human-only**.

### Dataverse MCP Servers (order of use)
1. **`devkit-dev`** (DynamicsCrm.DevKit, `devkit mcp devkit-dev`): use first for everything it covers (tables, columns, relationships, choices, forms, views, apps, commands, ribbons, web resources, environment variables, publish, records, FetchXML, plugin/flow/workflow inspection, trace logs, system jobs, audit).
2. **`dataverse-{{ORG}}`** (`@microsoft/dataverse mcp`): fallback only for what devkit lacks (Dataverse SQL `read_query`, schema/Custom API keyword `search`/`describe`, `search_data`, file columns, `invoke_api` for Custom APIs).
3. `dv-*` skills: last.
- Both servers point at dev. **Human-only**: devkit `manage_role` and `execute_webapi`; dataverse `delete_table` and the skill tools (`upsert_skill`, `create_skill_resource`, `delete_skill`).
- Never pass `include_config=true` to `get_plugins` or `include_token=true` to `whoami`.
- Each factory agent in `.agents/agents/` lists the MCP tools it may use. Read-only agents call `manage_*` tools with `list`/`detail` only; only `builder` writes.
- devkit writes backups to `.devkit/` (git-ignored); never commit them.

### C# Plugins
- Register plugin steps with explicit stage, mode, and filtering attributes.
- Keep plugins idempotent and check `context.Depth` to avoid infinite recursion.
- Never hard-code GUIDs or environment URLs.
- **Plugin Registration in Dev (macOS)**:
  - Since the Plugin Registration Tool is unavailable on macOS, build with the .NET 8 SDK:
    ```sh
    dotnet build plugins/{{PLUGINS}}/{{PLUGINS}}.csproj -c Release
    ```
  - First registration runs through the Web API (`dataverse api request` or `scripts/auth.py`) with header `MSCRM.SolutionUniqueName: {{SOLUTION}}`:
    1. `POST pluginassemblies` (`content` = base64 of `{{PLUGINS}}.dll`, `isolationmode` 2, `sourcetype` 0)
    2. `POST plugintypes` bound to the assembly
    3. `POST sdkmessageprocessingsteps` (`stage`, `mode`, `asyncautodelete`, `sdkmessageid`, `sdkmessagefilterid`, `eventhandler_plugintype`)
    4. Step images: `POST sdkmessageprocessingstepimages` (`name`, `entityalias`, `imagetype` 0 pre / 1 post, `messagepropertyname` `Target`, `attributes`, bound `sdkmessageprocessingstepid`)
  - Pushing a rebuilt dll to the already registered assembly: `PATCH pluginassemblies(<id>)` with body `{"content": "<base64 of {{PLUGINS}}.dll>"}` (same header, keep version 1.0.0.0), then `POST plugintypes` for any new class. `dataverse api request` wants a relative path without a leading slash (`--path "api/data/v9.2/..."`).
  - After registration, export and unpack the solution:
    - Assembly lands in `solution/src/PluginAssemblies/`
    - Step lands in `solution/src/SdkMessageProcessingSteps/`

### Customization Principles
- **Configuration over Code**: Prefer out-of-the-box configuration (business rules, Power Automate flows) over custom code unless explicitly specified.
- **Web Resources**:
  - Use `Xrm.WebApi` for Dataverse access.
  - Do not use unsupported DOM manipulation on model-driven forms.
  - Never include inline secrets or credentials.
- **Branching & Commits**:
  - Commit on feature / job branches (e.g. `factory/<job-id>`).
  - Merges to `main` are gated by review and approver sign-off.

---

## 5. UI Review & Testing Checks

- There is no standalone web app in this repository.
- UI reviews are conducted via:
  1. Model-driven app forms in the dev environment.
  2. PCF control test harness:
     ```sh
     cd pcf/<ControlName> && npm start watch
     ```
- Reviewers evaluate changes based on the unpacked git diff and the PCF test harness when no live form session is available.

---

## 6. Antigravity Agent Guidelines

When operating as Antigravity in this repository:
1. **Tool Usage**:
   - Execute builds and tests via `run_command` in the appropriate subdirectory (e.g., `plugins/`, `pcf/<ControlName>/`).
   - Inspect files with `view_file` before making targeted modifications with `replace_file_content`.
   - Preserve existing comments, docstrings, and formatting standards.
2. **Subagents & Delegation**:
   - When running multi-stage factory workflows (e.g. `spec-writer`, `builder`, `reviewer-code`, `reviewer-security`, `reviewer-ux`, `reviewer-ui`, `approver`, `retro`), use `invoke_subagent` to orchestrate parallel tasks cleanly.
3. **MCP Tooling**:
   - MCP servers for Antigravity are configured in `~/.gemini/config/mcp_config.json`, linked from `~/.gemini/antigravity/mcp_config.json` (Claude Code uses `.mcp.json`): `devkit-dev` first, `dataverse-{{ORG}}` as fallback. See "Dataverse MCP Servers" above.
4. **Safety & Verification**:
   - Always run `dotnet test` or relevant test suites after modifying code.
   - Never push directly to `main` without testing and review.
