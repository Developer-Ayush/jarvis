"""
model.py — Jarvis AI Alexa Skill
Decision-making layer using Cohere.
"""

import os
import logging
import cohere

logger = logging.getLogger(__name__)

COHERE_API_KEY = os.environ.get("CohereApiKey", "")

_co = None

def _get_client():
    global _co
    if _co is None:
        if not COHERE_API_KEY:
            raise RuntimeError("CohereApiKey environment variable is not set!")
        _co = cohere.Client(api_key=COHERE_API_KEY)
    return _co


FUNCS = [
    "exit", "general", "realtime", "play",
    "google search", "youtube search",
    "content", "reminder", "generate image",
]

PREAMBLE = """
You are a Decision-Making Model. Classify the user's query into one of the categories below.
DO NOT answer the query — only classify it.

Categories:
-> 'general (query)'        — answerable by an LLM, no real-time data needed.
-> 'realtime (query)'       — needs current internet data (news, prices, who is X right now, etc.).
                              Also use for ANY question about a person, celebrity, politician,
                              sportsperson, actor, singer — even if phrased in Hindi.
                              Hindi patterns that mean "who is X":
                              "kon hai", "kaun hai", "ke bare mein batao", "kya karta hai",
                              "kaun hain", "kiske baare mein", "koun hai".
-> 'play (song name)'       — user wants to play/listen to ANYTHING that can be played as audio.
                              This includes:
                              - Songs: Bollywood, English, devotional, classical, folk
                              - Devotional/religious audio: Hanuman Chalisa, Gayatri Mantra,
                                Aarti, Bhajan, Kirtan, Quran, Bible, any prayer or mantra
                              - Artist names: play their songs
                              - Any audio content the user wants to hear
                              Triggered by Hindi phrases:
                              'gana chalado', 'bajao', 'sunao', 'lagao', 'play karo',
                              'gana laga do', 'chalao', 'play', 'suno', 'lagao'.
                              IMPORTANT: If the user says play/bajao/sunao with ANY name —
                              even if it sounds religious or informational — classify as 'play'.
                              Example: 'Hanuman Chalisa bajao' -> 'play Hanuman Chalisa'
                              Example: 'Gayatri Mantra sunao' -> 'play Gayatri Mantra'
                              Example: 'bhaiya Hanuman Chalisa' -> 'play Hanuman Chalisa'
                              Example: 'play Hanuman Chalisa' -> 'play Hanuman Chalisa'
                              Example: 'Sahiba gana chalado' -> 'play Sahiba'
                              Example: 'Tum Hi Ho bajao' -> 'play Tum Hi Ho'
                              Example: 'play Shape of You' -> 'play Shape of You'
-> 'google search (topic)'  — user wants to search Google.
-> 'youtube search (topic)' — user wants to search YouTube (NOT play, just search).
-> 'content (topic)'        — user wants written content: essay, email, code, poem, etc.
-> 'reminder (datetime msg)'— user wants a reminder set.
-> 'exit'                   — user says goodbye / wants to end the conversation.
-> 'general (query)'        — fallback for anything not listed above.

CRITICAL RULE: If the query contains bajao, sunao, chalado, lagao, play, suno, chalao
— it is ALWAYS 'play', never 'general' or 'realtime'. No exceptions.

For multiple tasks, comma-separate: 'play Sahiba, general who sang Sahiba'
"""

CHAT_HISTORY = [
    {"role": "User",    "message": "how are you"},
    {"role": "Chatbot", "message": "general how are you"},
    {"role": "User",    "message": "Sahiba gana chalado"},
    {"role": "Chatbot", "message": "play Sahiba"},
    {"role": "User",    "message": "Tum Hi Ho bajao"},
    {"role": "Chatbot", "message": "play Tum Hi Ho"},
    {"role": "User",    "message": "play Shape of You"},
    {"role": "Chatbot", "message": "play Shape of You"},
    {"role": "User",    "message": "Arijit Singh ka gana sunao"},
    {"role": "Chatbot", "message": "play Arijit Singh"},
    {"role": "User",    "message": "aaj ka news kya hai"},
    {"role": "Chatbot", "message": "realtime today's news"},
    {"role": "User",    "message": "who is the PM of India"},
    {"role": "Chatbot", "message": "realtime who is the PM of India"},
    {"role": "User",    "message": "search google for best restaurants"},
    {"role": "Chatbot", "message": "google search best restaurants"},
    {"role": "User",    "message": "search youtube for lofi music"},
    {"role": "Chatbot", "message": "youtube search lofi music"},
    {"role": "User",    "message": "write an email to my boss"},
    {"role": "Chatbot", "message": "content email to boss"},
    {"role": "User",    "message": "bye"},
    {"role": "Chatbot", "message": "exit"},
    {"role": "User",    "message": "Virat Kohli kon hai"},
    {"role": "Chatbot", "message": "realtime who is Virat Kohli"},
    {"role": "User",    "message": "Modi kon hai"},
    {"role": "Chatbot", "message": "realtime who is Narendra Modi"},
    {"role": "User",    "message": "kaun hai Sachin Tendulkar"},
    {"role": "Chatbot", "message": "realtime who is Sachin Tendulkar"},
    {"role": "User",    "message": "Amitabh Bachchan kaun hain"},
    {"role": "Chatbot", "message": "realtime who is Amitabh Bachchan"},
    {"role": "User",    "message": "Shah Rukh Khan ke bare mein batao"},
    {"role": "Chatbot", "message": "realtime who is Shah Rukh Khan"},
    {"role": "User",    "message": "Elon Musk kya karta hai"},
    {"role": "Chatbot", "message": "realtime what does Elon Musk do"},
    {"role": "User",    "message": "aaj ka mausam kaisa hai"},
    {"role": "Chatbot", "message": "realtime today's weather"},
    {"role": "User",    "message": "IPL mein aaj kaun jeeta"},
    {"role": "Chatbot", "message": "realtime IPL match result today"},
    {"role": "User",    "message": "dollar ka rate kya hai"},
    {"role": "Chatbot", "message": "realtime dollar exchange rate"},
    {"role": "User",    "message": "petrol ka daam kya hai"},
    {"role": "Chatbot", "message": "realtime petrol price today"},
    # ── Devotional / religious music examples ──────────────────────────────────
    {"role": "User",    "message": "Hanuman Chalisa bajao"},
    {"role": "Chatbot", "message": "play Hanuman Chalisa"},
    {"role": "User",    "message": "play Hanuman Chalisa"},
    {"role": "Chatbot", "message": "play Hanuman Chalisa"},
    {"role": "User",    "message": "bhaiya Hanuman Chalisa"},
    {"role": "Chatbot", "message": "play Hanuman Chalisa"},
    {"role": "User",    "message": "Hanuman Chalisa sunao"},
    {"role": "Chatbot", "message": "play Hanuman Chalisa"},
    {"role": "User",    "message": "Gayatri Mantra sunao"},
    {"role": "Chatbot", "message": "play Gayatri Mantra"},
    {"role": "User",    "message": "Gayatri Mantra bajao"},
    {"role": "Chatbot", "message": "play Gayatri Mantra"},
    {"role": "User",    "message": "Om Namah Shivay bajao"},
    {"role": "Chatbot", "message": "play Om Namah Shivay"},
    {"role": "User",    "message": "Shiv Tandav bajao"},
    {"role": "Chatbot", "message": "play Shiv Tandav"},
    {"role": "User",    "message": "Aarti sunao"},
    {"role": "Chatbot", "message": "play Aarti"},
    {"role": "User",    "message": "bhajan sunao"},
    {"role": "Chatbot", "message": "play bhajan"},
    {"role": "User",    "message": "Shreya Ghoshal ka gana bajao"},
    {"role": "Chatbot", "message": "play Shreya Ghoshal"},
    {"role": "User",    "message": "lofi music chalao"},
    {"role": "Chatbot", "message": "play lofi music"},
    {"role": "User",    "message": "relaxing music sunao"},
    {"role": "Chatbot", "message": "play relaxing music"},
    {"role": "User",    "message": "old hindi songs bajao"},
    {"role": "Chatbot", "message": "play old hindi songs"},
]


def FirstLayerDMM(prompt: str) -> list:
    # ── Hard-coded override for play keywords ──────────────────────────────────
    # If the query contains any play trigger word, skip Cohere and return play directly.
    # This prevents Cohere from misclassifying music requests as general/realtime.
    play_triggers = [
        "bajao", "sunao", "chalado", "lagao", "laga do",
        "chalao", "bajado", "play karo", "gana", "song",
    ]
    prompt_lower = prompt.lower().strip()

    # Check if it starts with "play " — direct play command
    if prompt_lower.startswith("play "):
        song = prompt[5:].strip()
        logger.info(f"Hard-coded play override: 'play {song}'")
        return [f"play {song}"]

    # Check if it contains any Hindi play trigger
    for trigger in play_triggers:
        if trigger in prompt_lower:
            # Extract song name by removing the trigger word and common filler
            song = prompt_lower
            for word in play_triggers + ["bhaiya", "mujhe", "please", "zara", "ek baar"]:
                song = song.replace(word, "").strip()
            song = song.strip(" ,.")
            if song:
                logger.info(f"Hard-coded play override via '{trigger}': 'play {song}'")
                return [f"play {song}"]

    # ── Cohere classification for everything else ──────────────────────────────
    try:
        co = _get_client()
        for model in ["command-r7b-12-2024", "command-r-plus", "command-r"]:
            try:
                stream = co.chat_stream(
                    model=model,
                    message=prompt,
                    temperature=0.7,
                    chat_history=CHAT_HISTORY,
                    prompt_truncation="OFF",
                    connectors=[],
                    preamble=PREAMBLE,
                )
                response = ""
                for event in stream:
                    if event.event_type == "text-generation":
                        response += event.text
                break
            except Exception as model_err:
                logger.warning(f"Model {model} failed: {model_err}, trying next...")
                response = ""
                continue

        if not response:
            return [f"general {prompt}"]

        response = response.replace("\n", "")
        parts = [p.strip() for p in response.split(",")]
        valid = [p for p in parts if any(p.startswith(f) for f in FUNCS)]

        if not valid or "(query)" in " ".join(valid):
            return [f"general {prompt}"]
        return valid

    except Exception as exc:
        logger.error(f"FirstLayerDMM error: {exc}", exc_info=True)
        return [f"general {prompt}"]
