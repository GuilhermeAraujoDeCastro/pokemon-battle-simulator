"""Testes de pokebattle/audio.py — só a síntese e o cache do .wav; nunca
toca um dispositivo de áudio de verdade (o CI roda sem placa de som)."""

import wave

from pokebattle import audio


def test_synthesize_tone_writes_a_valid_wav_file(tmp_path):
    path = tmp_path / "beep.wav"
    audio._synthesize_tone(path, [(440, 100)], sample_rate=8000)

    assert path.exists()
    with wave.open(str(path), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getframerate() == 8000
        # 100ms a 8000Hz = 800 frames, com uma pequena tolerância de arredondamento
        assert abs(wav_file.getnframes() - 800) <= 1


def test_synthesize_tone_handles_silence():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "silence.wav"
        audio._synthesize_tone(path, [(0, 50)], sample_rate=8000)
        assert path.exists()


def test_get_sound_path_generates_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(audio, "AUDIO_CACHE_DIR", tmp_path)
    path = audio.get_sound_path("hit")
    assert path is not None
    assert path.exists()

    mtime_before = path.stat().st_mtime
    path_again = audio.get_sound_path("hit")
    assert path_again == path
    assert path.stat().st_mtime == mtime_before  # não regravou


def test_get_sound_path_returns_none_for_an_unknown_effect():
    assert audio.get_sound_path("efeito-que-nao-existe") is None


def test_play_and_init_never_raise_without_an_audio_device(monkeypatch):
    # Simula "pygame não instalado / sem dispositivo de áudio": init() deve
    # devolver False sem levantar nada, e play()/play_music() devem só não
    # fazer nada.
    monkeypatch.setattr(audio, "_mixer_ready", False)
    monkeypatch.setattr(audio, "_pygame", None)

    def _fail_import(*_args, **_kwargs):
        raise ImportError("sem pygame nesse ambiente de teste")

    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pygame":
            raise ImportError("sem pygame nesse ambiente de teste")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert audio.init() is False
    audio.play("hit")  # não pode levantar
    audio.play_music("gym_theme")  # não pode levantar
    audio.stop_music()  # não pode levantar
