"""Game of GIT entry point: launch the web UI on all interfaces."""

import socket

import uvicorn

_PORT = 8000


def _lan_ips() -> list[str]:
    """Return all non-loopback IPv4 addresses this host is reachable on.

    Combines two probes that catch different interfaces on multi-homed
    machines (VPNs, Docker bridges, WSL2): the UDP-connect trick for the
    primary routing interface, and hostname resolution for anything the
    OS has registered under our name. Either probe may fail on offline
    or misconfigured hosts — both are wrapped in try/except.
    """
    ips: set[str] = set()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.2)
            s.connect(("8.8.8.8", 80))
            ips.add(s.getsockname()[0])
    except OSError:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except socket.gaierror:
        pass

    return sorted(ip for ip in ips if not ip.startswith("127."))


def _print_banner() -> None:
    ips = _lan_ips()
    gold = "\033[1;33m"
    dim = "\033[2m"
    reset = "\033[0m"
    lines = [
        "",
        f"  {gold}Game of GIT: The Tears of DevSecOps{reset}",
        f"  {dim}─────────────────────────────────────{reset}",
    ]
    if ips:
        lines.append(f"  {dim}Play at:{reset}")
        lines.extend(f"    {gold}http://{ip}:{_PORT}{reset}" for ip in ips)
    else:
        lines.append(f"  {dim}No LAN interface detected — check your network.{reset}")
    lines.append("")
    print("\n".join(lines), flush=True)


def main() -> None:
    _print_banner()
    # Raise uvicorn's log level so its own "Uvicorn running on http://0.0.0.0:..."
    # banner doesn't clutter the LAN-first presentation. Errors still get through.
    uvicorn.run(
        "gameofgit.web.server:app",
        host="0.0.0.0",
        port=_PORT,
        reload=False,
        access_log=False,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
