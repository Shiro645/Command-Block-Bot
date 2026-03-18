from __future__ import annotations

from mcrcon import MCRcon

from utils.config import load_config


def rcon_command(command: str) -> str:
    cfg = load_config()
    host = cfg["minecraft"]["rcon_host"]
    port = int(cfg["minecraft"]["rcon_port"])
    password = cfg["minecraft"]["rcon_password"]

    with MCRcon(host, password, port=port) as mcr:
        return mcr.command(command)