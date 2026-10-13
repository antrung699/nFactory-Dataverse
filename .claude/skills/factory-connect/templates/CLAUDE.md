# {{TITLE}}

Customizations for Dynamics 365 Customer Engagement (Dataverse), built through
the software factory in `.claude/agents` and `/factory`.

## What gets built

| Area | Path | Build / test |
|---|---|---|
| Solution (tables, forms, views, business rules, apps) | `solution/src/` (unpacked) | `pac solution pack` |
| C# plugins | `plugins/{{PLUGINS}}.sln` (`{{PLUGINS}}/` plugin, `{{PLUGINS}}.Tests/` xUnit) | `cd plugins && dotnet build {{PLUGINS}}.sln`, `cd plugins && dotnet test {{PLUGINS}}.sln` |
| PCF controls | `pcf/<ControlName>/` | `npm ci`, `npm run build`, `npm test` |
| Web resources (JS/HTML) | `webresources/` | `npm run lint`, `npm test` |
| Power Automate flows | `solution/src/Workflows/` | Edited as unpacked solution files |
| Data migration | `migration/` | Scripts + mapping docs; never run against prod without a human |

Create folders as the first job needs them; don't scaffold empty ones.

## Setup

Run `/factory-connect` to set up a machine (macOS, Windows or Ubuntu) or switch to another
dev environment; it installs and checks the tools, sign-ins and MCP servers.
Install details per OS: `.claude/skills/factory-connect/references/`.

- Auth: `pac auth create --environment <DEV_URL>`. Never commit credentials,
  connection strings or `.env` files.

## Environments

- Dev environment URL: `{{URL}}`
- Solution: `{{SOLUTION}}` (display name "{{SOLUTION_DISPLAY}}")
- Only the dev environment is touched by agents. Test/prod deploys are human-only.

## Conventions

- Source of truth is the unpacked solution in git. Never hand-edit a packed `.zip`.
- Sync from dev: `pac solution export --name <Solution> --path out/ --managed false`,
  then `pac solution unpack --zipfile out/<Solution>.zip --folder solution/src`.
  Review the diff; keep it minimal (no unrelated churn from re-export).
- `pac` is the only way solution changes reach git or other environments.
- Dataverse plugin skills: `dv-query` is read-only. `dv-metadata` and `dv-data`
  write to the dev environment only, and every schema change must be exported
  and unpacked so it shows up as a git diff. `dv-security`, `dv-admin` and any
  write outside dev are human-only.
- MCP order: devkit-dev (`mcp__devkit-dev__*`) first, the Dataverse MCP
  (`mcp__dataverse-{{ORG}}__*`) only for what devkit lacks (Dataverse SQL,
  schema keyword search, file columns, invoking Custom APIs), then the `dv-*`
  skills. Both servers point at dev. Human-only: devkit `manage_role` and
  `execute_webapi`, Dataverse MCP `delete_table` and skill tools. Each factory
  agent's `tools:` list in `.claude/agents/` is its allowlist; read-only agents
  call `manage_*` tools with `list`/`detail` only.
- Use the publisher prefix on all new schema names (`{{PREFIX}}` prefix).
- Plugins: register steps with explicit stage, mode and filtering attributes;
  keep them idempotent and avoid recursion (check `Depth`); no hard-coded GUIDs or URLs.
- Plugin registration in dev (no Plugin Registration Tool on macOS): build with the
  .NET 8 SDK, e.g. `dotnet build plugins/{{PLUGINS}}/{{PLUGINS}}.csproj -c Release`.
  First registration goes through the Web API (`dataverse api request`) with header
  `MSCRM.SolutionUniqueName: {{SOLUTION}}`: POST `pluginassemblies` (`content` =
  base64 of `{{PLUGINS}}.dll`, `isolationmode` 2, `sourcetype` 0), POST `plugintypes`
  bound to the assembly, then POST `sdkmessageprocessingsteps` (stage, mode,
  `asyncautodelete`, `sdkmessageid`, `sdkmessagefilterid`, `eventhandler_plugintype`).
  Step images: POST `sdkmessageprocessingstepimages` (`name`, `entityalias`, `imagetype`
  0 pre / 1 post, `messagepropertyname` `Target`, `attributes`, bound
  `sdkmessageprocessingstepid`). A rebuilt dll goes to the already registered assembly
  with PATCH `pluginassemblies(<id>)` body `{"content": "<base64 of {{PLUGINS}}.dll>"}`
  (same header, keep version 1.0.0.0); then POST any new `plugintypes`. The CLI wants a
  relative path without a leading slash (`--path "api/data/v9.2/..."`). Then export and
  unpack the solution; the assembly lands in `solution/src/PluginAssemblies/` and
  the step in `solution/src/SdkMessageProcessingSteps/`.
- Prefer configuration (business rules, flows) over code unless the spec says otherwise.
- Web resources: no inline secrets, use `Xrm.WebApi`, no unsupported DOM access to forms.
- Commit on the factory job branch only; the approver gates merges to `main`.

## Dev server / UI checks

There is no standalone web app. UI review means a model-driven app form in the
dev environment or a PCF control in the test harness (`npm start watch` in the control folder).
Reviewers should judge from the diff and the harness when no live view exists.
