'''Persistent process entry point for the isolated VieNeu environment.'''

from __future__ import annotations

import contextlib
import json
import sys
import wave
from pathlib import Path


MAX_REQUEST_BYTES = 64 * 1024


def _reply(ok: bool) -> None:
    print(json.dumps({'ok': ok}), flush=True)


def _parse_request(raw: bytes) -> dict[str, object]:
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError('payload too large')

    payload = json.loads(raw.decode('utf-8'))
    warmup = bool(payload.get('warmup'))
    text = str(payload.get('text') or '').strip()
    reference_audio_value = payload.get('reference_audio')
    reference_audio = Path(reference_audio_value) if reference_audio_value else None
    voice = str(payload.get('voice') or '').strip()
    output_audio_value = payload.get('output_audio')
    output_audio = Path(output_audio_value) if output_audio_value else None
    model_snapshot = Path(payload['model_snapshot'])
    codec_snapshot = Path(payload['codec_snapshot'])
    threads = int(payload.get('threads') or 1)
    if (
        (not warmup and not text)
        or (not warmup and reference_audio is None and not voice)
        or (not warmup and reference_audio is not None and not reference_audio.is_file())
        or (not warmup and output_audio is None)
        or threads <= 0
    ):
        raise ValueError('invalid input')

    return {
        'text': text,
        'reference_audio': reference_audio,
        'voice': voice,
        'output_audio': output_audio,
        'model_snapshot': model_snapshot,
        'codec_snapshot': codec_snapshot,
        'threads': threads,
        'warmup': warmup,
    }


def _model_key(payload: dict[str, object]) -> tuple[str, str, int]:
    return (
        str(payload['model_snapshot']),
        str(payload['codec_snapshot']),
        int(payload['threads']),
    )


def _load_model(payload: dict[str, object]):
    from vieneu import Vieneu

    model_snapshot = Path(str(payload['model_snapshot']))
    codec_snapshot = Path(str(payload['codec_snapshot']))
    return Vieneu(
        backbone_repo=str(model_snapshot),
        backend='onnx',
        onnx_dir=str(model_snapshot / 'onnx_update'),
        codec_dir=str(codec_snapshot),
        precision='fp32',
        threads=int(payload['threads']),
    )


def _synthesize(tts, payload: dict[str, object]) -> None:
    options = {
        'apply_watermark': False,
        'max_chars': 256,
        'show_progress': False,
    }
    voice = str(payload['voice'])
    if voice:
        audio = tts.infer(str(payload['text']), voice=voice, **options)
    else:
        audio = tts.infer(
            str(payload['text']),
            ref_audio=str(payload['reference_audio']),
            denoise=True,
            **options,
        )
    if getattr(audio, 'size', 0) <= 0:
        raise ValueError('empty audio')

    output_audio = Path(str(payload['output_audio']))
    tts.save(audio, str(output_audio))
    with wave.open(str(output_audio), 'rb') as audio_file:
        if audio_file.getnframes() <= 0 or audio_file.getframerate() <= 0:
            raise ValueError('invalid output')


def main() -> int:
    tts = None
    loaded_key: tuple[str, str, int] | None = None

    for raw in sys.stdin.buffer:
        try:
            payload = _parse_request(raw)
            request_key = _model_key(payload)
            with contextlib.redirect_stdout(sys.stderr):
                if tts is None or loaded_key != request_key:
                    tts = _load_model(payload)
                    loaded_key = request_key
                if not payload['warmup']:
                    _synthesize(tts, payload)
        except Exception:
            _reply(False)
            continue

        _reply(True)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
