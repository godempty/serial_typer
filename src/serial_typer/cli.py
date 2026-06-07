from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path


DELAY_RE = re.compile(r"^\s*DELAY\s+(\d+(?:\.\d+)?)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class TypeLine:
    line_no: int
    text: str


@dataclass(frozen=True)
class Delay:
    line_no: int
    seconds: float


Action = TypeLine | Delay


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def parse_command_file(path: Path, *, comments: bool = True) -> list[Action]:
    actions: list[Action] = []
    text = path.read_text(encoding="utf-8-sig")

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip("\r\n")
        delay_match = DELAY_RE.match(line)
        if delay_match:
            seconds = float(delay_match.group(1))
            actions.append(Delay(line_no=line_no, seconds=seconds))
            continue

        if comments and line.lstrip().startswith("#"):
            continue

        actions.append(TypeLine(line_no=line_no, text=line))

    return actions


def choose_window() -> object:
    import pygetwindow as gw

    windows = [window for window in gw.getAllWindows() if window.title.strip()]
    if not windows:
        raise RuntimeError("找不到可選的視窗。請改用 --focus-delay，或先打開 Xshell。")

    print("可用視窗：")
    for index, window in enumerate(windows, start=1):
        print(f"{index:>2}. {window.title}")

    while True:
        value = input("請輸入目標視窗編號：").strip()
        if not value.isdigit():
            print("請輸入數字。")
            continue
        index = int(value)
        if 1 <= index <= len(windows):
            return windows[index - 1]
        print(f"請輸入 1 到 {len(windows)} 之間的編號。")


def activate_window(window: object) -> None:
    if getattr(window, "isMinimized", False):
        window.restore()
    window.activate()
    time.sleep(0.5)


def countdown(seconds: float) -> None:
    if seconds <= 0:
        return

    end_at = time.monotonic() + seconds
    while True:
        remaining = end_at - time.monotonic()
        if remaining <= 0:
            print()
            return
        print(f"\r開始輸入倒數：{remaining:0.1f} 秒", end="", flush=True)
        time.sleep(min(0.1, remaining))


def type_actions(actions: list[Action], *, wpm: float, enter_delay: float) -> None:
    import pyautogui

    if wpm <= 0:
        raise ValueError("--wpm 必須大於 0。")

    pyautogui.FAILSAFE = True
    interval = 60.0 / (wpm * 5.0)

    for action in actions:
        if isinstance(action, Delay):
            print(f"line {action.line_no}: delay {action.seconds:g}s")
            time.sleep(action.seconds)
            continue

        print(f"line {action.line_no}: type {action.text!r}")
        if action.text:
            pyautogui.write(action.text, interval=interval)
        pyautogui.press("enter")
        if enter_delay > 0:
            time.sleep(enter_delay)


def dry_run(actions: list[Action]) -> None:
    for action in actions:
        if isinstance(action, Delay):
            print(f"{action.line_no}: DELAY {action.seconds:g}s")
        else:
            print(f"{action.line_no}: TYPE {action.text!r} + ENTER")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Type a command file into a selected Windows application window."
    )
    parser.add_argument("file", type=Path, help="要送出的文字檔。")
    parser.add_argument("--wpm", type=float, default=60.0, help="輸入速度，預設 60 WPM。")
    parser.add_argument(
        "--choose-window",
        action="store_true",
        help="列出目前視窗並選擇目標視窗。",
    )
    parser.add_argument(
        "--focus-delay",
        type=float,
        default=3.0,
        help="開始前倒數秒數，讓你有時間切到目標視窗；預設 3 秒。",
    )
    parser.add_argument(
        "--enter-delay",
        type=float,
        default=0.05,
        help="每行按 Enter 後額外等待秒數；預設 0.05。",
    )
    parser.add_argument(
        "--no-comments",
        action="store_true",
        help="不要把 # 開頭的行當註解，會照樣送出。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只解析並顯示動作，不實際輸入。",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.file.exists():
        parser.error(f"檔案不存在：{args.file}")
    if args.wpm <= 0:
        parser.error("--wpm 必須大於 0")
    if args.focus_delay < 0:
        parser.error("--focus-delay 不能小於 0")
    if args.enter_delay < 0:
        parser.error("--enter-delay 不能小於 0")

    actions = parse_command_file(args.file, comments=not args.no_comments)
    if args.dry_run:
        dry_run(actions)
        return 0

    target_window = choose_window() if args.choose_window else None
    print("請確認 Xshell serial console 已可接收鍵盤輸入。按 Ctrl+C 可中止。")

    print(f"wpm: {args.wpm}")
    
    try:
        if target_window is not None:
            activate_window(target_window)
        countdown(args.focus_delay)
        type_actions(actions, wpm=args.wpm, enter_delay=args.enter_delay)
    except KeyboardInterrupt:
        print("\n已中止。", file=sys.stderr)
        return 130

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
