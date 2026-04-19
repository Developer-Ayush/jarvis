"""
music_player.py — Jarvis AI Alexa Skill

Multi-key rotation:
  Set env vars: RapidAPIKey, RapidAPIKey2, RapidAPIKey3, ... (up to any number)
  Keys are tried round-robin on each call.
  If a key returns 429 (rate-limited) or errors, the next key is tried automatically.
"""

import os
import re
import time
import logging
import requests

logger = logging.getLogger(__name__)

# ── Key loader ─────────────────────────────────────────────────────────────────

def _load_api_keys():
    keys = []
    k = os.environ.get("RapidAPIKey", "").strip()
    if k:
        keys.append(k)
    for i in range(2, 20):
        k = os.environ.get(f"RapidAPIKey{i}", "").strip()
        if k:
            keys.append(k)
    for i in range(1, 20):
        k = os.environ.get(f"RAPIDAPI_KEY_{i}", "").strip()
        if k and k not in keys:
            keys.append(k)
    return keys


_API_KEYS = _load_api_keys()
_key_index = 0  # round-robin pointer


# ── YouTube scraper ────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _youtube_search(query):
    try:
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code != 200:
            logger.error(f"YouTube search returned {r.status_code}")
            return None, None

        video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', r.text)
        titles    = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"', r.text)

        if not video_ids:
            logger.error(f"No video IDs found for: {query}")
            return None, None

        video_id = video_ids[0]
        title    = titles[0] if titles else query
        logger.info(f"YouTube found: '{title}' ({video_id})")
        return video_id, title

    except Exception as e:
        logger.error(f"YouTube scrape error: {e}")
        return None, None


# ── RapidAPI caller with key rotation ─────────────────────────────────────────

def _mp36_audio_url(video_id):
    global _key_index  # declared at the very top of the function

    if not _API_KEYS:
        logger.error("No RapidAPI keys found! Set RapidAPIKey, RapidAPIKey2 ... in Vercel env vars.")
        return None

    num_keys = len(_API_KEYS)
    logger.info(f"RapidAPI key pool: {num_keys} key(s) available")

    start_index = _key_index % num_keys
    for attempt in range(num_keys):
        key_pos = (start_index + attempt) % num_keys
        api_key = _API_KEYS[key_pos]
        masked  = api_key[:6] + "..." + api_key[-4:]

        result = _call_mp36(video_id, api_key, masked)
        if result == "RATE_LIMITED":
            logger.warning(f"Key [{key_pos + 1}/{num_keys}] {masked} is rate-limited, trying next...")
            continue
        if result is None:
            logger.warning(f"Key [{key_pos + 1}/{num_keys}] {masked} failed, trying next...")
            continue

        # Success — advance pointer for next call
        _key_index = (key_pos + 1) % num_keys
        logger.info(f"Key [{key_pos + 1}/{num_keys}] {masked} succeeded")
        return result

    logger.error(f"All {num_keys} RapidAPI key(s) exhausted for video {video_id}")
    return None


def _call_mp36(video_id, api_key, masked):
    headers = {
        "X-RapidAPI-Key":  api_key,
        "X-RapidAPI-Host": "youtube-mp36.p.rapidapi.com",
    }
    try:
        r = requests.get(
            "https://youtube-mp36.p.rapidapi.com/dl",
            params={"id": video_id},
            headers=headers,
            timeout=12,
        )

        if r.status_code == 429:
            logger.warning(f"429 Rate-limited: key {masked}")
            return "RATE_LIMITED"

        if r.status_code != 200:
            logger.error(f"youtube-mp36 returned {r.status_code} for key {masked}: {r.text[:120]}")
            return None

        d = r.json()
        status = d.get("status")
        logger.info(f"youtube-mp36 status={status} | key={masked}")

        if status == "ok":
            return d.get("link")

        if status == "processing":
            for poll in range(4):
                time.sleep(2)
                r2 = requests.get(
                    "https://youtube-mp36.p.rapidapi.com/dl",
                    params={"id": video_id},
                    headers=headers,
                    timeout=8,
                )
                if r2.status_code == 429:
                    return "RATE_LIMITED"
                if r2.status_code == 200:
                    d2 = r2.json()
                    logger.info(f"Poll {poll + 1}/4 status={d2.get('status')} | key={masked}")
                    if d2.get("status") == "ok":
                        return d2.get("link")

        logger.error(f"youtube-mp36 did not resolve: {d} | key={masked}")
        return None

    except Exception as e:
        logger.error(f"youtube-mp36 exception for key {masked}: {e}")
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

def get_youtube_stream(query):
    """
    Returns (stream_url, title, None) on success.
    Returns (None, None, None) on failure.
    """
    video_id, title = _youtube_search(query)
    if not video_id:
        return None, None, None

    audio_url = _mp36_audio_url(video_id)
    if not audio_url:
        return None, None, None

    logger.info(f"Stream ready: '{title}' -> {audio_url[:60]}...")
    return audio_url, title, None
