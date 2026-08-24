"""`manfred` — repo CLI for running the brain server.

Installed as a console script (`uv tool install --editable packages/brain-server`)
so `manfred brain up` works from anywhere, in an isolated environment that
already has the server's dependencies.

    manfred brain up        # start the server in the background
    manfred brain up -f     # ...in the foreground (Ctrl-C to stop)
    manfred brain down      # stop it
    manfred brain restart   # down + up
    manfred brain status    # running? + a /healthz probe
    manfred brain logs      # tail the server logs

Config resolves from (highest first): BRAIN_* environment variables, an optional
dotenv file (`$BRAIN_ENV_FILE`, else `~/.brain/env`, else the package's
`.brain.env`), then defaults (vault `~/brain-vault`, loopback `:8765`, no token =
dev mode). The vault is auto-created from the bundled template on first `up`.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# ---- config resolution -----------------------------------------------------


def load_env_file(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE dotenv file (supports `export`, # comments, quotes)."""
    values: dict[str, str] = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        values[key] = val
    return values


def _defaults() -> dict[str, str]:
    return {
        "BRAIN_VAULT": str(Path.home() / "brain-vault"),
        "BRAIN_HOST": "127.0.0.1",
        "BRAIN_PORT": "8765",
        "BRAIN_TOKEN": "",
    }


def resolve_settings(environ, env_files) -> dict:
    """Merge defaults < first existing dotenv file < BRAIN_* env vars."""
    values = _defaults()
    for f in env_files:
        if f and Path(f).exists():
            values.update(load_env_file(Path(f)))
            break
    for key, val in environ.items():
        if key.startswith("BRAIN_"):
            values[key] = val
    vault = Path(values["BRAIN_VAULT"]).expanduser()
    db = Path(values.get("BRAIN_DB", str(vault / ".brain" / "index.db"))).expanduser()
    return {
        "vault": vault,
        "db": db,
        "host": values["BRAIN_HOST"],
        "port": int(values["BRAIN_PORT"]),
        "token": values.get("BRAIN_TOKEN", ""),
    }


def env_file_candidates(environ) -> list[Path]:
    cands: list[Path] = []
    if environ.get("BRAIN_ENV_FILE"):
        cands.append(Path(environ["BRAIN_ENV_FILE"]).expanduser())
    cands.append(state_dir() / "env")
    cands.append(Path(__file__).resolve().parent.parent / ".brain.env")  # editable dev
    return cands


# ---- runtime state (pidfile + logs) ----------------------------------------


def state_dir() -> Path:
    return Path(os.environ.get("BRAIN_STATE", str(Path.home() / ".brain"))).expanduser()


def pidfile() -> Path:
    return state_dir() / "server.pid"


def log_paths() -> tuple[Path, Path]:
    log_dir = state_dir() / "log"
    return log_dir / "brain.out.log", log_dir / "brain.err.log"


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, ValueError):
        return False
    except PermissionError:
        return True  # exists, owned by someone else
    return True


def read_pid(pf: Path) -> int | None:
    try:
        return int(Path(pf).read_text().strip())
    except (OSError, ValueError):
        return None


def running_pid(pf: Path | None = None) -> int | None:
    pid = read_pid(pf or pidfile())
    return pid if pid is not None and pid_alive(pid) else None


# ---- vault bootstrap -------------------------------------------------------


def template_dir() -> Path | None:
    here = Path(__file__).resolve().parent
    for candidate in (here / "vault-template", here.parent / "vault-template"):
        if candidate.is_dir():
            return candidate
    return None


def ensure_vault(vault: Path, template: Path | None) -> None:
    if vault.exists():
        return
    if template and template.is_dir():
        shutil.copytree(template, vault)
    else:
        for d in ("inbox", "longterm", "archive", "_meta"):
            (vault / d).mkdir(parents=True, exist_ok=True)
    (vault / ".brain").mkdir(parents=True, exist_ok=True)


# ---- server process control ------------------------------------------------


def build_server_env(settings: dict, base: dict | None = None) -> dict:
    env = dict(os.environ if base is None else base)
    env["BRAIN_VAULT"] = str(settings["vault"])
    env["BRAIN_DB"] = str(settings["db"])
    env["BRAIN_HOST"] = settings["host"]
    env["BRAIN_PORT"] = str(settings["port"])
    if settings["token"]:
        env["BRAIN_TOKEN"] = settings["token"]
    else:
        env.pop("BRAIN_TOKEN", None)
    return env


def healthz(settings: dict, timeout: float = 2.0) -> str | None:
    url = f"http://{settings['host']}:{settings['port']}/healthz"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read().decode().strip()
    except OSError:
        return None


def cmd_up(settings: dict, foreground: bool = False) -> int:
    if running_pid() is not None:
        print(f"manfred: brain already running (pid {running_pid()}) "
              f"on {settings['host']}:{settings['port']}")
        return 0

    ensure_vault(settings["vault"], template_dir())
    if not settings["token"]:
        print("manfred: no BRAIN_TOKEN set — running in dev mode "
              "(auth disabled, loopback only)")

    env = build_server_env(settings)
    cmd = [sys.executable, "-m", "brain_server"]

    if foreground:
        print(f"manfred: starting brain (foreground) on "
              f"{settings['host']}:{settings['port']} — Ctrl-C to stop")
        return subprocess.call(cmd, env=env)

    out_log, err_log = log_paths()
    out_log.parent.mkdir(parents=True, exist_ok=True)
    print(f"manfred: starting brain on {settings['host']}:{settings['port']} ...")
    with open(out_log, "ab") as out, open(err_log, "ab") as err:
        # New session => the child leads its own process group, so `down` can
        # signal the whole tree (uvicorn + workers) cleanly.
        proc = subprocess.Popen(cmd, env=env, stdout=out, stderr=err,
                                start_new_session=True)
    pidfile().parent.mkdir(parents=True, exist_ok=True)
    pidfile().write_text(str(proc.pid))

    for _ in range(60):
        if healthz(settings) is not None:
            print(f"manfred: brain up (pid {proc.pid}) — "
                  f"http://{settings['host']}:{settings['port']}")
            print(f"manfred: logs at {err_log}")
            return 0
        if proc.poll() is not None:
            print("manfred: server exited during startup — last log lines:",
                  file=sys.stderr)
            _tail_to_stderr(err_log)
            pidfile().unlink(missing_ok=True)
            return 1
        time.sleep(0.5)
    print("manfred: brain did not become healthy within 30s — "
          f"see {err_log}", file=sys.stderr)
    return 1


def _tail_to_stderr(path: Path, n: int = 20) -> None:
    try:
        lines = Path(path).read_text().splitlines()[-n:]
        print("\n".join(lines), file=sys.stderr)
    except OSError:
        pass


def _terminate(pid: int) -> None:
    """SIGTERM the process group, escalate to SIGKILL if it lingers."""
    try:
        pgid = os.getpgid(pid)
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    for _ in range(20):
        if not pid_alive(pid):
            return
        time.sleep(0.25)
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except ProcessLookupError:
        pass


def cmd_down(settings: dict) -> int:
    pid = running_pid()
    if pid is None:
        pidfile().unlink(missing_ok=True)
        print("manfred: brain was not running")
        return 0
    _terminate(pid)
    pidfile().unlink(missing_ok=True)
    print("manfred: brain stopped")
    return 0


def cmd_status(settings: dict) -> int:
    pid = running_pid()
    print(f"status:  {'running (pid %d)' % pid if pid else 'stopped'}")
    print(f"url:     http://{settings['host']}:{settings['port']}")
    print(f"vault:   {settings['vault']}")
    print(f"auth:    {'enabled' if settings['token'] else 'dev mode (disabled)'}")
    health = healthz(settings)
    print(f"healthz: {health if health is not None else 'unreachable'}")
    return 0


def cmd_logs(settings: dict) -> int:
    out_log, err_log = log_paths()
    if not err_log.exists():
        print(f"manfred: no logs yet at {err_log} — start the server first",
              file=sys.stderr)
        return 1
    return subprocess.call(["tail", "-n", "50", "-f", str(err_log), str(out_log)])


# ---- dispatch --------------------------------------------------------------

_BRAIN_HELP = (
    "manfred brain — run the long-term memory server\n"
    "  up [-f|--foreground]   start the server (background, or foreground)\n"
    "  down                   stop the server\n"
    "  restart                down + up\n"
    "  status                 running? + a /healthz probe\n"
    "  logs                   tail the server logs\n"
)


def _brain(args: list[str]) -> int:
    sub = args[0] if args else "help"
    rest = args[1:]
    settings = resolve_settings(os.environ, env_file_candidates(os.environ))
    if sub == "up":
        return cmd_up(settings, foreground=any(a in ("-f", "--foreground") for a in rest))
    if sub in ("down", "stop"):
        return cmd_down(settings)
    if sub == "restart":
        cmd_down(settings)
        return cmd_up(settings, foreground=any(a in ("-f", "--foreground") for a in rest))
    if sub == "status":
        return cmd_status(settings)
    if sub == "logs":
        return cmd_logs(settings)
    if sub in ("help", "-h", "--help"):
        print(_BRAIN_HELP)
        return 0
    print(f"manfred: unknown 'brain' subcommand: {sub} "
          "(try: up, down, restart, status, logs)", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    group = argv[0] if argv else "help"
    rest = argv[1:]
    if group == "brain":
        return _brain(rest)
    if group in ("help", "-h", "--help", ""):
        print("manfred — repo CLI\nusage: manfred brain {up|down|restart|status|logs}")
        return 0
    print(f"manfred: unknown command: {group} (only 'brain' is available)",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
