from app.schemas.voiceover import VoiceoverGenerateRequest
from app.services.voiceover.emotion import (
    apply_vieneu_emotion_cue,
    is_vieneu_voice,
)


def test_apply_vieneu_emotion_cue_appends_supported_tag_once():
    assert apply_vieneu_emotion_cue('Xin chao', 'laugh') == 'Xin chao [c\u01b0\u1eddi]'
    assert apply_vieneu_emotion_cue('Xin chao [c\u01b0\u1eddi]', 'laugh') == 'Xin chao [c\u01b0\u1eddi]'


def test_apply_vieneu_emotion_cue_keeps_natural_text_for_none_or_unknown():
    assert apply_vieneu_emotion_cue('  Xin chao  ', 'none') == 'Xin chao'
    assert apply_vieneu_emotion_cue('Xin chao', 'unknown') == 'Xin chao'


def test_vieneu_provider_detection_is_scoped_to_builtin_presets():
    assert is_vieneu_voice('vieneu-v3-turbo:Ngoc Huyen')
    assert not is_vieneu_voice('vi-VN-HoaiMyNeural')
    assert not is_vieneu_voice(None)


def test_voiceover_request_keeps_emotion_cue_optional():
    request = VoiceoverGenerateRequest(text='Xin chao', emotion_cue='sigh')
    assert request.emotion_cue == 'sigh'
    assert VoiceoverGenerateRequest(text='Xin chao').emotion_cue == 'none'
