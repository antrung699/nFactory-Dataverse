# Setup guide: nFactory Dataverse on a new machine

Everything needed to run the software factory (`/factory`) against a Dynamics 365 /
Dataverse **dev** environment. Written for Ubuntu (the machine this was proven on, including
ARM64); macOS and Windows differ only in the install commands, see
`.claude/skills/factory-connect/references/`.

> Fastest path: open this folder in Claude Code and run `/factory-connect`. It checks and
> installs everything below, one line per step, then asks for your environment. This guide is the manual version and the
> reference for what each piece is and where it comes from.

## 1. What you are installing

Order of work: install the tools (2 to 6), validate them (7), and **only then configure your own
environment** (8 to 11). The repo ships with placeholders (`YOUR_ORG`, `YOUR_SOLUTION`,
`YOUR_PREFIX`, `YOUR_PLUGINS`) instead of real values.

| # | Piece | Why the factory needs it | Source |
|---|---|---|---|
| 1 | Base tools: git, GitHub CLI, curl, unzip | clone, branch, PRs | [cli.github.com](https://cli.github.com/) |
| 2 | Node.js 20+ (LTS) | runs the Dataverse CLI | [nodejs.org/en/download](https://nodejs.org/en/download) |
| 3 | Python 3.14 | `scripts/auth.py`, the Dataverse plugin's scripts | [deadsnakes PPA](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa) (Ubuntu) |
| 4 | .NET 8 SDK | builds plugins | [Ubuntu install](https://learn.microsoft.com/dotnet/core/install/linux-ubuntu) |
| 5 | .NET 10 runtimes (`~/.dotnet`) | run `pac` and DevKit | [dotnet-install.sh](https://dot.net/v1/dotnet-install.sh) |
| 6 | PAC CLI | solution export/unpack/pack, auth | [docs](https://learn.microsoft.com/power-platform/developer/cli/introduction), [NuGet linux-x64 core package](https://www.nuget.org/packages/Microsoft.PowerApps.CLI.Core.linux-x64) |
| 7 | DevKit CLI + MCP server (`devkit-dev`) | the agents' main Dataverse tools | [NuGet](https://www.nuget.org/packages/DynamicsCrm.DevKit.Cli), [GitHub](https://github.com/phuocle/Dynamics-Crm-DevKit) |
| 8 | Dataverse CLI (`@microsoft/dataverse`) | `dataverse-<org>` MCP server, API calls | [npm](https://www.npmjs.com/package/@microsoft/dataverse) |
| 9 | Python venv `~/.venvs/dv` | Dataverse SDK for scripts | pip packages listed below |
| 10 | Claude Code plugins `mattpocock-skills`, `dataverse` | grilling/spec skills, `dv-*` skills | [mattpocock/skills](https://github.com/mattpocock/skills), [microsoft/Dataverse-skills](https://github.com/microsoft/Dataverse-skills) |

Claude Code plugin docs: [Discover and install plugins](https://code.claude.com/docs/en/discover-plugins),
[Plugins](https://code.claude.com/docs/en/plugins).

## 2. Base tools (Ubuntu 22.04 / 24.04)

```sh
sudo apt update
sudo apt install -y curl unzip ca-certificates software-properties-common git gh
# Node.js LTS
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt install -y nodejs
# Python 3.14 (system Python is too old)
sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt install -y python3.14 python3.14-venv
# .NET 8 SDK (plugin builds)
sudo apt install -y dotnet-sdk-8.0
```

Put the tool folders on `PATH` once (`~/.profile`, and `~/.bashrc` if present):

```sh
export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$HOME/.dotnet/tools:$PATH"
```

### .NET 10 runtimes (needed by `pac` and DevKit)

```sh
curl -sSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
bash /tmp/dotnet-install.sh --channel 10.0 --runtime dotnet     --install-dir ~/.dotnet
bash /tmp/dotnet-install.sh --channel 10.0 --runtime aspnetcore --install-dir ~/.dotnet
```

## 3. PAC CLI

`dotnet tool install Microsoft.PowerApps.CLI.Tool` is Windows-only. On Linux unpack the
NuGet core package and run `pac.dll` on the .NET 10 runtime. This was verified on ARM64
too, because `pac.dll` is managed code.

```sh
mkdir -p ~/.pac/pkg ~/.local/bin
id=microsoft.powerapps.cli.core.linux-x64
ver=$(curl -s https://api.nuget.org/v3-flatcontainer/$id/index.json | python3 -c "import json,sys;print(json.load(sys.stdin)['versions'][-1])")
curl -sSL https://api.nuget.org/v3-flatcontainer/$id/$ver/$id.$ver.nupkg -o /tmp/pac.nupkg
unzip -oq /tmp/pac.nupkg -d ~/.pac/pkg
cat > ~/.local/bin/pac <<'SH'
#!/bin/sh
DOTNET_ROOT="$HOME/.dotnet" exec "$HOME/.dotnet/dotnet" "$HOME/.pac/pkg/tools/pac.dll" "$@"
SH
chmod +x ~/.local/bin/pac
pac    # prints the Microsoft PowerPlatform CLI banner
```

macOS arm64 uses package `Microsoft.PowerApps.CLI.Core.osx-x64`; Windows can use
`dotnet tool install --global Microsoft.PowerApps.CLI.Tool`.

## 4. DevKit CLI (NuGet) and its MCP server

Package: [`DynamicsCrm.DevKit.Cli`](https://www.nuget.org/packages/DynamicsCrm.DevKit.Cli)
(targets net10.0). Source and release builds:
[phuocle/Dynamics-Crm-DevKit](https://github.com/phuocle/Dynamics-Crm-DevKit).

**x86-64 machine with the .NET 8 SDK:**

```sh
dotnet tool install --global DynamicsCrm.DevKit.Cli     # or: dotnet tool update --global ...
```

**ARM64 (aarch64) machine, or a machine with only the .NET runtimes (no SDK):** older NuGet
builds (4.12.x) were compiled x86-64-only and crash on ARM with
`The assembly architecture is not compatible with the current process architecture`.
Builds from 4.44.44.44 are AnyCPU. Until NuGet carries one, take the package from the
GitHub `v5.5` branch and unpack it by hand:

```sh
v=4.44.44.44
mkdir -p /tmp/devkit && cd /tmp/devkit
curl -sL -O https://raw.githubusercontent.com/phuocle/Dynamics-Crm-DevKit/v5.5/v5/Published/$v/DynamicsCrm.DevKit.Cli.$v.nupkg
unzip -q DynamicsCrm.DevKit.Cli.$v.nupkg -d x
d=~/.dotnet/tools/.store/dynamicscrm.devkit.cli/$v/dynamicscrm.devkit.cli/$v
mkdir -p "$d" && cp -r x/tools "$d/"
```

Note: the `build-manifest.json` next to that package can be stale (it describes an earlier
build), so its hash will not match. Folder: `v5/Published/4.44.44.44` on branch `v5.5`
([browse](https://github.com/phuocle/Dynamics-Crm-DevKit/tree/v5.5/v5/Published/4.44.44.44)).

Wrapper that runs the newest installed version on the .NET 10 runtime:

```sh
cat > ~/.local/bin/devkit <<'SH'
#!/bin/bash
dll=$(ls -d "$HOME"/.dotnet/tools/.store/dynamicscrm.devkit.cli/*/dynamicscrm.devkit.cli/*/tools/net10.0/any/DynamicsCrm.DevKit.Cli.dll | sort -V | tail -1)
exec "$HOME/.dotnet/dotnet" "$dll" "$@"
SH
chmod +x ~/.local/bin/devkit
devkit --version        # e.g. 4.44.44.44 Build: ...
devkit mcp --setup-guide   # DevKit's own MCP configuration guide
```

## 5. Dataverse CLI and Python venv

```sh
npm install -g --prefix ~/.npm-global @microsoft/dataverse
~/.npm-global/bin/dataverse auth --help      # exits 0 when installed

python3.14 -m venv ~/.venvs/dv
~/.venvs/dv/bin/pip install --upgrade azure-identity requests PowerPlatform-Dataverse-Client pandas msal msal-extensions
```

Optional but recommended for the token cache: `sudo apt install -y gnome-keyring libsecret-1-0`
(without it the Dataverse CLI falls back to a plaintext token cache and warns).

## 6. Claude Code plugins

Run these inside Claude Code (you cannot install plugins from a script), then restart the session:

```
/plugin install mattpocock-skills@claude-plugins-official
/plugin install dataverse@claude-plugins-official
```

If the marketplace is not added yet: `/plugin marketplace add anthropics/claude-plugins-official`.
Or open `/plugin` and pick them from the list. Check afterwards that the skills
`mattpocock-skills:grilling` and `dataverse:dv-connect` appear in the skill list.

## 7. Validate the installed tools (no environment needed yet)

Do this **before** configuring anything environment-specific. Every line must succeed.

```sh
git --version; gh --version; node --version; python3.14 --version
dotnet --list-sdks                         # needs 8.x
~/.dotnet/dotnet --list-runtimes           # needs Microsoft.NETCore.App 10.x and Microsoft.AspNetCore.App 10.x
pac                                        # prints the PowerPlatform CLI banner
devkit --version                           # prints a version, e.g. 4.44.44.44
~/.npm-global/bin/dataverse auth --help    # exits 0
~/.venvs/dv/bin/python -c "from PowerPlatform.Dataverse.client import DataverseClient; import pandas, msal, msal_extensions, azure.identity; print('ok')"
```

In Claude Code, also check that the skills `mattpocock-skills:grilling` and `dataverse:dv-connect`
are listed. Only continue when all of these pass.

## 8. Configure your environment (last step)

The project files ship with placeholders so that no real environment, tenant or account is
stored in git. Replace them once, after step 7 passes.

| Placeholder | Replace with | Example |
|---|---|---|
| `YOUR_ORG` | first label of your dev URL; also names the `dataverse-YOUR_ORG` MCP server | `org12345678` |
| `https://YOUR_ORG.crm5.dynamics.com` | your dev environment URL; use the regional host the environment really has (`crm`, `crm4`, `crm5`, ...) | `https://org12345678.crm5.dynamics.com` |
| `YOUR_SOLUTION` / `Your Solution Display Name` | solution unique name and display name | `ContosoSalesDEV` / "Contoso Sales DEV" |
| `YOUR_PREFIX` | publisher prefix, 2 to 8 lowercase letters, not `mscrm` | `con` |
| `YOUR_PLUGINS` | plugin project name | `ConPlugins` |

Files that contain them: `.mcp.json`, `CLAUDE.md`, `ANTIGRAVITY.md`, `README.md`,
`.claude/agents/*.md`, `.agents/agents/*.md`, `.claude/skills/factory-connect/SKILL.md`.

**Easiest:** open this folder in Claude Code and run `/factory-connect`. It asks for the dev URL,
solution and publisher, shows you the list of changes, renames the placeholders everywhere
(including the agents' `mcp__dataverse-<org>__*` tool allowlists), signs you in, and creates the
solution in dev if it is missing.

**By hand:**

```sh
export ORG=org12345678 SOL=ContosoSalesDEV SOLDISPLAY="Contoso Sales DEV" PFX=con PLG=ConPlugins
grep -rlE 'YOUR_ORG|YOUR_SOLUTION|Your Solution Display Name|YOUR_PREFIX|YOUR_PLUGINS' . --exclude-dir=.git --exclude=SETUP.md \
  | xargs sed -i -e "s/YOUR_ORG/$ORG/g" -e "s/Your Solution Display Name/$SOLDISPLAY/g" \
                 -e "s/YOUR_SOLUTION/$SOL/g" -e "s/YOUR_PREFIX/$PFX/g" -e "s/YOUR_PLUGINS/$PLG/g"
```

Keep your real values out of the shared template: do this in a clone for your project, not in
the template repository.

## 9. Sign in (one browser or device-code login per tool)

Each tool keeps its own cache, so each needs its own sign-in. On a headless box (SSH) add
`--deviceCode`: it prints a code to enter at https://login.microsoft.com/device from any machine.

```sh
URL=https://YOUR_ORG.crm5.dynamics.com        # the dev URL you configured in step 8
pac auth create --environment $URL --name YOUR_ORG --deviceCode
pac auth select --name YOUR_ORG && pac org who
dataverse auth create --environment $URL       # add --deviceCode when headless
dataverse auth who
```

(Use your real values for `URL` and the profile name.) `pac` has one active profile per machine.
If another project also uses `pac`, run `pac auth select --name <profile>` before its commands.

DevKit signs in when its MCP server starts (next step).

## 10. MCP servers

`.mcp.json` in this repo registers both servers, pointed at the dev environment you configured in
step 8. Until then they point at the placeholder URL and show as failed in `/mcp`; that is expected.
The server names matter: the agents' tool allowlists use `mcp__devkit-dev__*` and
`mcp__dataverse-<org>__*`.

| Server | Command |
|---|---|
| `devkit-dev` | `~/.local/bin/devkit mcp devkit-dev --auth Interactive --url <dev-url>` |
| `dataverse-<org>` | `~/.npm-global/bin/dataverse mcp <dev-url>` with `PATH` including `~/.dotnet` and `~/.npm-global/bin` |

Restart Claude Code after changing `.mcp.json`, then run `/mcp` to check both are connected.

**DevKit sign-in over SSH / headless.** `--auth Interactive` opens a browser, and Claude Code
gives an MCP server only 30 seconds to start. If it times out with `CONNECT_TIMEOUT`:

- Use `--auth DeviceCode` in the `devkit-dev` args (the code is printed in the server log), or
- run Claude Code inside a desktop session, or set `DISPLAY` and `XAUTHORITY` in that
  server's `env` block to a live desktop (for example an RDP session), and/or
- start Claude Code with a longer limit: `MCP_TIMEOUT=180000 claude`.

Other auth modes (`devkit mcp --help`): `ClientSecret`, `FromPac --pacprofile <name>`, `OAuth`, `AD`.
Do not commit machine-specific `DISPLAY` values.

## 11. Verify end to end

In Claude Code, call the `whoami` tool of `devkit-dev` and check the user, environment and
roles. Then:

```sh
DATAVERSE_URL=$URL ~/.venvs/dv/bin/python scripts/auth.py --check     # prints REACHABLE
```

Optionally create `.env` (gitignored) with `DATAVERSE_URL`, `TENANT_ID`, `SOLUTION_NAME`,
`PUBLISHER_PREFIX`, `PAC_AUTH_PROFILE`; `dataverse:dv-connect` can write it.

To point at a different environment later, run `/factory-connect` again. Only **dev** is ever
touched by agents; test and prod deploys are human-only.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `devkit-dev` `CONNECTION_CLOSED` right after start | The CLI crashed. Run `devkit --version` in a shell. On ARM with a 4.12.x build: `assembly architecture is not compatible`, so install an AnyCPU build (section 4). |
| `devkit-dev` `CONNECT_TIMEOUT` (30000 ms) | Interactive sign-in is waiting for a browser. See "DevKit sign-in over SSH". |
| `dotnet tool install` says "No .NET SDKs were found" | Only runtimes are installed in `~/.dotnet`. Install the .NET 8 SDK from apt, or unpack the nupkg by hand (section 4). |
| `pac` says "No profiles were found" | `pac auth create ... --deviceCode` (section 7). |
| `dataverse` warns `Encrypted token cache not available` | Install `gnome-keyring libsecret-1-0`. Works without, with a plaintext cache. |
| `crm.dynamics.com` does not resolve | Use the regional host the environment really has (`crm5`, `crm4`, ...). |
| `python3.14: command not found` | Add the deadsnakes PPA (section 2). |
| MCP tools missing after `.mcp.json` edits | Restart Claude Code, then `/mcp`. |

## Using the factory

See [`README.md`](../README.md) for the `/factory` commands, and [`CLAUDE.md`](../CLAUDE.md) for the
project rules.
