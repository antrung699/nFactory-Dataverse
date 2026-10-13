# Windows install reference

Windows 10/11, x64. Run commands in PowerShell. `pac` and DevKit run natively
here, so no wrappers. After a `winget` install, a tool may not be on `PATH`
until the terminal restarts: check the full path, or ask the user to restart
Claude Code.

Paths used everywhere else:

| Name | Path |
|---|---|
| `<pac>` | `pac` (`%USERPROFILE%\.dotnet\tools\pac.exe`) |
| `<devkit>` | `%USERPROFILE%\.dotnet\tools\devkit.exe` |
| `<dataverse>` | `%APPDATA%\npm\dataverse.cmd` |
| MCP `PATH` for `dataverse-<org>` | not needed: the server inherits the user `PATH` |

Write absolute paths in every MCP config (`C:\\Users\\<you>\\...` with escaped
backslashes in JSON). In `.mcp.json`, `${USERPROFILE}` and `${APPDATA}` also work.

## Tools, in install order

| # | Tool | Check | Install |
|---|---|---|---|
| 1 | winget | `winget --version` | User installs "App Installer" from the Microsoft Store |
| 2 | Git, GitHub CLI | `git --version`, `gh --version` | `winget install -e --id Git.Git`, `winget install -e --id GitHub.cli` |
| 3 | Node.js LTS | `node --version` (≥ 20) | `winget install -e --id OpenJS.NodeJS.LTS` |
| 4 | Python 3.14 | `py -3.14 --version` | `winget install -e --id Python.Python.3.14` |
| 5 | .NET 8 SDK (plugin builds) | `dotnet --list-sdks` shows `8.` | `winget install -e --id Microsoft.DotNet.SDK.8` |
| 6 | .NET 10 runtimes (DevKit) | `dotnet --list-runtimes` shows `Microsoft.NETCore.App 10.` | `winget install -e --id Microsoft.DotNet.Runtime.10`, `winget install -e --id Microsoft.DotNet.AspNetCore.10` |
| 7 | PAC CLI | `pac` prints a banner | `dotnet tool install --global Microsoft.PowerApps.CLI.Tool` |
| 8 | DevKit CLI | `devkit --help` prints the DevKit banner | `dotnet tool install --global DynamicsCrm.DevKit.Cli` |
| 9 | Dataverse CLI | `dataverse auth --help` exits 0 (there is no `--version`) | `npm install -g @microsoft/dataverse` |
| 10 | Python venv for the Dataverse plugin | `$HOME\.venvs\dv\Scripts\python -c "from PowerPlatform.Dataverse.client import DataverseClient; import pandas, msal, msal_extensions, azure.identity"` | `py -3.14 -m venv $HOME\.venvs\dv; & $HOME\.venvs\dv\Scripts\pip install --upgrade azure-identity requests PowerPlatform-Dataverse-Client pandas msal msal-extensions` |

Use `dotnet tool update --global <id>` when a tool is installed but old.

## Windows-only extras

- Plugin Registration Tool: `pac tool prt` opens it. `CLAUDE.md` describes
  registration through the Web API because macOS has no PRT; on Windows either
  works, but keep the Web API steps so agents stay platform-neutral.
- Some `CLAUDE.md` setup lines are macOS paths (`~/.dotnet`,
  `/usr/local/share/dotnet`). On Windows use plain `dotnet` and `pac`.
