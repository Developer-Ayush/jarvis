"""
realtime_search.py — Jarvis AI Alexa Skill
"""

import datetime
import os
import logging
import requests
from groq import Groq

logger = logging.getLogger(__name__)

USERNAME       = os.environ.get("Username", "Sir")
ASSISTANT_NAME = os.environ.get("AssistantName", "Jarvis")
GROQ_API_KEY   = os.environ.get("GroqAPIKey", "")

_client = None

def _get_client():
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise RuntimeError("GroqAPIKey environment variable is not set!")
        _client = Groq(api_key=GROQ_API_KEY)
    return _client

SYSTEM_PROMPT = f"""You are {ASSISTANT_NAME}, an advanced AI assistant.
Rules:
- Maximum 4 sentences. Spoken aloud by Alexa — no lists, no markdown.
- Plain English, professional tone.
- Answer as accurately as possible from your knowledge.
- If you are not sure about current/realtime data, say so briefly."""

_BASE_CHAT = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user",   "content": "Hi"},
    {"role": "assistant", "content": "Hello, how can I help you?"},
]

# ── Weather keywords ───────────────────────────────────────────────────────────
WEATHER_KEYWORDS = [
    "temperature", "temprature", "mausam", "weather", "garmi", "sardi",
    "celsius", "fahrenheit", "humidity", "kitni garmi", "kitni thand",
    "barish", "rain", "forecast", "temp", "aaj ka mausam"
]


def _is_weather_query(prompt: str) -> bool:
    prompt_lower = prompt.lower()
    return any(word in prompt_lower for word in WEATHER_KEYWORDS)


def _extract_city(prompt: str) -> str:
    prompt_lower = prompt.lower()
    remove_words = [
        "aaj", "ka", "ki", "ke", "mein", "temperature", "temprature",
        "mausam", "weather", "kaisa", "kya", "hai", "batao", "bata",
        "abhi", "garmi", "sardi", "kitni", "celsius", "temp", "today",
        "current", "what", "is", "the", "in", "of", "how", "tell", "me"
    ]
    words = prompt_lower.split()
    city_words = [w for w in words if w not in remove_words and len(w) > 2]
    city = " ".join(city_words).strip()
    if not city:
        city = "Delhi"
    logger.info(f"Extracted city: '{city}'")
    return city


def _get_weather(prompt: str) -> str:
    city = _extract_city(prompt)
    try:
        # Step 1: Geocode city
        geo_resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=8
        )
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            return f"I could not find weather data for {city}. Please check the city name."

        result    = geo_data["results"][0]
        lat       = result["latitude"]
        lon       = result["longitude"]
        city_name = result.get("name", city)
        country   = result.get("country", "")
        logger.info(f"Geocoded '{city}' → {city_name}, {country}")

        # Step 2: Fetch weather
        weather_resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":            lat,
                "longitude":           lon,
                "current":             "temperature_2m,relative_humidity_2m,windspeed_10m,apparent_temperature",
                "daily":               "temperature_2m_max,temperature_2m_min",
                "timezone":            "auto",
                "forecast_days":       1,
            },
            timeout=8
        )
        w        = weather_resp.json()
        current  = w.get("current", {})
        daily    = w.get("daily", {})

        temp       = current.get("temperature_2m", "N/A")
        feels_like = current.get("apparent_temperature", "N/A")
        humidity   = current.get("relative_humidity_2m", "N/A")
        wind       = current.get("windspeed_10m", "N/A")
        temp_max   = daily.get("temperature_2m_max", [None])[0]
        temp_min   = daily.get("temperature_2m_min", [None])[0]

        response = (
            f"The current temperature in {city_name} is {temp} degrees Celsius, "
            f"feels like {feels_like} degrees. "
            f"Humidity is {humidity} percent, wind speed {wind} kilometres per hour. "
        )
        if temp_max and temp_min:
            response += f"Today's high is {temp_max} and low is {temp_min} degrees Celsius."

        return response

    except Exception as e:
        logger.error(f"Weather error: {e}")
        return f"I had trouble fetching weather for {city}. Please try again."


def _now_info() -> str:
    n = datetime.datetime.now()
    return f"Current date and time: {n.strftime('%A, %d %B %Y, %H:%M:%S')}."


def _clean(text: str) -> str:
    lines = [l for l in text.split("\n") if l.strip()]
    return " ".join(lines).replace("</s>", "").strip()


def RealtimeSearchEngine(prompt: str) -> str:

    # ── Weather: use Open-Meteo directly ──────────────────────────────────────
    if _is_weather_query(prompt):
        logger.info(f"Weather query: '{prompt}'")
        return _get_weather(prompt)

    # ── Everything else: straight to Groq ─────────────────────────────────────
    logger.info(f"Sending directly to Groq: '{prompt}'")
    system_messages = _BASE_CHAT + [
        {"role": "system", "content": _now_info()},
    ]
    messages = [{"role": "user", "content": prompt}]

    try:
        client = _get_client()
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=system_messages + messages,
            temperature=0.7,
            max_tokens=300,
            top_p=1,
            stream=True,
        )
        answer = ""
        for chunk in completion:
            delta = chunk.choices[0].delta.content
            if delta:
                answer += delta
        return _clean(answer)

    except Exception as exc:
        logger.error(f"RealtimeSearchEngine error: {exc}", exc_info=True)
        return "I could not fetch information right now. Please try again."
