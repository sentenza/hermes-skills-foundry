#!/usr/bin/env python3
# MIT License
# agy-cli-reader — authored by sentenza.
# Reads agy's own run artifacts under ~/.gemini/antigravity-cli.
# It does NOT invoke agy; it is a read-only viewer.
"""
agy-cli-reader: Follow an agy (Gemini antigravity CLI) run and render a live TUI.
Standard library only.
"""

import argparse
import atexit
import json
import os
import re
import select
import shutil
import signal
import sys
import termios
import time
import tty
from datetime import datetime

# Global terminal state for safe cleanup
_orig_termios = None
_in_alt_screen = False
_cursor_hidden = False
_cleaned_up = False


def cleanup_terminal():
    global _orig_termios, _in_alt_screen, _cursor_hidden, _cleaned_up
    if _cleaned_up:
        return
    _cleaned_up = True

    if _orig_termios is not None:
        try:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, _orig_termios)
        except Exception:
            pass

    out = []
    if _in_alt_screen:
        out.append("\033[?1049l")
    if _cursor_hidden:
        out.append("\033[?25h")
    if out:
        try:
            sys.stdout.write("".join(out))
            sys.stdout.flush()
        except Exception:
            pass


atexit.register(cleanup_terminal)


def _signal_handler(signum, frame):
    cleanup_terminal()
    sys.exit(0)


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# ANSI regex
ANSI_REGEX = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def strip_ansi(text: str) -> str:
    return ANSI_REGEX.sub("", text)


def visible_len(text: str) -> int:
    return len(strip_ansi(text))


def truncate_visible(text: str, max_w: int) -> str:
    if max_w <= 0:
        return ""
    cur_len = 0
    result = []
    parts = ANSI_REGEX.split(text)
    codes = ANSI_REGEX.findall(text)

    for i, part in enumerate(parts):
        if cur_len + len(part) <= max_w:
            result.append(part)
            cur_len += len(part)
        else:
            remaining = max_w - cur_len
            result.append(part[:remaining])
            cur_len += remaining
            break
        if i < len(codes):
            result.append(codes[i])
    return "".join(result)


def parse_iso_timestamp(iso_str: str) -> float:
    if not iso_str:
        return 0.0
    try:
        clean = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        return dt.timestamp()
    except Exception:
        return 0.0


def fmt_time(iso_str: str) -> str:
    if not iso_str:
        return "--:--:--"
    if "T" in iso_str:
        return iso_str.split("T")[1][:8]
    return iso_str[:8]


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def extract_first_sentence(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    m = re.search(r"^(.*?[.!?])(?:\s|$)", text)
    if m:
        sentence = m.group(1)
    else:
        sentence = text.split("\n")[0]
    return " ".join(sentence.split())


def extract_first_nonempty_line(text: str) -> str:
    if not text:
        return ""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("<") and line.endswith(">") and len(line) < 30:
            continue
        return " ".join(line.split())
    return ""


def get_file_tail(filepath: str, max_lines: int = 20, max_bytes: int = 65536) -> list:
    if not os.path.isfile(filepath):
        return []
    try:
        size = os.path.getsize(filepath)
        with open(filepath, "rb") as f:
            if size > max_bytes:
                f.seek(size - max_bytes)
            data = f.read()
        text = data.decode("utf-8", errors="replace")
        lines = text.splitlines()
        return lines[-max_lines:]
    except Exception:
        return []


def read_transcript(filepath: str) -> list:
    if not os.path.isfile(filepath):
        return []
    records = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                records.append(obj)
        except Exception:
            # Skip invalid or incomplete trailing lines
            continue
    return records


def read_stream_events(filepath: str) -> dict:
    if not filepath or not os.path.isfile(filepath):
        return {}
    step_updates = {}
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("event") == "step_update" and "step_update" in data:
                        su = data["step_update"]
                        idx = su.get("step_index")
                        if idx is not None:
                            step_updates[idx] = su
                except Exception:
                    continue
    except Exception:
        pass
    return step_updates


def resolve_conversation_dir(root: str, target: str) -> tuple:
    root = os.path.expanduser(root)
    brain_dir = os.path.join(root, "brain")

    # If target is an existing directory path
    if os.path.isdir(target):
        abs_path = os.path.abspath(target)
        cid = os.path.basename(abs_path)
        return cid, abs_path

    # Check directly inside brain_dir
    direct_match = os.path.join(brain_dir, target)
    if os.path.isdir(direct_match):
        return target, direct_match

    if not os.path.isdir(brain_dir):
        sys.stderr.write(f"Error: Brain directory not found at '{brain_dir}'\n")
        sys.exit(1)

    try:
        candidates = [
            d for d in os.listdir(brain_dir)
            if os.path.isdir(os.path.join(brain_dir, d)) and not d.startswith(".")
        ]
    except Exception as e:
        sys.stderr.write(f"Error listing '{brain_dir}': {e}\n")
        sys.exit(1)

    if not candidates:
        sys.stderr.write(f"Error: No conversation runs found in '{brain_dir}'\n")
        sys.exit(1)

    if target == "latest":
        candidates.sort(
            key=lambda d: os.path.getmtime(os.path.join(brain_dir, d)),
            reverse=True,
        )
        chosen = candidates[0]
        return chosen, os.path.join(brain_dir, chosen)

    # Prefix search
    matches = [c for c in candidates if c.startswith(target)]
    if len(matches) == 1:
        return matches[0], os.path.join(brain_dir, matches[0])
    elif len(matches) > 1:
        sys.stderr.write(
            f"Error: Ambiguous conversation ID prefix '{target}'. Matching directories:\n  "
            + "\n  ".join(matches)
            + "\n"
        )
        sys.exit(1)
    else:
        sys.stderr.write(f"Error: Conversation ID '{target}' not found in '{brain_dir}'\n")
        sys.exit(1)


def parse_step_record(raw: dict, stream_data: dict = None) -> dict:
    idx = raw.get("step_index", 0)
    stype = raw.get("type", "GENERIC")
    source = raw.get("source", "")
    status = raw.get("status", "DONE")
    created_at = raw.get("created_at", "")
    in_tokens = raw.get("input_tokens", 0)
    out_tokens = raw.get("output_tokens", 0)
    cache_tokens = raw.get("cache_read_tokens", 0)
    thinking = raw.get("thinking", "")
    tool_calls = raw.get("tool_calls", [])
    content = raw.get("content", "")

    tool_names = []
    if tool_calls:
        tool_names = [tc.get("name", "tool") for tc in tool_calls if isinstance(tc, dict)]

    su = stream_data.get(idx) if stream_data else None
    if su:
        if "tool_name" in su and su["tool_name"]:
            tool_names = [su["tool_name"]]
        if "usage" in su and isinstance(su["usage"], dict):
            u = su["usage"]
            in_tokens = u.get("input_tokens", in_tokens)
            out_tokens = u.get("output_tokens", out_tokens)
            cache_tokens = u.get("cache_read_tokens", cache_tokens)
        if "state" in su:
            status = su["state"]

    # Preview logic
    if stype == "PLANNER_RESPONSE":
        if thinking:
            preview = extract_first_sentence(thinking)
        elif tool_names:
            preview = f"Call {', '.join(tool_names)}"
        else:
            preview = "(empty response)"
    elif stype == "USER_INPUT":
        preview = extract_first_nonempty_line(content)
    else:  # GENERIC / tool output
        preview = extract_first_nonempty_line(content)

    badge = "OUT"
    if stype == "USER_INPUT":
        badge = "USR"
    elif stype == "PLANNER_RESPONSE":
        badge = "PLAN"
    elif stype == "GENERIC":
        badge = "OUT"
    else:
        badge = stype[:4].upper()

    return {
        "step_index": idx,
        "type": stype,
        "source": source,
        "status": status,
        "created_at": created_at,
        "badge": badge,
        "tool_names": tool_names,
        "tool_calls": tool_calls,
        "thinking": thinking,
        "content": content,
        "preview": preview,
        "in_tokens": in_tokens,
        "out_tokens": out_tokens,
        "cache_tokens": cache_tokens,
        "stream_info": su,
    }


def format_step_line(step: dict, use_color: bool = True) -> str:
    badge = step["badge"]
    idx_str = f"#{step['step_index']}"
    t_str = fmt_time(step["created_at"])
    tools = ", ".join(step["tool_names"])
    preview = step["preview"]

    if use_color:
        if badge == "USR":
            c_badge = f"\033[1;36m[{badge:<4}]\033[0m"
        elif badge == "PLAN":
            c_badge = f"\033[1;35m[{badge:<4}]\033[0m"
        else:
            c_badge = f"\033[1;32m[{badge:<4}]\033[0m"
        c_idx = f"\033[1m{idx_str:<4}\033[0m"
        c_time = f"\033[2m{t_str}\033[0m"
        c_tools = f"\033[33m{tools:<14}\033[0m" if tools else " " * 14
        return f"{c_badge} {c_idx} {c_time} {c_tools} {preview}"
    else:
        t_col = f"{tools:<14}" if tools else " " * 14
        return f"[{badge:<4}] {idx_str:<4} {t_str} {t_col} {preview}"


def read_key(timeout: float) -> str:
    if not sys.stdin.isatty():
        time.sleep(timeout)
        return ""
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    if not rlist:
        return ""
    try:
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
            if rlist:
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if rlist:
                        ch3 = sys.stdin.read(1)
                        return "\x1b[" + ch3
                return ch + ch2
            return "\x1b"
        return ch
    except Exception:
        return ""


def wrap_text(text: str, width: int) -> list:
    if width <= 0:
        return []
    lines = []
    for paragraph in text.splitlines():
        if not paragraph:
            lines.append("")
            continue
        cur = 0
        while cur < len(paragraph):
            lines.append(paragraph[cur : cur + width])
            cur += width
    return lines


def run_tui(cid: str, cid_dir: str, stream_file: str, interval: float, use_color: bool, use_alt_screen: bool):
    global _orig_termios, _in_alt_screen, _cursor_hidden

    if sys.stdin.isatty():
        try:
            _orig_termios = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        except Exception:
            _orig_termios = None

    if use_alt_screen:
        sys.stdout.write("\033[?1049h")
        _in_alt_screen = True
    sys.stdout.write("\033[?25l")
    _cursor_hidden = True
    sys.stdout.flush()

    transcript_file = os.path.join(cid_dir, ".system_generated", "logs", "transcript.jsonl")
    steps_dir = os.path.join(cid_dir, ".system_generated", "steps")

    short_id = cid[:8] if len(cid) >= 8 else cid
    selected_idx = -1
    auto_follow = True
    detail_scroll = 0
    paused = False
    idle_ticks = 0
    last_record_count = -1
    force_redraw = True

    try:
        while True:
            t_start = time.time()

            if not paused or force_redraw:
                raw_records = read_transcript(transcript_file)
                stream_data = read_stream_events(stream_file) if stream_file else {}

                steps = [parse_step_record(r, stream_data) for r in raw_records]

                if len(steps) == last_record_count:
                    idle_ticks += 1
                else:
                    idle_ticks = 0
                    last_record_count = len(steps)

                # Determine status
                is_active = any(s.get("status") == "ACTIVE" for s in steps)
                last_is_agent_done = (
                    len(steps) > 0
                    and steps[-1]["type"] == "PLANNER_RESPONSE"
                    and steps[-1]["status"] == "DONE"
                    and not steps[-1]["tool_names"]
                )

                if is_active:
                    status = "RUNNING"
                elif last_is_agent_done:
                    status = "DONE"
                elif idle_ticks >= 6:
                    status = "IDLE"
                else:
                    status = "RUNNING"

                # Calculate elapsed time
                if steps:
                    t0 = parse_iso_timestamp(steps[0]["created_at"])
                    t1 = parse_iso_timestamp(steps[-1]["created_at"])
                    if status == "DONE":
                        elapsed = max(0.0, t1 - t0)
                    else:
                        elapsed = max(0.0, time.time() - t0 if t0 > 0 else 0.0)
                else:
                    elapsed = 0.0

                m, s = divmod(int(elapsed), 60)
                h, m = divmod(m, 60)
                elapsed_str = f"{h}h {m}m {s}s" if h > 0 else f"{m}m {s}s"

                # Tokens
                in_tok = sum(st["in_tokens"] for st in steps)
                out_tok = sum(st["out_tokens"] for st in steps)
                cache_tok = sum(st["cache_tokens"] for st in steps)
                tot_tok = in_tok + out_tok + cache_tok

                max_step_idx = steps[-1]["step_index"] if steps else 0

                if auto_follow and steps:
                    selected_idx = len(steps) - 1
                elif selected_idx >= len(steps):
                    selected_idx = len(steps) - 1

                # Terminal dimensions
                cols, lines = shutil.get_terminal_size((80, 24))
                cols = max(cols, 40)
                lines = max(lines, 12)

                # Layout calculation
                step_pane_h = max(3, (lines - 5) // 3)
                detail_pane_h = max(3, lines - 4 - step_pane_h)

                # Render Upper Pane (Step list)
                if steps:
                    if selected_idx < 0:
                        selected_idx = 0
                    if selected_idx < step_pane_h:
                        w_start = 0
                    else:
                        w_start = min(selected_idx - step_pane_h + 1, len(steps) - step_pane_h)
                        w_start = max(0, w_start)
                    w_steps = steps[w_start : w_start + step_pane_h]
                else:
                    w_steps = []
                    w_start = 0

                # Render Detail Pane lines
                detail_lines = []
                if steps and 0 <= selected_idx < len(steps):
                    cur = steps[selected_idx]
                    detail_lines.append(
                        f"Step #{cur['step_index']} · Type: {cur['type']} · Status: {cur['status']} · Time: {cur['created_at']}"
                    )
                    if cur["in_tokens"] or cur["out_tokens"] or cur["cache_tokens"]:
                        detail_lines.append(
                            f"Tokens: in={cur['in_tokens']} out={cur['out_tokens']} cache_read={cur['cache_tokens']}"
                        )
                    detail_lines.append("")

                    if cur["thinking"]:
                        detail_lines.append("─── Thinking ───")
                        detail_lines.extend(wrap_text(cur["thinking"], cols - 2))
                        detail_lines.append("")

                    if cur["tool_calls"]:
                        detail_lines.append("─── Tool Calls ───")
                        for tc in cur["tool_calls"]:
                            tname = tc.get("name", "tool")
                            targs = tc.get("args", {})
                            detail_lines.append(f"• {tname}")
                            if isinstance(targs, dict):
                                for k, v in targs.items():
                                    val_str = str(v)
                                    if len(val_str) > cols - 6:
                                        val_str = val_str[: cols - 9] + "..."
                                    detail_lines.append(f"    {k}: {val_str}")
                            else:
                                detail_lines.append(f"    {targs}")
                        detail_lines.append("")

                    # Output.txt tail
                    out_file = os.path.join(steps_dir, str(cur["step_index"]), "output.txt")
                    tail_lines = get_file_tail(out_file, max_lines=20)
                    if tail_lines:
                        detail_lines.append("─── Step Output (tail) ───")
                        for tl in tail_lines:
                            detail_lines.extend(wrap_text(tl, cols - 2))
                        detail_lines.append("")
                    elif cur["content"] and cur["type"] == "GENERIC":
                        detail_lines.append("─── Content ───")
                        detail_lines.extend(wrap_text(cur["content"], cols - 2))
                        detail_lines.append("")
                    elif cur["content"] and cur["type"] == "USER_INPUT":
                        detail_lines.append("─── User Request ───")
                        detail_lines.extend(wrap_text(cur["content"], cols - 2))
                        detail_lines.append("")

                # Bound detail_scroll
                max_scroll = max(0, len(detail_lines) - detail_pane_h)
                detail_scroll = max(0, min(detail_scroll, max_scroll))

                # Assemble screen buffer
                buf = ["\033[H"]  # Home cursor

                # 1. Header
                stat_colored = status
                if use_color:
                    if status == "RUNNING":
                        stat_colored = f"\033[1;32m{status}\033[0m"
                    elif status == "DONE":
                        stat_colored = f"\033[1;34m{status}\033[0m"
                    else:
                        stat_colored = f"\033[1;33m{status}\033[0m"

                hdr_text = (
                    f"agy · {short_id} · {stat_colored} · step {max_step_idx} · "
                    f"elapsed {elapsed_str} · tokens {fmt_tokens(in_tok)}/{fmt_tokens(out_tok)}/{fmt_tokens(tot_tok)}"
                )
                if use_color:
                    hdr_line = f"\033[1;7m {strip_ansi(hdr_text):<{cols - 2}} \033[0m"
                else:
                    hdr_line = f" {strip_ansi(hdr_text):<{cols - 2}} "
                buf.append(truncate_visible(hdr_line, cols) + "\n")

                # 2. Steps Divider
                step_div_title = f" Steps ({len(steps)}) "
                dash_len = max(0, cols - len(step_div_title) - 2)
                step_div = f"──{step_div_title}{'─' * dash_len}"
                if use_color:
                    buf.append(f"\033[2m{truncate_visible(step_div, cols)}\033[0m\n")
                else:
                    buf.append(truncate_visible(step_div, cols) + "\n")

                # 3. Steps list
                for i in range(step_pane_h):
                    step_idx_in_list = w_start + i
                    if step_idx_in_list < len(steps):
                        st = steps[step_idx_in_list]
                        is_sel = step_idx_in_list == selected_idx
                        ptr = ">" if is_sel else " "
                        row_str = f"{ptr} {format_step_line(st, use_color=use_color)}"
                        if is_sel and use_color:
                            vlen = visible_len(row_str)
                            pad = " " * max(0, cols - vlen)
                            row_rendered = f"\033[7m{row_str}{pad}\033[0m"
                        else:
                            vlen = visible_len(row_str)
                            pad = " " * max(0, cols - vlen)
                            row_rendered = f"{row_str}{pad}"
                        buf.append(truncate_visible(row_rendered, cols) + "\n")
                    else:
                        buf.append(" " * cols + "\n")

                # 4. Detail Divider
                cur_step_no = steps[selected_idx]["step_index"] if (steps and 0 <= selected_idx < len(steps)) else "-"
                detail_div_title = f" Detail (Step #{cur_step_no}) "
                dash_len2 = max(0, cols - len(detail_div_title) - 2)
                detail_div = f"──{detail_div_title}{'─' * dash_len2}"
                if use_color:
                    buf.append(f"\033[2m{truncate_visible(detail_div, cols)}\033[0m\n")
                else:
                    buf.append(truncate_visible(detail_div, cols) + "\n")

                # 5. Detail Pane
                for i in range(detail_pane_h):
                    line_idx = detail_scroll + i
                    if line_idx < len(detail_lines):
                        d_line = detail_lines[line_idx]
                        vlen = len(d_line)
                        pad = " " * max(0, cols - vlen)
                        buf.append(truncate_visible(d_line + pad, cols) + "\n")
                    else:
                        buf.append(" " * cols + "\n")

                # 6. Footer
                paused_str = " [PAUSED]" if paused else ""
                footer_raw = f" q:quit  j/k/↑/↓:scroll detail  g/G:top/bottom  r:redraw  p:pause{paused_str}"
                if use_color:
                    c_pause = "\033[1;31m [PAUSED]\033[0m" if paused else ""
                    ft_text = f" q:quit  j/k/↑/↓:scroll detail  g/G:top/bottom  r:redraw  p:pause{c_pause}"
                    vlen = visible_len(ft_text)
                    pad = " " * max(0, cols - vlen)
                    footer_rendered = f"\033[2m{ft_text}{pad}\033[0m"
                else:
                    vlen = len(footer_raw)
                    pad = " " * max(0, cols - vlen)
                    footer_rendered = f"{footer_raw}{pad}"
                buf.append(truncate_visible(footer_rendered, cols))

                sys.stdout.write("".join(buf))
                sys.stdout.flush()
                force_redraw = False

            # Wait for keypress with timeout
            time_spent = time.time() - t_start
            wait_time = max(0.05, interval - time_spent)
            key = read_key(wait_time)

            if key in ("q", "Q"):
                break
            elif key in ("j", "\x1b[B"):  # Down / scroll detail down
                detail_scroll += 1
                force_redraw = True
            elif key in ("k", "\x1b[A"):  # Up / scroll detail up
                detail_scroll = max(0, detail_scroll - 1)
                force_redraw = True
            elif key in ("g",):  # Jump to top of step list
                if steps:
                    selected_idx = 0
                    auto_follow = False
                    detail_scroll = 0
                    force_redraw = True
            elif key in ("G",):  # Jump to bottom of step list
                if steps:
                    selected_idx = len(steps) - 1
                    auto_follow = True
                    detail_scroll = 0
                    force_redraw = True
            elif key in ("[", "h", "\x1b[D"):  # Prev step
                if steps and selected_idx > 0:
                    selected_idx -= 1
                    auto_follow = False
                    detail_scroll = 0
                    force_redraw = True
            elif key in ("]", "l", "\x1b[C"):  # Next step
                if steps and selected_idx < len(steps) - 1:
                    selected_idx += 1
                    if selected_idx == len(steps) - 1:
                        auto_follow = True
                    detail_scroll = 0
                    force_redraw = True
            elif key in ("r", "R"):
                force_redraw = True
            elif key in ("p", "P"):
                paused = not paused
                force_redraw = True

    finally:
        cleanup_terminal()


def run_plain_stream(
    cid: str,
    cid_dir: str,
    stream_file: str,
    interval: float,
    use_color: bool,
    once_mode: bool,
):
    transcript_file = os.path.join(cid_dir, ".system_generated", "logs", "transcript.jsonl")
    last_printed_idx = -1

    while True:
        raw_records = read_transcript(transcript_file)
        stream_data = read_stream_events(stream_file) if stream_file else {}
        steps = [parse_step_record(r, stream_data) for r in raw_records]

        for st in steps:
            if st["step_index"] > last_printed_idx:
                line = format_step_line(st, use_color=use_color)
                print(line)
                last_printed_idx = st["step_index"]
        sys.stdout.flush()

        if once_mode:
            break

        time.sleep(interval)


def run_selftest():
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        fake_cid = "selftest-conv-001"
        brain_dir = os.path.join(tmpdir, "brain", fake_cid)
        logs_dir = os.path.join(brain_dir, ".system_generated", "logs")
        step2_dir = os.path.join(brain_dir, ".system_generated", "steps", "2")
        os.makedirs(logs_dir, exist_ok=True)
        os.makedirs(step2_dir, exist_ok=True)

        tool_snippet = "Selftest verification tool snippet output 42"

        rec0 = {
            "step_index": 0,
            "source": "USER_EXPLICIT",
            "type": "USER_INPUT",
            "status": "DONE",
            "created_at": "2026-10-11T12:00:00Z",
            "content": "Perform the system self-test verification",
        }
        rec1 = {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "status": "DONE",
            "created_at": "2026-10-11T12:00:01Z",
            "thinking": "I need to run the verification command now.",
            "tool_calls": [{"name": "verify_cmd", "args": {"flag": True}}],
            "input_tokens": 200,
            "output_tokens": 40,
            "cache_read_tokens": 0,
        }
        rec2 = {
            "step_index": 2,
            "source": "MODEL",
            "type": "GENERIC",
            "status": "DONE",
            "created_at": "2026-10-11T12:00:02Z",
            "content": tool_snippet,
        }

        transcript_path = os.path.join(logs_dir, "transcript.jsonl")
        with open(transcript_path, "w", encoding="utf-8") as f:
            for rec in [rec0, rec1, rec2]:
                f.write(json.dumps(rec) + "\n")

        output_txt_path = os.path.join(step2_dir, "output.txt")
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(f"{tool_snippet}\nAdditional details in step 2 output\n")

        script_path = os.path.abspath(__file__)
        cmd = [
            sys.executable,
            script_path,
            fake_cid,
            "--root",
            tmpdir,
            "--once",
            "--no-color",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            sys.stderr.write(f"Self-test failed (exit {res.returncode}):\n{res.stderr}\n")
            sys.exit(1)

        out = res.stdout
        assert "#0" in out or " 0 " in out or "step 0" in out.lower(), f"Step index 0 missing:\n{out}"
        assert "#1" in out or " 1 " in out or "step 1" in out.lower(), f"Step index 1 missing:\n{out}"
        assert "#2" in out or " 2 " in out or "step 2" in out.lower(), f"Step index 2 missing:\n{out}"
        assert tool_snippet in out, f"Tool snippet missing:\n{out}"

        print("SELFTEST OK")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Follow an agy run and render a live TUI in the terminal."
    )
    parser.add_argument(
        "id",
        nargs="?",
        default="latest",
        help="Conversation ID, prefix, 'latest' (default), or brain path",
    )
    parser.add_argument(
        "--root",
        default=os.path.expanduser("~/.gemini/antigravity-cli"),
        help="Antigravity root directory (default: ~/.gemini/antigravity-cli)",
    )
    parser.add_argument(
        "--stream",
        help="Follow stream-json NDJSON file for tool parameters/output and usage",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="Refresh interval in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Render current state once and exit (snapshot mode)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors",
    )
    parser.add_argument(
        "--no-alt-screen",
        action="store_true",
        help="Do not use alternate screen buffer",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run built-in self-test and exit",
    )

    args = parser.parse_args()

    if args.selftest:
        run_selftest()

    cid, cid_dir = resolve_conversation_dir(args.root, args.id)

    use_color = not args.no_color and ("NO_COLOR" not in os.environ) and sys.stdout.isatty()
    is_tty = sys.stdout.isatty()

    if args.once or not is_tty:
        run_plain_stream(
            cid=cid,
            cid_dir=cid_dir,
            stream_file=args.stream,
            interval=args.interval,
            use_color=use_color,
            once_mode=args.once,
        )
    else:
        run_tui(
            cid=cid,
            cid_dir=cid_dir,
            stream_file=args.stream,
            interval=args.interval,
            use_color=use_color,
            use_alt_screen=not args.no_alt_screen,
        )


if __name__ == "__main__":
    main()
