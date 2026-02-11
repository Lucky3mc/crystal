import subprocess
import vlc
import os
import time
import threading
import random
import re
from skill_manager import Skill
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL


class MusicSkill(Skill):
    """
    Stable, singleton-based music streaming skill.
    Designed for voice assistants (Siri-like).
    """

    # ---------- SINGLETON VLC ----------
    _vlc_instance = None
    _vlc_player = None
    _monitor_started = False

    name = "MusicSkill"
    description = "Plays music via YouTube audio using yt-dlp and VLC."
    keywords = [
        "play", "music", "song",
        "stop", "pause", "resume",
        "volume", "next", "skip",
        "queue", "add",
        "radio", "background"
    ]

    def __init__(self):
        # Locate VLC DLLs (Windows)
        vlc_paths = [
            r"C:\Program Files\VideoLAN\VLC",
            r"C:\Program Files (x86)\VideoLAN\VLC",
        ]
        for path in vlc_paths:
            if os.path.exists(path):
                try:
                    os.add_dll_directory(path)
                    break
                except Exception:
                    pass

        # Initialize singleton VLC
        if MusicSkill._vlc_instance is None:
            MusicSkill._vlc_instance = vlc.Instance(
                "--quiet",
                "--no-video",
                "--network-caching=3000"
            )
            MusicSkill._vlc_player = MusicSkill._vlc_instance.media_player_new()
            print("✅ [MUSIC]: VLC engine initialized (singleton)")

        self.instance = MusicSkill._vlc_instance
        self.player = MusicSkill._vlc_player

        # Playback state
        self.queue = []
        self.current_track = None
        self.is_playing = False
        self.radio_mode = False
        self.last_action_time = time.time()

        # Default radio pool
        self.radio_tracks = [
            "lofi hip hop radio",
            "chillhop music",
            "jazz music",
            "ambient music",
            "classical music"
        ]

        # Volume
        self.current_volume = 0.5
        self._init_volume()

        # Start monitor thread once
        if not MusicSkill._monitor_started:
            threading.Thread(
                target=self._monitor_loop,
                daemon=True
            ).start()
            MusicSkill._monitor_started = True

    # ---------- VOLUME ----------
    def _init_volume(self):
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_,
                CLSCTX_ALL,
                None
            )
            self.volume_control = cast(interface, POINTER(IAudioEndpointVolume))
            self.current_volume = self.volume_control.GetMasterVolumeLevelScalar()
        except Exception:
            self.volume_control = None

    def _set_volume(self, level: float):
        level = max(0.0, min(1.0, level))
        if self.volume_control:
            self.volume_control.SetMasterVolumeLevelScalar(level, None)
        self.player.audio_set_volume(int(level * 100))
        self.current_volume = level

    # ---------- STREAM ----------
    def _get_stream_url(self, query: str):
        try:
            cmd = [
                "yt-dlp",
                "-g",
                f"ytsearch1:{query}",
                "--format", "bestaudio",
                "--quiet",
                "--no-warnings"
            ]
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=25
            )
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return None

    def _play(self, query: str):
        url = self._get_stream_url(query)
        if not url:
            return "I couldn't find that track."

        self.player.stop()
        time.sleep(0.3)

        media = self.instance.media_new(url)
        media.add_option("network-caching=3000")
        self.player.set_media(media)
        self.player.play()

        time.sleep(0.3)
        self._set_volume(self.current_volume)

        self.current_track = query
        self.is_playing = True
        self.last_action_time = time.time()

        return f"Playing {query}."

    # ---------- MONITOR ----------
    def _monitor_loop(self):
        while True:
            try:
                if self.is_playing and self.player.get_state() == vlc.State.Ended:
                    if self.queue:
                        next_song = self.queue.pop(0)
                        self._play(next_song)
                    elif self.radio_mode:
                        self._play(random.choice(self.radio_tracks))
                    else:
                        self.is_playing = False
                        self.current_track = None
                time.sleep(2)
            except Exception:
                time.sleep(5)

    # ---------- MAIN ENTRY ----------
    def run(self, parameters: dict):
        text = parameters.get("user_input", "").lower().strip()
        self.last_action_time = time.time()

        # STOP
        if any(w in text for w in ["stop", "quiet", "silence"]):
            self.player.stop()
            self.is_playing = False
            self.radio_mode = False
            self.queue.clear()
            return "Music stopped."

        # PAUSE / RESUME
        if "pause" in text:
            self.player.pause()
            return "Paused."

        if "resume" in text:
            self.player.play()
            return "Resumed."

        # VOLUME
        if "volume" in text:
            if "up" in text:
                self._set_volume(self.current_volume + 0.1)
            elif "down" in text:
                self._set_volume(self.current_volume - 0.1)
            elif "max" in text:
                self._set_volume(1.0)
            elif "mute" in text:
                self._set_volume(0.0)
            return f"Volume {int(self.current_volume * 100)} percent."

        # QUEUE
        if "add" in text and "queue" in text:
            song = re.sub(r"add|to queue|queue", "", text).strip()
            if song:
                self.queue.append(song)
                return f"Added {song} to queue."

        if "next" in text or "skip" in text:
            if self.queue:
                return self._play(self.queue.pop(0))
            return "Nothing queued."

        # STATUS
        if "what's playing" in text or "now playing" in text:
            return self.current_track or "Nothing playing."

        # RADIO
        if "radio" in text or "background" in text:
            self.radio_mode = True
            return self._play(random.choice(self.radio_tracks))

        # PLAY
        if "play" in text:
            query = re.sub(
                r"\b(play|music|song|listen|put on|please|the|a)\b",
                "",
                text
            ).strip()
            if not query:
                self.radio_mode = True
                return self._play(random.choice(self.radio_tracks))
            self.radio_mode = False
            return self._play(query)

        return None
