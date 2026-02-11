"""
Enhanced Music Streaming Skill for Crystal Assistant
Features:
- YouTube audio/video streaming via yt-dlp
- Continuous radio/background play
- Hardware volume control (Windows)
- Queue management
- Video toggle
- Genre-based radio stations
- Thread-safe operations
- Proper resource cleanup
"""

import subprocess
import vlc
import os
import time
import threading
import random
import re
import logging
from typing import Optional, List, Dict, Tuple
from enum import Enum
from skill_manager import Skill
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class PlaybackState(Enum):
    """Playback state enumeration"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"
    ERROR = "error"


class MusicSkill(Skill):
    """Enhanced music streaming skill with continuous play and video support"""
    
    name = "MusicSkill"
    description = "Streams YouTube audio/video with continuous play, radio stations, and hardware volume control"
    keywords = ["play", "music", "song", "stop", "volume", "next", "queue", "add", 
                "video", "radio", "continue", "background", "pause", "resume", 
                "skip", "genre", "station"]
    supported_intents = ["music_skill"]
    # Radio station definitions
    RADIO_STATIONS = {
        "lo-fi": {
            "name": "Lo-Fi Hip Hop",
            "queries": [
                "lofi hip hop radio - beats to relax/study to",
                "chillhop music live radio 24/7",
                "synthwave radio - beats to chill/game to"
            ],
            "description": "Chill lo-fi beats for studying and relaxing",
            "tags": ["lofi", "chill", "study", "relax"]
        },
        "jazz": {
            "name": "Jazz Station",
            "queries": [
                "jazz music 24/7 live radio",
                "smooth jazz radio",
                "coffee shop jazz - background music"
            ],
            "description": "Smooth jazz and classic standards",
            "tags": ["jazz", "smooth", "coffee", "relaxing"]
        },
        "classical": {
            "name": "Classical Music",
            "queries": [
                "classical music live radio",
                "mozart radio 24/7",
                "piano classical music for studying"
            ],
            "description": "Classical masterpieces and piano works",
            "tags": ["classical", "piano", "orchestral", "study"]
        },
        "ambient": {
            "name": "Ambient Space",
            "queries": [
                "space ambient music live",
                "dark ambient radio",
                "meditation ambient music"
            ],
            "description": "Atmospheric ambient and space music",
            "tags": ["ambient", "space", "meditation", "calm"]
        },
        "electronic": {
            "name": "Electronic Beats",
            "queries": [
                "electronic dance music radio",
                "chill electronic beats",
                "synthwave retrowave radio"
            ],
            "description": "Electronic and synthwave music",
            "tags": ["electronic", "edm", "synthwave", "dance"]
        },
        "rock": {
            "name": "Rock Classics",
            "queries": [
                "classic rock radio 24/7",
                "alternative rock radio",
                "80s rock hits live"
            ],
            "description": "Classic and alternative rock",
            "tags": ["rock", "classic", "alternative", "guitar"]
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the music skill with configuration"""
        super().__init__()
        
        # Setup logger
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Thread safety
        self.queue_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self.radio_lock = threading.Lock()
        
        # Playback state
        self.playback_state = PlaybackState.STOPPED
        self.current_track = None
        self.current_position = 0
        self.duration = 0
        
        # Settings
        self.show_video = False
        self.video_hidden = True
        self.radio_mode = False
        self.radio_genre = "lo-fi"
        self.continuous_play = True  # Keep playing after track ends
        self.last_played = []
        self.max_history = 20
        
        # Playback data
        self.queue = []
        self.current_volume = self.config["default_volume"]
        self.is_playing = False
        self.vlc_instance = None
        self.vlc_player = None
        self.video_hwnd = None
        
        # Initialize components
        self._setup_vlc()
        self._init_volume_control()
        self._load_user_preferences()
        
        # Start background threads
        self._start_background_threads()
        
        self.logger.info("Music Skill initialized successfully")
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            "default_volume": 0.5,
            "cache_duration": 3000,
            "auto_radio": True,
            "default_genre": "lo-fi",
            "quality": "bestaudio",
            "video_quality": "best[height<=720]",
            "vlc_audio_args": ["--quiet", "--no-video", f"--network-caching=3000"],
            "vlc_video_args": ["--quiet", f"--network-caching=3000"],
            "max_queue_size": 50,
            "stream_timeout": 30,
            "retry_attempts": 3,
            "save_history": True,
            "history_file": "music_history.json"
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                self.logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                self.logger.error(f"Failed to load config: {e}")
        
        return default_config
    
    def _setup_vlc(self):
        """Setup VLC with proper DLL paths"""
        # Try common VLC installation paths
        vlc_paths = [
            r"C:\Program Files (x86)\VideoLAN\VLC",
            r"C:\Program Files\VideoLAN\VLC",
            r"C:\Program Files\VideoLAN\vlc-3.0.0",
            os.path.expanduser(r"~\AppData\Local\Programs\VideoLAN\VLC")
        ]
        
        vlc_found = False
        for path in vlc_paths:
            if os.path.exists(path):
                try:
                    os.add_dll_directory(path)
                    self.logger.info(f"Found VLC at: {path}")
                    vlc_found = True
                    break
                except Exception as e:
                    self.logger.debug(f"Failed to add DLL directory {path}: {e}")
        
        if not vlc_found:
            self.logger.warning("VLC path not found, relying on system PATH")
        
        # Create initial VLC instance (audio-only)
        try:
            args = " ".join(self.config["vlc_audio_args"])
            self.vlc_instance = vlc.Instance(args)
            self.vlc_player = self.vlc_instance.media_player_new()
            self.logger.info("VLC engine initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize VLC: {e}")
            self.vlc_player = None
    
    def _init_volume_control(self):
        """Initialize Windows audio volume control"""
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, 
                CLSCTX_ALL, 
                None
            )
            self.volume_control = cast(interface, POINTER(IAudioEndpointVolume))
            current_vol = self.volume_control.GetMasterVolumeLevelScalar()
            self.current_volume = current_vol
            self.logger.info(f"Windows volume control initialized: {int(current_vol * 100)}%")
        except Exception as e:
            self.logger.warning(f"Could not initialize pycaw volume control: {e}")
            self.logger.info("Falling back to software volume control")
            self.volume_control = None
    
    def _load_user_preferences(self):
        """Load user preferences from file"""
        pref_file = "music_preferences.json"
        if os.path.exists(pref_file):
            try:
                with open(pref_file, 'r') as f:
                    prefs = json.load(f)
                self.radio_genre = prefs.get("last_genre", self.radio_genre)
                self.current_volume = prefs.get("last_volume", self.current_volume)
                self.show_video = prefs.get("show_video", self.show_video)
                self.logger.info("Loaded user preferences")
            except Exception as e:
                self.logger.error(f"Failed to load preferences: {e}")
    
    def _save_user_preferences(self):
        """Save user preferences to file"""
        pref_file = "music_preferences.json"
        try:
            prefs = {
                "last_genre": self.radio_genre,
                "last_volume": self.current_volume,
                "show_video": self.show_video,
                "radio_mode": self.radio_mode,
                "continuous_play": self.continuous_play
            }
            with open(pref_file, 'w') as f:
                json.dump(prefs, f, indent=2)
            self.logger.debug("User preferences saved")
        except Exception as e:
            self.logger.error(f"Failed to save preferences: {e}")
    
    def _save_to_history(self, track_info: Dict):
        """Save track to playback history"""
        if not self.config["save_history"]:
            return
        
        try:
            history_file = self.config["history_file"]
            history = []
            
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    history = json.load(f)
            
            # Add timestamp
            track_info["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
            track_info["genre"] = self.radio_genre if self.radio_mode else None
            
            # Add to beginning
            history.insert(0, track_info)
            
            # Keep only recent history
            if len(history) > self.max_history:
                history = history[:self.max_history]
            
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
            
            self.last_played.insert(0, track_info)
            if len(self.last_played) > self.max_history:
                self.last_played = self.last_played[:self.max_history]
                
        except Exception as e:
            self.logger.error(f"Failed to save history: {e}")
    
    def _get_stream_url(self, query: str, audio_only: bool = True) -> Optional[str]:
        """
        Get stream URL using yt-dlp with retry logic
        
        Args:
            query: Search query or YouTube URL
            audio_only: Whether to get audio-only stream
            
        Returns:
            Stream URL or None if failed
        """
        for attempt in range(self.config["retry_attempts"]):
            try:
                # Build command
                cmd = [
                    "yt-dlp",
                    "-g",
                    f"ytsearch1:{query}" if not query.startswith(("http://", "https://")) else query,
                    "--no-warnings",
                    "--quiet",
                    "--no-playlist"
                ]
                
                # Add format selection
                if audio_only:
                    cmd.extend(["--format", self.config["quality"]])
                else:
                    cmd.extend(["--format", self.config["video_quality"]])
                
                # Execute
                self.logger.debug(f"Executing yt-dlp command: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    shell=False, 
                    timeout=self.config["stream_timeout"]
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    url = result.stdout.strip().split('\n')[0]
                    self.logger.info(f"Retrieved stream URL for: {query[:50]}...")
                    return url
                else:
                    self.logger.warning(f"yt-dlp attempt {attempt + 1} failed: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                self.logger.warning(f"yt-dlp timeout on attempt {attempt + 1}")
            except FileNotFoundError:
                self.logger.error("yt-dlp not found. Please install from https://github.com/yt-dlp/yt-dlp")
                return None
            except Exception as e:
                self.logger.error(f"Unexpected error in yt-dlp: {e}")
            
            # Wait before retry
            if attempt < self.config["retry_attempts"] - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        self.logger.error(f"Failed to get stream URL after {self.config['retry_attempts']} attempts: {query}")
        return None
    
    def _create_vlc_instance(self, audio_only: bool = True) -> Optional[vlc.Instance]:
        """Create VLC instance with appropriate parameters"""
        try:
            args = self.config["vlc_audio_args"] if audio_only else self.config["vlc_video_args"]
            instance = vlc.Instance(" ".join(args))
            return instance
        except Exception as e:
            self.logger.error(f"Failed to create VLC instance: {e}")
            return None
    
    def _toggle_video_mode(self, show_video: Optional[bool] = None) -> str:
        """
        Toggle between audio-only and video modes
        
        Args:
            show_video: True for video, False for audio, None to toggle
            
        Returns:
            Status message
        """
        if show_video is None:
            self.show_video = not self.show_video
        else:
            self.show_video = show_video
        
        if not self.vlc_player:
            return "Player not available."
        
        try:
            current_track = self.current_track
            was_playing = self.is_playing
            
            # Stop current playback
            if was_playing:
                self._stop_playback()
                time.sleep(0.5)
            
            # Release old instance
            if self.vlc_instance:
                self.vlc_player.release()
                self.vlc_instance.release()
            
            # Create new instance
            self.vlc_instance = self._create_vlc_instance(not self.show_video)
            if not self.vlc_instance:
                return "Failed to create VLC instance."
            
            self.vlc_player = self.vlc_instance.media_player_new()
            
            # Setup video window if needed
            if self.show_video:
                self.vlc_player.set_hwnd(0)
                self.video_hidden = False
                
                if current_track:
                    self.vlc_player.set_title(f"Music Player - {current_track}")
            
            # Restart playback if needed
            if was_playing and current_track:
                self._play_song(current_track, from_radio=True)
                return f"Switched to {'video' if self.show_video else 'audio'} mode. Playback resumed."
            else:
                return f"Switched to {'video' if self.show_video else 'audio'} mode."
                
        except Exception as e:
            self.logger.error(f"Failed to toggle video mode: {e}")
            return f"Error switching modes: {e}"
    
    def _set_volume(self, level: float) -> bool:
        """
        Set volume level (0.0 to 1.0)
        
        Args:
            level: Volume level between 0.0 and 1.0
            
        Returns:
            Success status
        """
        try:
            # Clamp value
            level = max(0.0, min(1.0, level))
            
            # Set system volume if available
            if self.volume_control:
                self.volume_control.SetMasterVolumeLevelScalar(level, None)
            
            # Set VLC volume as well
            if self.vlc_player:
                self.vlc_player.audio_set_volume(int(level * 100))
            
            self.current_volume = level
            self.logger.info(f"Volume set to {int(level * 100)}%")
            
            # Save preference
            self._save_user_preferences()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Volume control error: {e}")
            return False
    
    def _play_song(self, query: str, from_radio: bool = False) -> Optional[str]:
        """
        Play a song or video
        
        Args:
            query: Song/video query or URL
            from_radio: Whether this is from radio mode
            
        Returns:
            Status message or None if from_radio
        """
        if not self.vlc_player:
            return "Player not available."
        
        # Get stream URL
        url = self._get_stream_url(query, audio_only=not self.show_video)
        if not url:
            if not from_radio:
                return f"Could not find: {query}"
            return None
        
        try:
            # Stop current playback
            if self.is_playing:
                self._stop_playback()
                time.sleep(0.5)
            
            # Load and play media
            media = self.vlc_instance.media_new(url)
            media.add_option(f'network-caching={self.config["cache_duration"]}')
            
            self.vlc_player.set_media(media)
            self.vlc_player.play()
            
            # Wait for playback to start
            for _ in range(10):  # 2 second timeout
                time.sleep(0.2)
                if self.vlc_player.is_playing():
                    break
            
            # Set volume
            self._set_volume(self.current_volume)
            
            # Update state
            with self.state_lock:
                self.current_track = query
                self.is_playing = True
                self.playback_state = PlaybackState.PLAYING
            
            # Setup video window if needed
            if self.show_video and not self.video_hidden:
                self.vlc_player.set_title(f"Music Player - {query[:50]}...")
            
            # Save to history
            track_info = {
                "query": query,
                "url": url,
                "audio_only": not self.show_video,
                "radio_mode": from_radio
            }
            self._save_to_history(track_info)
            
            # Return status message
            if not from_radio:
                mode = "with video" if self.show_video and not self.video_hidden else "audio only"
                return f"Now playing: {query} ({mode})"
            
            self.logger.info(f"Radio playing: {query}")
            return None
            
        except Exception as e:
            self.logger.error(f"Playback error: {e}")
            if not from_radio:
                return f"Failed to play: {query}"
            return None
    
    def _stop_playback(self):
        """Stop current playback"""
        if self.vlc_player:
            self.vlc_player.stop()
        
        with self.state_lock:
            self.is_playing = False
            self.playback_state = PlaybackState.STOPPED
            self.current_position = 0
    
    def _pause_playback(self):
        """Pause current playback"""
        if self.vlc_player and self.is_playing:
            self.vlc_player.pause()
            with self.state_lock:
                self.playback_state = PlaybackState.PAUSED
    
    def _resume_playback(self):
        """Resume paused playback"""
        if self.vlc_player and self.playback_state == PlaybackState.PAUSED:
            self.vlc_player.play()
            with self.state_lock:
                self.playback_state = PlaybackState.PLAYING
                self.is_playing = True
    
    def _skip_to_next(self) -> str:
        """Skip to next track in queue or radio"""
        with self.queue_lock:
            if self.queue:
                next_song = self.queue.pop(0)
                return self._play_song(next_song)
        
        # If radio mode is active, play next radio track
        if self.radio_mode:
            self._play_radio_track()
            return "Skipped. Playing next radio track."
        
        # If continuous play is enabled, play random track
        if self.continuous_play and self.is_playing:
            self._play_radio_track()
            return "Skipped. Playing random track."
        
        return "Skipped. Nothing in queue."
    
    def _play_radio_track(self, genre: Optional[str] = None) -> bool:
        """
        Play a track from radio station
        
        Args:
            genre: Radio station genre
            
        Returns:
            Success status
        """
        if genre:
            self.radio_genre = genre
        
        # Get station queries
        if self.radio_genre in self.RADIO_STATIONS:
            queries = self.RADIO_STATIONS[self.radio_genre]["queries"]
        else:
            # Fallback to all queries
            queries = []
            for station in self.RADIO_STATIONS.values():
                queries.extend(station["queries"])
        
        # Try up to 3 different queries
        for _ in range(3):
            query = random.choice(queries)
            result = self._play_song(query, from_radio=True)
            if result is None:  # Success
                return True
        
        return False
    
    def _add_to_queue(self, query: str) -> int:
        """
        Add song to queue
        
        Args:
            query: Song query
            
        Returns:
            New queue length
        """
        with self.queue_lock:
            if len(self.queue) >= self.config["max_queue_size"]:
                self.queue.pop(0)  # Remove oldest if queue is full
            self.queue.append(query)
            return len(self.queue)
    
    def _clear_queue(self):
        """Clear the playback queue"""
        with self.queue_lock:
            self.queue.clear()
    
    def _get_queue_status(self) -> str:
        """Get formatted queue status"""
        with self.queue_lock:
            if not self.queue:
                return "Queue is empty."
            
            queue_list = []
            for i, song in enumerate(self.queue[:10], 1):
                queue_list.append(f"{i}. {song}")
            
            if len(self.queue) > 10:
                queue_list.append(f"... and {len(self.queue) - 10} more")
            
            return "Queue:\n" + "\n".join(queue_list)
    
    def _get_playback_info(self) -> Dict:
        """Get detailed playback information"""
        info = {
            "current_track": self.current_track,
            "playback_state": self.playback_state.value,
            "volume": int(self.current_volume * 100),
            "video_enabled": self.show_video and not self.video_hidden,
            "radio_mode": self.radio_mode,
            "radio_genre": self.radio_genre,
            "queue_length": len(self.queue),
            "continuous_play": self.continuous_play
        }
        
        if self.vlc_player and self.is_playing:
            try:
                length = self.vlc_player.get_length() / 1000  # Convert to seconds
                current = self.vlc_player.get_time() / 1000
                if length > 0:
                    info["position"] = f"{int(current // 60)}:{int(current % 60):02d}"
                    info["duration"] = f"{int(length // 60)}:{int(length % 60):02d}"
                    info["progress"] = int((current / length) * 100)
            except:
                pass
        
        return info
    
    def _start_background_threads(self):
        """Start background monitoring threads"""
        
        def monitor_playback():
            """Monitor playback state and handle track completion"""
            while True:
                try:
                    if self.vlc_player and self.is_playing:
                        state = self.vlc_player.get_state()
                        
                        # Track ended
                        if state == vlc.State.Ended:
                            time.sleep(1)
                            
                            # Try queue first
                            next_track = None
                            with self.queue_lock:
                                if self.queue:
                                    next_track = self.queue.pop(0)
                            
                            if next_track:
                                self.logger.info(f"Playing next from queue: {next_track}")
                                self._play_song(next_track)
                            # Radio mode
                            elif self.radio_mode:
                                self.logger.info("Playing next radio track")
                                time.sleep(2)
                                self._play_radio_track()
                            # Continuous play
                            elif self.continuous_play and self.is_playing:
                                self.logger.info("Continuing with random track")
                                time.sleep(3)
                                self._play_radio_track()
                            else:
                                with self.state_lock:
                                    self.is_playing = False
                                    self.playback_state = PlaybackState.STOPPED
                                    self.current_track = None
                    
                    time.sleep(2)
                    
                except Exception as e:
                    self.logger.error(f"Playback monitor error: {e}")
                    time.sleep(5)
        
        def monitor_radio():
            """Ensure radio keeps playing"""
            while True:
                try:
                    if self.radio_mode and self.vlc_player:
                        state = self.vlc_player.get_state()
                        
                        # If player stopped but should be playing
                        if state in [vlc.State.Error, vlc.State.Stopped, vlc.State.NothingSpecial]:
                            if self.is_playing:  # Should be playing
                                self.logger.info("Restarting radio playback")
                                time.sleep(2)
                                self._play_radio_track()
                    
                    time.sleep(10)
                    
                except Exception as e:
                    self.logger.error(f"Radio monitor error: {e}")
                    time.sleep(30)
        
        # Start threads
        threading.Thread(target=monitor_playback, daemon=True).start()
        threading.Thread(target=monitor_radio, daemon=True).start()
        self.logger.info("Background threads started")
    
    def _extract_query(self, text: str) -> Optional[str]:
        """Extract music query from text"""
        # Remove command words and common phrases
        patterns_to_remove = [
            r'play\s+', r'listen\s+to\s+', r'put\s+on\s+', r'queue\s+', 
            r'add\s+', r'search\s+for\s+', r'find\s+', r'music\s+',
            r'song\s+', r'track\s+', r'video\s+', r'please\s+',
            r'could\s+you\s+', r'would\s+you\s+', r'can\s+you\s+',
            r'the\s+', r'a\s+', r'an\s+'
        ]
        
        query = text.lower()
        for pattern in patterns_to_remove:
            query = re.sub(pattern, '', query, flags=re.IGNORECASE)
        
        # Remove extra spaces
        query = re.sub(r'\s+', ' ', query).strip()
        
        return query if query else None
    
    def cleanup(self):
        """Clean up resources before shutdown"""
        try:
            self.logger.info("Cleaning up music skill resources...")
            
            # Stop playback
            self._stop_playback()
            
            # Release VLC resources
            if self.vlc_player:
                self.vlc_player.release()
            
            if self.vlc_instance:
                self.vlc_instance.release()
            
            # Save preferences
            self._save_user_preferences()
            
            self.logger.info("Music skill cleanup complete")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def run(self, parameters: dict):
        """
        Main skill execution method
        
        Args:
            parameters: Dictionary containing user_input and other parameters
            
        Returns:
            Response message or None
        """
        text = parameters.get("user_input", "").strip()
        
        # Extract query for music commands
        query = self._extract_query(text)
        
        # --- RADIO / CONTINUOUS PLAY ---
        if any(word in text.lower() for word in ["radio", "background", "continue", "keep playing"]):
            if "stop" in text.lower() or "off" in text.lower():
                self.radio_mode = False
                self.continuous_play = False
                return "Radio mode disabled. Music will stop after current track."
            
            # Set specific genre
            for genre in self.RADIO_STATIONS:
                if genre in text.lower():
                    self.radio_genre = genre
                    self.radio_mode = True
                    if not self.is_playing:
                        self._play_radio_track(genre)
                    station_name = self.RADIO_STATIONS[genre]["name"]
                    return f"{station_name} radio enabled. Music will continue playing."
            
            # General radio
            self.radio_mode = True
            if not self.is_playing:
                self._play_radio_track()
            return "Radio mode enabled. Music will continue playing automatically."
        
        # --- VIDEO CONTROL ---
        if "video" in text.lower():
            if "on" in text.lower() or "show" in text.lower():
                return self._toggle_video_mode(show_video=True)
            elif "off" in text.lower() or "hide" in text.lower():
                return self._toggle_video_mode(show_video=False)
            else:
                return self._toggle_video_mode()
        
        # --- PLAYBACK CONTROL ---
        if any(word in text.lower() for word in ["stop", "hush", "shut up", "quiet"]):
            self._stop_playback()
            self.radio_mode = False
            self.continuous_play = False
            return "Music stopped."
        
        if "pause" in text.lower():
            if self.is_playing:
                self._pause_playback()
                return "Playback paused."
            return "Nothing is playing."
        
        if "resume" in text.lower() or "continue" in text.lower():
            if self.playback_state == PlaybackState.PAUSED:
                self._resume_playback()
                return "Playback resumed."
            return "Playback is not paused."
        
        if any(word in text.lower() for word in ["next", "skip"]):
            return self._skip_to_next()
        
        # --- VOLUME CONTROL ---
        if "volume" in text.lower():
            if "max" in text.lower() or "100" in text.lower():
                self._set_volume(1.0)
                return "Maximum volume! 🔊"
            elif "mute" in text.lower() or "silent" in text.lower():
                self._set_volume(0.0)
                return "Audio muted. 🔇"
            elif any(w in text.lower() for w in ["up", "increase", "louder"]):
                new_vol = min(1.0, self.current_volume + 0.1)
                self._set_volume(new_vol)
                return f"Volume: {int(new_vol * 100)}%"
            elif any(w in text.lower() for w in ["down", "decrease", "quieter", "lower"]):
                new_vol = max(0.0, self.current_volume - 0.1)
                self._set_volume(new_vol)
                return f"Volume: {int(new_vol * 100)}%"
            else:
                return f"Current volume: {int(self.current_volume * 100)}%"
        
        # --- QUEUE MANAGEMENT ---
        if "clear queue" in text.lower():
            self._clear_queue()
            return "Queue cleared."
        
        if "show queue" in text.lower() or "what's in queue" in text.lower():
            return self._get_queue_status()
        
        if "add" in text.lower() and "queue" in text.lower() and query:
            queue_len = self._add_to_queue(query)
            return f"Added '{query}' to queue. ({queue_len} total)"
        
        # --- STATUS / INFO ---
        if any(phrase in text.lower() for phrase in ["what's playing", "current song", "now playing", "status"]):
            info = self._get_playback_info()
            
            if info["current_track"]:
                response = f"Playing: {info['current_track']}\n"
                response += f"Volume: {info['volume']}% | "
                response += f"State: {info['playback_state']}\n"
                
                if "position" in info and "duration" in info:
                    response += f"Progress: {info['position']} / {info['duration']}"
                
                if info['radio_mode']:
                    response += f"\nRadio: {info['radio_genre']}"
                
                return response
            else:
                return "Nothing is playing right now."
        
        if "history" in text.lower():
            if not self.last_played:
                return "No playback history yet."
            
            history_list = []
            for i, track in enumerate(self.last_played[:5], 1):
                track_name = track.get('query', 'Unknown')[:40]
                time_str = track.get('timestamp', 'Unknown time')
                history_list.append(f"{i}. {track_name} ({time_str})")
            
            return "Recent history:\n" + "\n".join(history_list)
        
        if "stations" in text.lower() or "genres" in text.lower():
            stations_list = []
            for genre, info in self.RADIO_STATIONS.items():
                stations_list.append(f"• {genre}: {info['description']}")
            
            return "Available radio stations:\n" + "\n".join(stations_list)
        
        # --- PLAY MUSIC ---
        if any(trigger in text.lower() for trigger in ["play", "music", "song", "listen", "put on"]) and query:
            # Turn off radio mode for specific requests
            self.radio_mode = False
            return self._play_song(query)
        
        # If no specific command but has query, play it
        if query and len(query) > 2:
            return self._play_song(query)
        
        # Default: Start background music if nothing specified
        if not self.is_playing:
            self.radio_mode = True
            self._play_radio_track()
            return "Starting background music. Say 'stop' to pause."
        
        return None


# Test the skill
if __name__ == "__main__":
    def run_tests():
        """Run comprehensive tests"""
        print("🎵 Testing Enhanced Music Skill 🎵")
        print("=" * 50)
        
        skill = None
        try:
            # Initialize skill
            skill = MusicSkill()
            time.sleep(2)
            
            # Test sequence
            tests = [
                ("radio on", "Enable radio mode"),
                ("volume 70", "Set volume to 70%"),
                ("play classical music", "Play specific track"),
                ("add jazz to queue", "Add to queue"),
                ("what's playing", "Show current status"),
                ("next", "Skip to next"),
                ("video on", "Enable video"),
                ("show queue", "Display queue"),
                ("pause", "Pause playback"),
                ("stations", "List radio stations"),
                ("stop", "Stop everything"),
            ]
            
            for command, description in tests:
                print(f"\n🔘 {description}")
                print(f"   Command: {command}")
                result = skill.run({"user_input": command})
                print(f"   Result: {result}")
                time.sleep(2)
            
            print("\n✅ All tests completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if skill:
                skill.cleanup()
    
    # Run tests
    run_tests()