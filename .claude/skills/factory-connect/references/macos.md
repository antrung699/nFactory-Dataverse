# macOS install reference

Works on Apple Silicon and Intel. On Apple Silicon, `pac` and DevKit have no
native arm64 build, hence the wrappers below. Check `uname -m` (`arm64` or
`x86_64`) first.

Paths used everywhere else:

| Name | Path |
|---|---|
| `<pac>` | `~/.local/bin/pac` (wrapper) |
| `<devkit>` | `~/.local/bin/devkit` (wrapper) |
| `<dataverse>` | `~/.npm-global/bin/dataverse` |
| MCP `PATH` for `dataverse-<org>` | `$HOME/.dotnet:$HOME/.npm-global/bin:/usr/local/bin:/usr/bin:/bin` |

In `.mcp.json`, write `${HOME}/...` for these paths; in the user-level and
Antigravity configs, write the expanded absolute path.

Make sure `~/.local/bin`, `~/.npm-global/bin` and `~/.dotnet/tools` are on
`PATH` (check `echo $PATH`; they may be set in `~/.zprofile` or `~/.zshrc`).
Append a missing `export PATH=...` line once, to `~/.zprofile`.

## Tools, in install order

| # | Tool | Check | Install |
|---|---|---|---|
| 1 | Xcode command line tools | `xcode-select -p` | User runs `! xcode-select --install` (GUI) |
| 2 | Homebrew | `brew --version` | User runs the install line from https://brew.sh |
| 3 | Rosetta (Apple Silicon only) | `pgrep -q oahd` or `arch -x86_64 /usr/bin/true` | User runs `! softwareupdate --install-rosetta --agree-to-license` |
| 4 | Git, GitHub CLI | `git --version`, `gh --version` | `brew install git gh` |
| 5 | Node.js LTS | `node --version` (≥ 20) | `brew install node` |
| 6 | Python 3.14 | `python3.14 --version` | `brew install python@3.14` (system 3.9 is too old) |
| 7 | .NET 8 SDK (plugin builds) | `/usr/local/share/dotnet/dotnet --list-sdks` shows `8.` | User runs the arm64 or x64 `.pkg` from https://dotnet.microsoft.com/download/dotnet/8.0 (needs admin) |
| 8 | .NET 10 runtimes (for `pac`) | `~/.dotnet/dotnet --list-runtimes` shows `Microsoft.NETCore.App 10.` and `Microsoft.AspNetCore.App 10.` | see **.NET 10 runtimes** |
| 9 | PAC CLI | `~/.local/bin/pac` prints a banner | see **PAC** |
| 10 | x64 .NET 10 runtime (DevKit, Apple Silicon only) | `~/.dotnet-x64/dotnet --list-runtimes` shows `10.` | see **DevKit** |
| 11 | DevKit CLI | `~/.local/bin/devkit --help` prints the DevKit banner | see **DevKit** |
| 12 | Dataverse CLI | `~/.npm-global/bin/dataverse auth --help` exits 0 (there is no `--version`) | `npm install -g --prefix ~/.npm-global @microsoft/dataverse` |
| 13 | Python venv for the Dataverse plugin | `~/.venvs/dv/bin/python -c "from PowerPlatform.Dataverse.client import DataverseClient; import pandas, msal, msal_extensions, azure.identity"` | `python3.14 -m venv ~/.venvs/dv && ~/.venvs/dv/bin/pip install --upgrade azure-identity requests PowerPlatform-Dataverse-Client pandas msal msal-extensions` |

## .NET 10 runtimes

```sh
curl -sSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
bash /tmp/dotnet-install.sh --channel 10.0 --runtime dotnet --install-dir ~/.dotnet
bash /tmp/dotnet-install.sh --channel 10.0 --runtime aspnetcore --install-dir ~/.dotnet
```

## PAC

No brew or `dotnet tool` package runs on arm64, so unpack the NuGet package
and run `pac.dll` with the .NET 10 runtime:

```sh
mkdir -p ~/.pac/pkg ~/.local/bin
id=microsoft.powerapps.cli.core.osx-x64
ver=$(curl -s https://api.nuget.org/v3-flatcontainer/$id/index.json | python3 -c "import json,sys;print(json.load(sys.stdin)['versions'][-1])")
curl -sSL https://api.nuget.org/v3-flatcontainer/$id/$ver/$id.$ver.nupkg -o /tmp/pac.nupkg
unzip -oq /tmp/pac.nupkg -d ~/.pac/pkg
cat > ~/.local/bin/pac <<'SH'
#!/bin/sh
DOTNET_ROOT="$HOME/.dotnet" exec "$HOME/.dotnet/dotnet" "$HOME/.pac/pkg/tools/pac.dll" "$@"
SH
chmod +x ~/.local/bin/pac
```

On Intel Macs the same works; `dotnet tool install --global Microsoft.PowerApps.CLI.Tool` is an alternative.

## DevKit

DevKit (`DynamicsCrm.DevKit.Cli`, https://github.com/phuocle/Dynamics-Crm-DevKit)
targets net10.0 and is x64-only. Install it as a .NET global tool, then run it
through a wrapper with an x64 runtime (under Rosetta on Apple Silicon):

```sh
/usr/local/share/dotnet/dotnet tool install --global DynamicsCrm.DevKit.Cli \
  || /usr/local/share/dotnet/dotnet tool update --global DynamicsCrm.DevKit.Cli
# Apple Silicon only: x64 .NET 10 runtime
arch -x86_64 bash /tmp/dotnet-install.sh --channel 10.0 --runtime dotnet --architecture x64 --install-dir ~/.dotnet-x64
cat > ~/.local/bin/devkit <<'SH'
#!/bin/bash
# DevKit CLI is x64-only; run it with the x64 .NET runtime (Rosetta).
dll=$(ls -d "$HOME"/.dotnet/tools/.store/dynamicscrm.devkit.cli/*/dynamicscrm.devkit.cli/*/tools/net10.0/any/DynamicsCrm.DevKit.Cli.dll | sort -V | tail -1)
exec "$HOME/.dotnet-x64/dotnet" "$dll" "$@"
SH
chmod +x ~/.local/bin/devkit
```

On Intel Macs, point the wrapper at `~/.dotnet/dotnet` instead of
`~/.dotnet-x64/dotnet` and skip the x64 runtime.
