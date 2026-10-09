"""Non-mutating dependency and gateway diagnostics for every supported OS."""
from __future__ import annotations
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from .ngrok import ngrok_version, NgrokError
from .state import load_config, load_runtime, state_dir

def diagnose() -> dict:
    config = load_config()
    items = []
    def add(name, ok, detail, fix=""):
        items.append({"name": name, "ok": bool(ok), "detail": str(detail), "fix": fix})
    add("python", sys.version_info >= (3, 11), platform.python_version(), "Install Python 3.12 or use a bundled CTUN package.")
    try:
        v = importlib.metadata.version("mcp")
        add("mcp-sdk", True, v)
    except importlib.metadata.PackageNotFoundError:
        add("mcp-sdk", False, "not installed", "Reinstall CTUN with pipx or a platform package.")
    binary = str(config.get("ngrok_bin") or "ngrok")
    try:
        add("ngrok", True, ngrok_version(binary))
    except (NgrokError, OSError, subprocess.TimeoutExpired) as exc:
        hint = "brew install --cask ngrok" if sys.platform == "darwin" else ("winget install Ngrok.Ngrok" if sys.platform == "win32" else "Install ngrok via its official Linux repository")
        add("ngrok", False, str(exc), hint)
    runtime = load_runtime()
    add("ngrok-authorization", bool(config.get("public_url") or runtime.get("ngrok_ready")),
        "Configured public URL or active ngrok tunnel" if (config.get("public_url") or runtime.get("ngrok_ready")) else "Not verified",
        "Run ngrok config add-authtoken <TOKEN>, then ctun setup. A configured URL alone does not prove authorization.")
    add("gateway", bool(runtime.get("ngrok_ready")), "ready" if runtime.get("ngrok_ready") else "not running/ready",
        "Run ctun setup after installing and authenticating ngrok.")
    return {"platform": platform.system(), "state_dir": str(state_dir()), "checks": items,
            "ok": all(x["ok"] for x in items if x["name"] in ("python", "mcp-sdk", "ngrok"))}

def print_diagnostics(json_mode=False):
    result = diagnose()
    if json_mode:
        print(json.dumps(result, indent=2))
    else:
        print("CTUN doctor -", result["platform"])
        for x in result["checks"]:
            print(("OK" if x["ok"] else "WARN") + " " + x["name"] + ": " + x["detail"])
            if not x["ok"] and x["fix"]:
                print("    " + x["fix"])
    return 0 if result["ok"] else 2
