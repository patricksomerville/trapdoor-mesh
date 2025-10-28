#!/usr/bin/env python3
"""Render launch agent and Cloudflare configuration files from config/trapdoor.json."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from string import Template
from typing import Dict, Any


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "trapdoor.json"
TEMPLATE_DIR = BASE_DIR / "templates"


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _render_template(template_path: Path, mapping: Dict[str, str]) -> str:
    template = Template(template_path.read_text(encoding="utf-8"))
    return template.safe_substitute(mapping)


def render(config_path: Path) -> None:
    cfg = _load_json(config_path)

    app_cfg = cfg["app"]
    auth_cfg = cfg["auth"]
    launch_cfg = cfg["launch_agents"]
    cf_cfg = cfg["cloudflare"]

    log_dir = Path(launch_cfg["log_dir"])

    localproxy_mapping = {
        "LOCALPROXY_LABEL": launch_cfg["localproxy_label"],
        "PYTHON_PATH": launch_cfg["python_path"],
        "SERVER_PATH": launch_cfg["server_path"],
        "WORKING_DIR": launch_cfg["working_directory"],
        "PATH_ENV": launch_cfg["path_env"],
        "BACKEND": app_cfg["backend"],
        "MODEL": app_cfg["model"],
        "AUTH_TOKEN_FILE": auth_cfg["token_file"],
        "BASE_DIR": app_cfg["base_dir"],
        "ALLOW_ABSOLUTE": "1" if app_cfg.get("allow_absolute", False) else "0",
        "ALLOW_SUDO": "1" if app_cfg.get("allow_sudo", False) else "0",
        "DEFAULT_SYSTEM_PROMPT": html.escape(app_cfg.get("default_system_prompt", "")),
        "PORT": str(app_cfg["port"]),
        "LOG_DIR": str(log_dir),
    }

    cloudflare_mapping = {
        "CLOUDFLARE_LABEL": launch_cfg["cloudflared_label"],
        "CLOUDFLARE_TOKEN": cf_cfg["token"],
        "CLOUDFLARED_BIN": launch_cfg["cloudflared_bin"],
        "PATH_ENV": launch_cfg["path_env"],
        "LOG_DIR": str(log_dir),
    }

    cloudflared_cfg_mapping = {
        "TUNNEL_ID": cf_cfg["tunnel_id"],
        "CONFIG_DIR": cf_cfg["config_dir"],
        "HOSTNAME": cf_cfg["hostname"],
        "PORT": str(app_cfg["port"]),
    }

    outputs = {
        "com.trapdoor.localproxy.plist.tmpl": BASE_DIR / "plists" / "com.trapdoor.localproxy.plist",
        "com.trapdoor.cloudflared.plist.tmpl": BASE_DIR / "plists" / "com.trapdoor.cloudflared.plist",
        "cloudflared.config.yml.tmpl": BASE_DIR / "config" / "cloudflared.config.yml",
    }

    for template_name, target_path in outputs.items():
        template_path = TEMPLATE_DIR / template_name
        if template_name == "com.trapdoor.localproxy.plist.tmpl":
            rendered = _render_template(template_path, localproxy_mapping)
        elif template_name == "com.trapdoor.cloudflared.plist.tmpl":
            rendered = _render_template(template_path, cloudflare_mapping)
        else:
            rendered = _render_template(template_path, cloudflared_cfg_mapping)

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(rendered, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render config and plist files from trapdoor.json.")
    parser.add_argument(
        "--config",
        dest="config_path",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the configuration JSON file (default: config/trapdoor.json)",
    )
    args = parser.parse_args()
    render(args.config_path)


if __name__ == "__main__":
    main()
