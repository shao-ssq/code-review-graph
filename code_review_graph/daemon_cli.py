"""CLI entry point for the crg-daemon multi-repo watcher.

Usage:
    crg-daemon start [--foreground]
    crg-daemon stop
    crg-daemon restart [--foreground]
    crg-daemon status
    crg-daemon logs [--repo ALIAS] [--follow] [--lines N]
    crg-daemon add <path> [--alias ALIAS]
    crg-daemon remove <path_or_alias>
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import subprocess
import sys
import time

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def _handle_start(args: argparse.Namespace) -> None:
    """Start the daemon process."""
    from .daemon import WatchDaemon, is_daemon_running, load_config, write_pid

    if is_daemon_running():
        print("错误：守护进程已在运行。")
        sys.exit(1)

    config = load_config()
    daemon = WatchDaemon(config=config)

    if not args.foreground:
        # Fork before start() creates watcher and health-check threads.
        daemon.daemonize()
    else:
        write_pid()

    try:
        if args.foreground:
            daemon._setup_signal_handlers()
        daemon.start()
        daemon.run_forever()
    finally:
        # Covers normal return, startup failure, KeyboardInterrupt, and signals.
        daemon.stop()


def _handle_stop(_args: argparse.Namespace) -> None:
    """Stop the running daemon process."""
    from .daemon import clear_pid, is_daemon_running, read_pid

    if not is_daemon_running():
        print("守护进程未在运行。")
        sys.exit(1)

    pid = read_pid()
    if pid is None:
        print("错误：无法读取守护进程 PID。")
        sys.exit(1)

    print(f"正在停止守护进程（PID {pid}）……")
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        clear_pid()
        print("守护进程已停止（进程已不存在）。")
        return
    except PermissionError:
        print(f"错误：向 PID {pid} 发送信号被拒绝。")
        sys.exit(1)

    # Wait up to 5 seconds for process to die
    for _ in range(50):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        # Still alive after 5s — send SIGKILL
        print("守护进程未优雅退出，正在发送 SIGKILL……")
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    clear_pid()
    print("守护进程已停止。")


def _handle_restart(args: argparse.Namespace) -> None:
    """Restart the daemon (stop + start)."""
    from .daemon import is_daemon_running

    if is_daemon_running():
        _handle_stop(args)
    else:
        print("守护进程未在运行，直接启动。")

    _handle_start(args)


def _handle_status(_args: argparse.Namespace) -> None:
    """Show daemon status and configuration."""
    from .daemon import is_daemon_running, load_config, load_state, pid_alive, read_pid

    config = load_config()
    running = is_daemon_running()

    if running:
        pid = read_pid()
        print(f"守护进程：运行中（PID {pid}）")
    else:
        print("守护进程：未运行")

    print(f"名称：    {config.session_name}")
    print(f"日志目录：{config.log_dir}")
    print(f"轮询间隔：{config.poll_interval}s")
    print()

    if not config.repos:
        print("尚未配置任何仓库。")
        print("用法：crg-daemon add <path> [--alias NAME]")
        return

    # Header
    alias_width = max(len(r.alias) for r in config.repos)
    alias_width = max(alias_width, 5)  # minimum "Alias" header width

    if running:
        state = load_state()
        print(f"  {'别名':<{alias_width}}  {'状态':<8}  {'PID':<8}  路径")
        print(f"  {'-' * alias_width}  {'-' * 8}  {'-' * 8}  {'-' * 40}")
        for repo in config.repos:
            entry = state.get(repo.alias, {})
            child_pid: int | None = entry.get("pid")
            alive = child_pid is not None and pid_alive(child_pid)
            status_str = "存活" if alive else "已死"
            pid_str = str(child_pid) if child_pid is not None else "-"
            print(f"  {repo.alias:<{alias_width}}  {status_str:<8}  {pid_str:<8}  {repo.path}")
    else:
        print(f"  {'别名':<{alias_width}}  路径")
        print(f"  {'-' * alias_width}  {'-' * 40}")
        for repo in config.repos:
            print(f"  {repo.alias:<{alias_width}}  {repo.path}")


def _handle_logs(args: argparse.Namespace) -> None:
    """Show daemon or per-repo log files."""
    from .daemon import load_config

    config = load_config()

    if args.repo:
        log_file = config.log_dir / f"{args.repo}.log"
    else:
        log_file = config.log_dir / "daemon.log"

    if not log_file.exists():
        print(f"未找到日志文件：{log_file}")
        sys.exit(1)

    if args.follow:
        try:
            subprocess.run(["tail", "-f", str(log_file)], check=False)
        except KeyboardInterrupt:
            pass
        return

    # Read last N lines
    lines_count = args.lines
    try:
        text = log_file.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"读取日志文件出错：{exc}")
        sys.exit(1)

    lines = text.splitlines()
    tail = lines[-lines_count:] if len(lines) > lines_count else lines
    for line in tail:
        print(line)


def _handle_add(args: argparse.Namespace) -> None:
    """Add a repository to the daemon config."""
    from .daemon import add_repo_to_config, is_daemon_running

    try:
        add_repo_to_config(args.path, alias=args.alias)
    except ValueError as exc:
        print(f"错误：{exc}")
        sys.exit(1)

    # Find the repo we just added to show confirmation
    alias = args.alias or os.path.basename(os.path.abspath(args.path))
    print(f"已添加仓库：{args.path}（别名：{alias}）")

    if is_daemon_running():
        print("守护进程将自动应用该变更。")


def _handle_remove(args: argparse.Namespace) -> None:
    """Remove a repository from the daemon config."""
    from .daemon import is_daemon_running, load_config, remove_repo_from_config

    config_before = load_config()
    count_before = len(config_before.repos)

    config_after = remove_repo_from_config(args.path_or_alias)
    count_after = len(config_after.repos)

    if count_before == count_after:
        print(f"配置中未找到匹配 '{args.path_or_alias}' 的仓库。")
        sys.exit(1)

    print(f"已移除仓库：{args.path_or_alias}")

    if is_daemon_running():
        print("守护进程将自动应用该变更。")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the crg-daemon CLI."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    ap = argparse.ArgumentParser(
        prog="crg-daemon",
        description="code-review-graph 的多仓库监听守护进程",
    )
    sub = ap.add_subparsers(dest="command")

    # start
    start_cmd = sub.add_parser("start", help="启动守护进程")
    start_cmd.add_argument(
        "--foreground",
        action="store_true",
        help="在前台运行，而非后台 daemonize",
    )

    # stop
    sub.add_parser("stop", help="停止守护进程")

    # restart
    restart_cmd = sub.add_parser("restart", help="重启守护进程")
    restart_cmd.add_argument(
        "--foreground",
        action="store_true",
        help="在前台运行，而非后台 daemonize",
    )

    # status
    sub.add_parser("status", help="查看守护进程状态与配置")

    # logs
    logs_cmd = sub.add_parser("logs", help="查看守护进程或单个仓库的日志")
    logs_cmd.add_argument(
        "--repo",
        default=None,
        metavar="ALIAS",
        help="查看指定仓库（按别名）的日志",
    )
    logs_cmd.add_argument(
        "--follow",
        "-f",
        action="store_true",
        help="持续追踪日志输出（tail -f）",
    )
    logs_cmd.add_argument(
        "--lines",
        "-n",
        type=int,
        default=50,
        help="显示的行数（默认：50）",
    )

    # add
    add_cmd = sub.add_parser("add", help="将仓库加入守护进程配置")
    add_cmd.add_argument("path", help="仓库路径")
    add_cmd.add_argument(
        "--alias",
        default=None,
        help="仓库的短别名（默认：目录名）",
    )

    # remove
    remove_cmd = sub.add_parser("remove", help="将仓库从守护进程配置中移除")
    remove_cmd.add_argument("path_or_alias", help="要移除的仓库路径或别名")

    args = ap.parse_args()

    if not args.command:
        ap.print_help()
        sys.exit(0)

    handlers: dict[str, object] = {
        "start": _handle_start,
        "stop": _handle_stop,
        "restart": _handle_restart,
        "status": _handle_status,
        "logs": _handle_logs,
        "add": _handle_add,
        "remove": _handle_remove,
    }

    handler = handlers.get(args.command)
    if handler is None:
        ap.print_help()
        sys.exit(1)

    handler(args)  # type: ignore[operator]


if __name__ == "__main__":
    main()
