"""Som e música do modo gráfico: efeitos curtos (golpe acertando, desmaio,
jingle de vitória, tema de ginásio) sintetizados na hora com a biblioteca
padrão (`wave` + `struct`, tons puros) e cacheados em `.pokecache/audio/`, no
mesmo espírito de `.pokecache/sprites/` — sem nenhum asset de terceiro, então
sem nenhum problema de direito autoral.

A reprodução em si usa `pygame.mixer`, mas de um jeito totalmente à prova de
ambiente sem áudio (CI, servidor sem placa de som): toda chamada pra
`init()`/`play()`/`play_music()` está protegida por try/except amplo — sem
dispositivo de áudio ou sem pygame instalado, o jogo continua funcionando
em silêncio, nunca quebra.
"""

import math
import struct
import wave
from pathlib import Path
from typing import Optional

AUDIO_CACHE_DIR = Path(__file__).resolve().parent.parent / ".pokecache" / "audio"
SAMPLE_RATE = 22050
AMPLITUDE = 12000  # abaixo do teto de int16 (32767), pra não estourar/clipar

# nome do efeito -> sequência de (frequência em Hz, duração em ms); frequência
# 0 = silêncio (pausa entre notas de um jingle).
SOUND_DEFS: dict[str, list[tuple[int, int]]] = {
    "hit": [(600, 80)],
    "faint": [(400, 150), (300, 150), (200, 220)],
    "victory": [(523, 150), (659, 150), (784, 320)],
    "level_up": [(659, 90), (784, 90), (988, 180)],
    "gym_theme": [(392, 260), (0, 20), (440, 260), (0, 20), (494, 260), (0, 20), (440, 260)],
}

_pygame = None
_mixer_ready = False


def _synthesize_tone(path: Path, notes: list[tuple[int, int]], sample_rate: int = SAMPLE_RATE) -> None:
    """Gera um .wav com uma sequência de tons puros (onda senoidal)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for frequency, duration_ms in notes:
        sample_count = int(sample_rate * duration_ms / 1000)
        for i in range(sample_count):
            if frequency <= 0:
                value = 0
            else:
                value = int(AMPLITUDE * math.sin(2 * math.pi * frequency * i / sample_rate))
            frames += struct.pack("<h", value)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(bytes(frames))


def get_sound_path(name: str) -> Optional[Path]:
    """Caminho local do efeito `name`, sintetizando (e cacheando) na
    primeira vez que é pedido. None se `name` não é um efeito conhecido."""
    notes = SOUND_DEFS.get(name)
    if notes is None:
        return None
    path = AUDIO_CACHE_DIR / f"{name}.wav"
    if not path.exists():
        _synthesize_tone(path, notes)
    return path


def init() -> bool:
    """Tenta inicializar o mixer de áudio. Devolve True se conseguiu — nunca
    levanta exceção, mesmo sem dispositivo de áudio ou sem pygame instalado."""
    global _pygame, _mixer_ready
    if _mixer_ready:
        return True
    try:
        import pygame
        pygame.mixer.init()
        _pygame = pygame
        _mixer_ready = True
    except Exception:  # noqa: BLE001 — qualquer falha de áudio vira "sem som", não crash
        _pygame = None
        _mixer_ready = False
    return _mixer_ready


def play(name: str) -> None:
    """Toca um efeito curto uma vez. Silencioso (não faz nada) se o áudio
    não estiver disponível nesse ambiente."""
    if not init():
        return
    path = get_sound_path(name)
    if path is None:
        return
    try:
        _pygame.mixer.Sound(str(path)).play()
    except Exception:  # noqa: BLE001
        pass


def play_music(name: str, loop: bool = True) -> None:
    """Toca um tema em loop (ex: música de ginásio) até stop_music()."""
    if not init():
        return
    path = get_sound_path(name)
    if path is None:
        return
    try:
        _pygame.mixer.music.load(str(path))
        _pygame.mixer.music.play(loops=-1 if loop else 0)
    except Exception:  # noqa: BLE001
        pass


def stop_music() -> None:
    if not _mixer_ready or _pygame is None:
        return
    try:
        _pygame.mixer.music.stop()
    except Exception:  # noqa: BLE001
        pass
