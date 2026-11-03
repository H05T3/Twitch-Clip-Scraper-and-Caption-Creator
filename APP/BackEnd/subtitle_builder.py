"""Groups word-level timestamps into short, readable on-screen subtitle lines."""
from APP.BackEnd.config import Settings
from APP.BackEnd.models import SubtitleLine, WordTiming


class SubtitleLineBuilder:
    """Single responsibility: split a list of WordTiming into SubtitleLine groups
    so each line is short (few words / characters) and breaks at natural pauses.
    Limits come from settings (SUBTITLE_MAX_WORDS, SUBTITLE_MAX_CHARS,
    SUBTITLE_MAX_GAP_SECONDS)."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def build(self, words: list) -> list:
        lines, current = [], []
        for word in words:
            if not word.text.strip():
                continue
            if current and self._should_break(current, word):
                lines.append(SubtitleLine(words=current))
                current = []
            current.append(word)
        if current:
            lines.append(SubtitleLine(words=current))
        return lines

    def _should_break(self, current: list, next_word: WordTiming) -> bool:
        too_many_words = len(current) >= self.settings.subtitle_max_words
        projected_chars = len(" ".join(w.text for w in current + [next_word]))
        too_long = projected_chars > self.settings.subtitle_max_chars
        long_pause = (next_word.start - current[-1].end) > self.settings.subtitle_max_gap_seconds
        ends_sentence = current[-1].text.rstrip().endswith((".", "!", "?"))
        return too_many_words or too_long or long_pause or ends_sentence
