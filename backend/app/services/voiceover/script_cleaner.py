from typing import Tuple
from app.services.voiceover.extractor import VoiceoverScriptExtractor, ExtractionResult


class ScriptCleaner:
    """
    Adapter and utility for Voiceover Script Extraction.
    Delegates extraction to VoiceoverScriptExtractor to strictly isolate
    the spoken dialogue from AI-generated multi-scene advertising scripts.
    """

    @classmethod
    def extract(cls, raw_text: str) -> ExtractionResult:
        """
        Runs the full VoiceoverScriptExtractor pipeline.
        """
        return VoiceoverScriptExtractor.extract(raw_text)

    @classmethod
    def clean(cls, raw_text: str) -> Tuple[str, int]:
        """
        Backward-compatible method:
        Returns (cleaned_script, removed_tags_count).
        """
        result = cls.extract(raw_text)
        tags_count = result.dialogue_blocks_count
        return result.cleaned_script, tags_count