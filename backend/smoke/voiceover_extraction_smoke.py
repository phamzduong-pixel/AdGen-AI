"""Manual smoke check for script extraction; never imported by unit discovery."""

from app.services.voiceover.extractor import VoiceoverScriptExtractor


CASES = [
    ('dialogue-labelled', 'Visual: product close-up\nVoiceover: "Try it today."'),
    ('non-dialogue', '# Campaign plan\n- Audience: creators\n- Budget: 10m'),
]


def main() -> int:
    for name, text in CASES:
        result = VoiceoverScriptExtractor.extract(text)
        print(f'{name}: status={result.status} blocks={result.dialogue_blocks_count}')
        assert result.cleaned_script is not None
    print('VOICEOVER_EXTRACTION_SMOKE_PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())