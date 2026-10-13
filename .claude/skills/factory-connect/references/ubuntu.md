# Ubuntu install reference

Ubuntu 22.04 or 24.04, x86_64 (check `uname -m`). Run commands in bash. `pac`
and DevKit ship x64 builds only, so on `aarch64` stop and tell the user: there
is no supported way to run them natively. Steps that use `sudo` go to the user:
give the exact command and ask them to run it with `! <command>`.

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
`PATH` (check `echo $PATH`). Append a missing `export PATH=...` line once, to
`~/.profile` (and `~/.bashrc` if it exists, since non-login shells skip `.profile`).

## Tools, in install order

| # | Tool | Check | Install |
|---|---|---|---|
| 1 | Base packages | `dpkg -s curl unzip ca-certificates software-properties-common` | User runs `! sudo apt update && sudo apt install -y curl unzip ca-certificates software-properties-common` |
| 2 | Git, GitHub CLI | `git --version`, `gh --version` | User runs `! sudo apt install -y git gh` |
| 3 | Node.js LTS | `node --version` (≥ 20) | User runs `! curl -fsSL https://deb.nodesource.com/setup_lts.x \| sudo -E bash - && sudo apt install -y nodejs` |
| 4 | Python 3.14 | `python3.14 --version` | User runs `! sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt install -y python3.14 python3.14-venv` (system Python is too old) |
| 5 | .NET 8 SDK (plugin builds) | `dotnet --list-sdks` shows `8.` | User runs `! sudo apt install -y dotnet-sdk-8.0` |
| 6 | .NET 10 runtimes (for `pac`, DevKit) | `~/.dotnet/dotnet --list-runtimes` shows `Microsoft.NETCore.App 10.` and `Microsoft.AspNetCore.App 10.` | see **.NET 10 runtimes** |
| 7 | PAC CLI | `~/.local/bin/pac` prints a banner | see **PAC** |
| 8 | DevKit CLI | `~/.local/bin/devkit --help` prints the DevKit banner | see **DevKit** |
| 9 | Dataverse CLI | `~/.npm-global/bin/dataverse auth --help` exits 0 (there is no `--version`) | `npm install -g --prefix ~/.npm-global @microsoft/dataverse` |
| 10 | Python venv for the Dataverse plugin | `~/.venvs/dv/bin/python -c "from PowerPlatform.Dataverse.client import DataverseClient; import pandas, msal, msal_extensions, azure.identity"` | `python3.14 -m venv ~/.venvs/dv && ~/.venvs/dv/bin/pip install --upgrade azure-identity requests PowerPlatform-Dataverse-Client pandas msal msal-extensions` |

## .NET 10 runtimes

```sh
curl -sSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
bash /tmp/dotnet-install.sh --channel 10.0 --runtime dotnet --install-dir ~/.dotnet
bash /tmp/dotnet-install.sh --channel 10.0 --runtime aspnetcore --install-dir ~/.dotnet
```

## PAC

`dotnet tool install Microsoft.PowerApps.CLI.Tool` is Windows-only. On Linux
unpack the NuGet package and run `pac.dll` with the .NET 10 runtime:

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
```

## DevKit

DevKit (`DynamicsCrm.DevKit.Cli`, https://github.com/phuocle/Dynamics-Crm-DevKit)
targets net10.0. Install it as a .NET global tool with the .NET 8 SDK, then run
it through a wrapper that uses the .NET 10 runtime from `~/.dotnet`:

```sh
dotnet tool install --global DynamicsCrm.DevKit.Cli \
  || dotnet tool update --global DynamicsCrm.DevKit.Cli
cat > ~/.local/bin/devkit <<'SH'
#!/bin/bash
dll=$(ls -d "$HOME"/.dotnet/tools/.store/dynamicscrm.devkit.cli/*/dynamicscrm.devkit.cli/*/tools/net10.0/any/DynamicsCrm.DevKit.Cli.dll | sort -V | tail -1)
exec "$HOME/.dotnet/dotnet" "$dll" "$@"
SH
chmod +x ~/.local/bin/devkit
```

## Ubuntu-only notes

- **Sign-in on a machine without a browser** (SSH, server): `pac auth create
  --environment <url> --deviceCode` prints a code to enter on another device.
  `dataverse auth create` and DevKit's interactive sign-in need a browser on
  the same machine; on a headless box, sign in from a desktop session first or
  ask the user how they want to proceed.
- **Token cache**: `msal-extensions` stores tokens in the Secret Service
  keyring. Without a desktop session install `gnome-keyring` and `libsecret-1-0`
  (user runs `! sudo apt install -y gnome-keyring libsecret-1-0`), or the
  Python scripts fail to cache the token.
- `CLAUDE.md` setup lines with macOS paths (`/usr/local/share/dotnet`,
  `~/.dotnet` as the only runtime location) differ here: the .NET 8 SDK is the
  apt one (plain `dotnet`), the .NET 10 runtimes are in `~/.dotnet`.
