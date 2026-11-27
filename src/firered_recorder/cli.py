from __future__ import annotations

import argparse
import asyncio
import sys

from .client import DEFAULT_URL, RecorderConfig
from .file_stream import stream_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="firered_recorder")
    parser.add_argument("--url", default=DEFAULT_URL, help="Backend WebSocket URL")
    parser.add_argument("--mode", default="balanced", choices=["balanced", "accuracy"])
    parser.add_argument("--lang", default="auto", choices=["auto", "zh", "yue", "en"])
    parser.add_argument(
        "--output-script",
        default="simplified",
        choices=["simplified", "traditional", "as-is"],
    )
    parser.add_argument("--file", help="Stream a WAV file instead of opening the recorder UI")
    parser.add_argument(
        "--no-realtime",
        action="store_true",
        help="Send file frames as fast as possible (headless testing)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = RecorderConfig(
        url=args.url,
        mode=args.mode,
        lang=args.lang,
        output_script=args.output_script,
    )

    if args.file:
        def on_event(event: dict) -> None:
            if event.get("type") == "final" and sys.stdout is not None:
                print(
                    f"[{event.get('start_ms', 0)}-{event.get('end_ms', 0)}] "
                    f"{event.get('text', '')}"
                )
            elif event.get("type") == "error" and sys.stderr is not None:
                print(
                    f"error: {event.get('code')} {event.get('message')}",
                    file=sys.stderr,
                )

        asyncio.run(
            stream_file(
                cfg,
                args.file,
                realtime=not args.no_realtime,
                on_event=on_event,
            )
        )
        return 0

    from .app import run_gui

    return run_gui(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
