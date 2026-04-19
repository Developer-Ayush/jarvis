"""
music_player.py — Jarvis AI Alexa Skill

Inspired by pywhatkit.playonyt() from the desktop Jarvis repo.

Flow:
  1. Scrape youtube.com/results?q=<query> to get the first video ID
     (same technique as pywhatkit — free, no API key, just a plain HTML GET)
  2. Pass the video ID to RapidAPI youtube-mp36 to get a direct MP3 URL
     (one free RapidAPI key, 500 conversions/month)

Why this works from Vercel:
  - YouTube blocks VIDEO DOWNLOAD requests from datacenter IPs
  - But youtube.com/results is a public webpage served to everyone (for SEO)
  - So scraping search results HTML works fine from Vercel
  - The mp3 conversion is done by RapidAPI (their servers, not Vercel hitting YouTube)

Keys needed: ONLY RapidAPIKey (one key, subscribe free to youtube-mp36 on rapidapi.com)
"""

import os
import re
import requests
import logging
import time

logger = logging.getLogger(__name__)

RAPIDAPI_KEY = os.environ.get("RapidAPIKey", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _youtube_search(query: str):
    """
    Scrape YouTube search results to find the first video ID and title.
    Exactly like pywhatkit.playonyt() but returns ID instead of opening browser.
    Returns (video_id, title) or (None, None).
    """
    try:
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        r = requests.get(url, headers=HEADERS, timeout=8)

        if r.status_code != 200:
            logger.error(f"YouTube search returned {r.status_code}")
            return None, None

        # Extract video IDs — same data pywhatkit parses
        video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', r.text)
        # Extract titles alongside — grab first title near first video ID
        titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"', r.text)

        if not video_ids:
            logger.error(f"No video IDs found for: {query}")
            return None, None

        video_id = video_ids[0]
        title = titles[0] if titles else query
        logger.info(f"YouTube found: '{title}' ({video_id})")
        return video_id, title

    except Exception as e:
        logger.error(f"YouTube scrape error: {e}")
        return None, None


def _mp36_audio_url(video_id: str):
    """
    Get direct MP3 URL from RapidAPI youtube-mp36.
    Subscribe free at: https://rapidapi.com/yosefbiu/api/youtube-mp36
    Returns audio URL string or None.
    """
    if not RAPIDAPI_KEY:
        logger.error("RapidAPIKey not set in Vercel env vars!")
        return None

    headers = {
        "X-RapidAPI-Key":  RAPIDAPI_KEY,
        "X-RapidAPI-Host": "youtube-mp36.p.rapidapi.com",
    }

    try:
        r = requests.get(
            "https://youtube-mp36.p.rapidapi.com/dl",
            params={"id": video_id},
            headers=headers,
            timeout=12,
        )
        if r.status_code != 200:
            logger.error(f"youtube-mp36 {r.status_code}: {r.text[:200]}")
            return None

        d = r.json()
        logger.info(f"youtube-mp36 status: {d.get('status')}")

        if d.get("status") == "ok":
            return d.get("link")

        # Poll if still converting
        if d.get("status") == "processing":
            for attempt in range(4):
                time.sleep(2)
                r2 = requests.get(
                    "https://youtube-mp36.p.rapidapi.com/dl",
                    params={"id": video_id},
                    headers=headers,
                    timeout=8,
                )
                if r2.status_code == 200:
                    d2 = r2.json()
                    logger.info(f"Poll {attempt+1}: {d2.get('status')}")
                    if d2.get("status") == "ok":
                        return d2.get("link")

        logger.error(f"youtube-mp36 failed: {d}")
        return None

    except Exception as e:
        logger.error(f"youtube-mp36 error: {e}")
        return None


def get_youtube_stream(query: str):
    """
    Main function called by api/index.py

    Returns (stream_url, title, None) on success.
    Returns (None, None, None) on failure.

    Usage:
      Set in Vercel env vars:
        RapidAPIKey = your key from rapidapi.com
      Subscribe free to: youtube-mp36 on rapidapi.com (500/month free)
      No YouTube API key needed — search is done by scraping public HTML.
    """
    # Step 1: Find the video (free, no key, like pywhatkit)
    video_id, title = _youtube_search(query)
    if not video_id:
        return None, None, None

    # Step 2: Get audio URL (RapidAPI, one key)
    audio_url = _mp36_audio_url(video_id)
    if not audio_url:
        return None, None, None

    logger.info(f"Stream ready: '{title}' -> {audio_url[:60]}")
    return audio_url, title, None
