"""Tests détection embed vidéo / live."""
from web_tools import _video_embed_url, _youtube_video_id


def test_youtube_watch_embed():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert _youtube_video_id(url) == "dQw4w9WgXcQ"
    embed = _video_embed_url(url)
    assert embed and "youtube-nocookie.com/embed/dQw4w9WgXcQ" in embed


def test_youtube_live_embed():
    url = "https://www.youtube.com/live/abc123xyz"
    assert _youtube_video_id(url) == "abc123xyz"


def test_twitch_channel_embed():
    url = "https://www.twitch.tv/shroud"
    embed = _video_embed_url(url, parent="emo.example.com")
    assert embed and "player.twitch.tv" in embed
    assert "channel=shroud" in embed
    assert "parent=emo.example.com" in embed


def test_kick_channel_embed():
    url = "https://kick.com/xqc"
    embed = _video_embed_url(url)
    assert embed and "player.kick.com/xqc" in embed
