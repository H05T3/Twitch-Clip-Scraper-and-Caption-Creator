"""Backend tests. Network services are faked; ffmpeg rendering is run for real."""
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from APP.BackEnd.analysis_models import ClipAnalysis, ProcessedClip, ZoomRegion
from APP.BackEnd.errors import ClipperError, TwitchServiceError
from APP.BackEnd.models import ClipInfo, WordTiming
from APP.BackEnd.pipeline import ClipPipeline
from APP.BackEnd.storage_service import ClipLibrary, SettingsStore
from APP.BackEnd.subtitle_builder import SubtitleLineBuilder
from APP.BackEnd.transcription_service import ClipAnalyzer
from APP.BackEnd.twitch_service import ChannelUrlParser, TwitchApiClient
from APP.BackEnd.video_processor import FilterGraphBuilder, VideoProcessor


def words(*items):
    return [WordTiming(t, s, e) for t, s, e in items]


# ---------- URL parsing ----------
@pytest.mark.parametrize("text,expected", [
    ("https://www.twitch.tv/Some_Streamer/clips", "some_streamer"),
    ("twitch.tv/abc123", "abc123"),
    ("  Ninja ", "ninja"),
])
def test_parser_ok(settings, text, expected):
    assert ChannelUrlParser(settings).parse(text) == expected


@pytest.mark.parametrize("text", ["", "https://youtube.com/abc", "https://twitch.tv/directory", "bad name!"])
def test_parser_rejects(settings, text):
    with pytest.raises(TwitchServiceError):
        ChannelUrlParser(settings).parse(text)


# ---------- Twitch API (fake HTTP) ----------
class FakeSession:
    def __init__(self, clips):
        self.clips, self.calls = clips, []

    def post(self, url, **kw):
        return SimpleNamespace(status_code=200, json=lambda: {"access_token": "t", "expires_in": 3600})

    def get(self, url, **kw):
        self.calls.append((url, kw["params"]))
        if url.endswith("/users"):
            return SimpleNamespace(status_code=200, json=lambda: {"data": [{"id": "42"}]})
        return SimpleNamespace(status_code=200, json=lambda: {"data": self.clips, "pagination": {}})


def raw_clip(i, created):
    return {"id": f"c{i}", "url": f"https://clips.twitch.tv/c{i}", "title": f"t{i}", "created_at": created,
            "duration": 20, "view_count": i}


def test_recent_clips_sorted_by_date_not_views(settings):
    clips = [raw_clip(i, f"2026-10-{i:02d}T00:00:00Z") for i in range(1, 9)]  # c8 newest
    client = TwitchApiClient(settings, FakeSession(clips))
    result = client.get_recent_clips(client.get_broadcaster_id("x"))
    assert [c.clip_id for c in result] == ["c8", "c7", "c6", "c5", "c4"]


# ---------- Subtitles ----------
def test_subtitle_line_breaks(settings):
    ws = words(("Hi", 0, .3), ("you", .3, .6), ("all.", .6, 1.0), ("Next", 1.1, 1.4), ("line", 3.0, 3.3))
    lines = SubtitleLineBuilder(settings).build(ws)
    assert [l.text for l in lines] == ["Hi you all.", "Next", "line"]  # sentence end + long pause


# ---------- Analyzer validation ----------
class FakeChat:
    def __init__(self, payload):
        self.payload = payload
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.kw = kw
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(self.payload)))])


def test_analyzer_clamps_bad_ai_values(settings):
    clip = ClipInfo("c1", "u", "Orig title", "S", "C", "2026-01-01T00:00:00Z", duration=10)
    payload = {"title": "X" * 200, "zoom_regions": [
        {"start": 1, "end": 99, "focus_x": 5, "focus_y": -2, "zoom": 9},   # clamped
        {"start": 5, "end": 4},                                            # invalid -> dropped
        {"start": "bad"},                                                  # invalid -> dropped
    ], "emphasis_words": ["Wow!"], "hashtags": ["#fun"]}
    fake = FakeChat(payload)
    result = ClipAnalyzer(settings, client=fake).analyze(clip, "hi", words(("hi", 0, .5)))
    assert len(result.title) == settings.title_max_chars
    assert len(result.zoom_regions) == 1
    z = result.zoom_regions[0]
    assert (z.end, z.focus_x, z.focus_y, z.zoom) == (10, 1.0, 0.0, settings.zoom_max_factor)
    assert result.emphasis_words == ["wow"] and result.hashtags == ["fun"]
    assert "{" not in fake.kw["messages"][0]["content"].split("Return ONLY")[0]  # placeholders filled
    assert str(settings.title_max_chars) in fake.kw["messages"][0]["content"]


# ---------- Filter graph ----------
def test_zoom_regions_never_overlap():
    cleaned = FilterGraphBuilder.non_overlapping([ZoomRegion(3, 6), ZoomRegion(1, 4), ZoomRegion(5, 5.5)])
    assert [(r.start, r.end) for r in cleaned] == [(1, 4), (4, 6)]


# ---------- Real ffmpeg render ----------
@pytest.fixture
def sample_clip(tmp_path):
    path = tmp_path / "src.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=6",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=6", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", str(path)], check=True, capture_output=True)
    return path


def make_analysis(settings):
    ws = words(("this", .2, .6), ("is", .6, .9), ("totally", 1.0, 1.6), ("insane", 1.6, 2.2),
               ("no", 3.0, 3.3), ("way", 3.3, 3.8), ("dude", 3.8, 4.3))
    return ClipAnalysis(title="This streamer just did the absolutely impossible thing live on stream",
                        subtitle_lines=SubtitleLineBuilder(settings).build(ws), emphasis_words=["insane"],
                        zoom_regions=[ZoomRegion(1.0, 2.5, 0.25, 0.3, 1.5), ZoomRegion(3.0, 4.5, 0.8, 0.6, 1.3)])


def probe(path, entries):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          f"stream={entries}", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return out.stdout.strip()

#This part isn't working gangy
def test_render_produces_portrait_video(settings, sample_clip, tmp_path):
    out = VideoProcessor(settings).render(sample_clip, make_analysis(settings), tmp_path / "out" / "r.mp4")
    assert probe(out, "width,height") == f"{settings.output_width},{settings.output_height}"
    assert not list(out.parent.glob("*.ass"))  # temp caption file cleaned up
    audio = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name",
                            "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout
    assert "aac" in audio


def test_render_without_zoom_or_subtitles(settings, sample_clip, tmp_path):
    out = VideoProcessor(settings).render(sample_clip, ClipAnalysis(title="Hi"), tmp_path / "plain.mp4")
    assert out.exists()


# ---------- Storage ----------
def test_storage_roundtrip(settings, tmp_path):
    store = SettingsStore(settings)
    assert store.theme == settings.theme
    store.set_theme("light")
    assert SettingsStore(settings).theme == "light"  # persisted
    with pytest.raises(ClipperError):
        store.set_theme("neon")
    video = tmp_path / "p.mp4"
    video.write_bytes(b"x")
    lib = ClipLibrary(settings, store)
    saved = lib.save(ProcessedClip("c1", "My Title!", video))
    assert saved.exists() and lib.stats()["clips_saved"] == 1
    assert lib.list_clips()[0]["title"] == "My Title!"
    lib.delete(saved)
    assert lib.list_clips() == []


# ---------- Whole pipeline with fakes ----------
def test_pipeline_end_to_end_with_fakes(settings, sample_clip):
    info = ClipInfo("c1", "https://clips.twitch.tv/c1", "Orig", "Streamer", "Me", "2026-10-01T00:00:00Z", 6)
    bad = ClipInfo("c2", "https://clips.twitch.tv/c2", "Broken", "Streamer", "Me", "2026-10-01T00:00:00Z", 6)

    class T:
        def get_broadcaster_id(self, login): return "1"
        def get_recent_clips(self, _id): return [info, bad]

    class D:
        def download(self, clip, folder):
            if clip.clip_id == "c2":
                raise TwitchServiceError("nope")
            return sample_clip

    class A:
        def extract(self, video, folder): return video

    class W:
        def transcribe(self, audio): return "hi", words(("hi", 0.2, 0.6))

    class N:
        def analyze(self, clip, text, ws):
            return ClipAnalysis(title="Great title", subtitle_lines=SubtitleLineBuilder(settings).build(ws))

    messages = []
    pipe = ClipPipeline(settings, twitch=T(), downloader=D(), audio=A(), transcriber=W(), analyzer=N())
    results, errors = pipe.fetch_and_process("https://twitch.tv/streamer", messages.append)
    assert len(results) == 1 and len(errors) == 1 and results[0].video_path.exists()
    saved = pipe.save(results[0])
    assert saved.exists() and results[0].video_path.exists()  # preview kept until workspace cleanup
    pipe.clear_workspace()
    assert not results[0].video_path.exists()
    assert pipe.library.stats()["clips_created"] == 1
