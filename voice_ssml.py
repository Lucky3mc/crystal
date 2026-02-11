# voice_ssml.py

VOICE_PROFILES = {
    "gentle": ("medium", "+2%", "300ms"),
    "playful": ("fast", "+8%", "150ms"),
    "cold": ("slow", "-6%", "400ms"),
    "protective": ("medium", "-2%", "250ms"),
}

def humanize(text):
    return (
        text.replace("...", "<break time='500ms'/>")
            .replace(",", ",<break time='120ms'/>")
            .replace(".", ".<break time='220ms'/>")
    )

def build_ssml(text, state):
    rate, pitch, pause = VOICE_PROFILES[state.personality]
    intimacy_boost = int(state.intimacy * 5)
    final_pitch = f"+{int(pitch.replace('%','')) + intimacy_boost}%"

    return f"""
<speak>
  <prosody rate="{rate}" pitch="{final_pitch}">
    <break time="{pause}"/>
    {humanize(text)}
  </prosody>
</speak>
"""
