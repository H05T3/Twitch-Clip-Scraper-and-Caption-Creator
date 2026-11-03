"""Command-line entry point so the backend can be used (and debugged) before the GUI exists.

    python -m APP.BackEnd.cli fetch https://twitch.tv/somestreamer
    python -m APP.BackEnd.cli saved
    python -m APP.BackEnd.cli stats
    python -m APP.BackEnd.cli theme dark
"""
import argparse
import sys

from APP.BackEnd.config import load_settings
from APP.BackEnd.errors import ClipperError
from APP.BackEnd.pipeline import ClipPipeline

# Command names and help text, declared once.
CMD_FETCH, CMD_SAVED, CMD_STATS, CMD_THEME = "fetch", "saved", "stats", "theme"
HELP_FETCH = "Fetch the newest clips of a channel and render them as portrait videos"
HELP_SAVED = "List saved clips"
HELP_STATS = "Show counters and the save folder"
HELP_THEME = "Show or set the UI theme"
PROMPT_SAVE = "Save '{title}'? [y/N] "
YES_ANSWERS = ("y", "yes")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Twitch clip -> portrait short generator")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser(CMD_FETCH, help=HELP_FETCH)
    fetch.add_argument("channel", help="Twitch channel URL or name")
    fetch.add_argument("--save-all", action="store_true", help="Save every result without asking")
    commands.add_parser(CMD_SAVED, help=HELP_SAVED)
    commands.add_parser(CMD_STATS, help=HELP_STATS)
    theme = commands.add_parser(CMD_THEME, help=HELP_THEME)
    theme.add_argument("value", nargs="?")
    args = parser.parse_args(argv)

    pipeline = ClipPipeline(load_settings())
    try:
        if args.command == CMD_FETCH:
            clips, errors = pipeline.fetch_and_process(args.channel, progress=print)
            for clip in clips:
                keep = args.save_all or input(PROMPT_SAVE.format(title=clip.title)).strip().lower() in YES_ANSWERS
                print(f"Saved: {pipeline.save(clip)}" if keep else pipeline.discard(clip) or "Discarded.")
        elif args.command == CMD_SAVED:
            for clip in pipeline.library.list_clips():
                print(f"{clip.get('title')}  ->  {clip['video_path']}")
        elif args.command == CMD_STATS:
            for key, value in pipeline.library.stats().items():
                print(f"{key}: {value}")
        elif args.command == CMD_THEME:
            if args.value:
                pipeline.store.set_theme(args.value)
            print(pipeline.store.theme)
    except ClipperError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
