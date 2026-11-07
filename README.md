# Twitch Clip-to-Shorts Automator

Fetches the newest clips from a Twitch channel, turns them into 9:16 portrait videos
(blurred background, title banner on top, word-highlight subtitles, AI-chosen zoom moments)
and lets you keep the ones you like in `APP/SavedClips`.

**Status:** backend and front end (CustomTkinter) complete; 19 automated tests pass. Not yet run against live Twitch/OpenAI.

## Setup
1. Python 3.10+ and `ffmpeg` on your PATH (with libass - standard builds have it).
2. `pip install -r requirements.txt`
3. `cp .env.example .env` and fill in `OPENAI_API_KEY`, `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET`
   (free Twitch keys: https://dev.twitch.tv/console). `.env` is in `.gitignore` - never commit it.

## Run the app
```
python -m APP.main
```
On Linux you may also need tkinter: `sudo apt install python3-tk`.

**ffmpeg:** `pip install -r requirements.txt` includes `imageio-ffmpeg`, so the app works even if ffmpeg is not installed on your PC.
It looks for ffmpeg in this order: `FFMPEG_BINARY` in `.env` (full path) -> your PATH -> the bundled copy.

**Run everything from the project folder** (the one containing `APP/` and `README.md`), always as a module:
`python -m APP.main` / `python -m pytest`. Do not run files inside `APP/` directly (e.g. `python conftest.py`) - that causes `No module named 'APP'`.

## Command line (same backend, no window)
```
python -m APP.BackEnd.cli fetch https://www.twitch.tv/somestreamer
python -m APP.BackEnd.cli saved
python -m APP.BackEnd.cli stats
python -m APP.BackEnd.cli theme light
python -m pytest APP/Tests
```

## How it works
```
URL -> ChannelUrlParser -> TwitchApiClient (Helix: newest N clips) -> ClipDownloader (yt-dlp)
    -> AudioExtractor (ffmpeg) -> WhisperTranscriber (word timestamps)
    -> ClipAnalyzer (GPT: title, emphasis words, zoom regions)  + SubtitleLineBuilder
    -> VideoProcessor (one ffmpeg pass: blur bg, zoom, title banner, subtitles)
    -> preview in APP/Workspace -> user Saves (-> APP/SavedClips) or Discards
```
Helix returns clips sorted by views, so the app requests a lookback window
(`CLIP_LOOKBACK_DAYS`) and sorts by date itself.

## Rules followed
- Max 3 classes per file; every class has a purpose docstring.
- No hard-coded values: everything lives in `APP/BackEnd/config.py` (`DEFAULTS`) and can be overridden in `.env`.
- GPT prompt is a text file (`APP/Assets/prompts/analysis_prompt.txt`), editable without touching code.
- All app files under `APP/`: `BackEnd/`, `FrontEnd/`, `Assets/`, `SavedClips/`, `Tests/`.
- Every UI string, size, timing and colour is in `APP/BackEnd/ui_config.py`.

## Backend API for the front end
`ClipPipeline` (`APP/BackEnd/pipeline.py`): `fetch_and_process(url, progress_cb)`, `save(clip)`,
`discard(clip)`, `library.list_clips()`, `library.delete(path)`, `library.stats()`, `store.theme / set_theme()`.
All expected failures raise `ClipperError` with a user-friendly message.

## Front end (APP/FrontEnd)
| File | Job |
|---|---|
| `main_window.py` | Window, page switching, F11 full screen, theme (remembered in `settings.json`) |
| `views/home_view.py` | "Welcome User" with blue glow, clips created/saved, save folder |
| `views/fetch_view.py` | Animated link box, Fetch & Process, progress, Save/Discard cards |
| `views/gallery_view.py` | Saved clips grid with delete |
| `components/nav_bar.py` | Home / Get new clips / See past clips, full-screen button, dark-mode switch |
| `components/video_card.py`, `video_player.py` | Card + in-app player (play/pause/scrub) |
| `components/glow_frame.py`, `responsive_grid.py` | Glow effect, auto-reflowing grid |
| `task_runner.py` | Runs the slow backend on a thread so the window never freezes |

Notes: minimise / maximise / close use the native title bar. The built-in player is silent
(video only) - each card has an "Open with sound" button that opens the file in your system player.
