# chatgpt-tun

A detached, multi-project local MCP gateway for ChatGPT.

The design is deliberately **one connector, one tunnel, many local project roots**:

```text
ChatGPT custom connector
        |
        | one stable URL, configured once
        v
https://<your-dev-domain>.ngrok.app/<secret>/mcp
        |
        v
ngrok agent on your machine
        |
        v
chatgpt-tun daemon on 127.0.0.1:8765
        |
        +-- kikimora
        +-- game
        +-- sprite-processing
        +-- any other enabled folder
```

There is no tunnel per project. `ctun up` only changes the global project registry. The detached daemon and ngrok endpoint stay the same, so the ChatGPT connector URL does not change.

## Requirements

- Linux/macOS/Windows
- Python 3.11+
- an ngrok account and the ngrok agent
- ngrok authenticated once with its normal local config

Install ngrok using the official instructions, then add your token **locally**:

```bash
ngrok config add-authtoken '<YOUR_TOKEN>'
```

The token never needs to be passed to `chatgpt-tun`.

## Install

The intended global installation is with `pipx`:

```bash
pipx install git+https://github.com/smollgreymouse/chatgpt-tun.git
```

This installs both command names:

```bash
ctun
chatgpt-tun
```

Upgrade later with:

```bash
pipx upgrade chatgpt-tun
```

## One-time setup

Run:

```bash
ctun setup
```

On the first successful start, ngrok assigns the account's development domain. `chatgpt-tun` discovers it from the local ngrok agent, stores it, and from then on starts ngrok with that same URL.

The output contains a connector URL similar to:

```text
https://example.ngrok.app/4A1v...random-secret...qQ/mcp
```

Configure the ChatGPT custom connector with that **full URL exactly once**.

The random path component is generated locally and persisted. It is intentionally part of the URL: this project exposes powerful local-development tools and does not assume ChatGPT can send a custom static Authorization header. Treat the connector URL as a secret. If it leaks, remove the local state/config or rotate the token in a future release and update the connector.

## Daily use

In any project directory:

```bash
cd ~/Projects/game
ctun up
```

The project name defaults to the folder name, so the example becomes `game`.

Open another terminal in another project:

```bash
cd ~/Projects/kikimora
ctun up
```

Both projects are now available through the **same** MCP endpoint.

The command returns after enabling the project. The daemon is detached, so that terminal can be closed.

Disable the current project from any later terminal opened in that directory:

```bash
ctun down
```

Or disable it globally by registered name from anywhere:

```bash
ctun down game
```

Re-enable it:

```bash
ctun up ~/Projects/game
```

If two different directories have the same basename, give one an explicit registry name:

```bash
ctun up ~/work/client/game --name client-game
```

## Global registry

The registry is not tied to the terminal that started a project.

```bash
ctun list
ctun list --active
ctun list --json
```

Example:

```text
ON   game               /home/me/Projects/game
ON   kikimora           /home/me/Projects/kikimora
OFF  sprite-processing  /home/me/Projects/sprite-processing
```

`down` only disables a project. It remains in the registry.

Remove a disabled record completely with:

```bash
ctun remove game
```

## Gateway lifecycle

```bash
ctun status
ctun url
ctun logs
ctun logs -f
ctun restart
ctun shutdown
```

`ctun shutdown` stops the shared MCP daemon and ngrok process but preserves the project registry. A later `ctun up` automatically starts the gateway again.

## Configuration and state

By default all persistent runtime state lives under:

```text
~/.local/state/chatgpt-tun/
```

The important files are:

```text
config.json    stable ngrok origin, local port and secret MCP path
registry.json  every known project and whether it is enabled
runtime.json   detached daemon/ngrok PIDs and live status
daemon.log     daemon and ngrok logs
```

For tests or isolated installations, set `CHATGPT_TUN_HOME`.

Inspect configuration:

```bash
ctun config
```

If automatic ngrok URL discovery is unavailable, pin the already-assigned development URL manually:

```bash
ctun config --public-url https://your-assigned-domain.ngrok.app
ctun restart
```

## MCP tools

The single MCP server exposes the active registry dynamically. Projects can be enabled or disabled while ChatGPT remains connected.

Current tools:

- `list_projects`
- `list_directory`
- `read_text`
- `write_text`
- `replace_text`
- `make_directory`
- `remove_path`
- `search_text`
- `run_command`

Every workspace tool requires a `project` argument. File operations resolve paths against that project's root and reject `..`, absolute paths, and symlink traversal outside the root.

`run_command` does **not** invoke a shell, but it is intentionally a powerful developer tool: an executable launched inside a project can still access anything that the local OS user can access. The secret connector URL therefore must be handled like a credential.

Disabling a project with `ctun down` takes effect immediately for subsequent MCP calls.

## Why one tunnel instead of one per project?

A tunnel-per-project design forces either multiple ChatGPT connectors or changing the connector whenever the active folder changes. This project keeps the network identity stable and moves project selection into the MCP protocol itself.

The persistent objects are:

```text
one ngrok development domain
one secret MCP URL
one detached local daemon
one global project registry
```

Project activation is just registry state.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
```

The implementation uses the current MCP Python SDK v2 and Streamable HTTP.
