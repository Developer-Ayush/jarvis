"""
api/index.py — Jarvis AI Alexa Skill (Vercel entry point)
ARCHITECTURE: Single QueryIntent catches everything.
              Cohere (FirstLayerDMM) classifies and routes:
              play -> YouTube MP3 stream
              realtime -> Google Search + Groq summary
              general -> Groq LLM
"""

import sys
import os
import json
import logging
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── oscrypto patch ─────────────────────────────────────────────────────────────
try:
    import re
    from cffi import FFI
    import ctypes.util
    import oscrypto._openssl._libcrypto_cffi as _lc

    _lib = ctypes.util.find_library("crypto")
    if _lib:
        _ffi = FFI()
        try:
            _ffi.cdef("const char *OpenSSL_version(int type);")
            _ver_str = _ffi.string(_ffi.dlopen(_lib).OpenSSL_version(0)).decode("utf-8")
        except Exception:
            _ffi2 = FFI()
            _ffi2.cdef("const char *SSLeay_version(int type);")
            _ver_str = _ffi2.string(_ffi2.dlopen(_lib).SSLeay_version(0)).decode("utf-8")

        _m = re.search(r"\b(\d+\.\d+\.\d+[a-z]*)\b", _ver_str)
        if _m and not hasattr(_lc, "_patched"):
            _version = _m.group(1)
            _version_parts = re.sub(r"(\d)([a-z]+)", r"\1.\2", _version).split(".")
            _version_info = tuple(int(p) if p.isdigit() else p for p in _version_parts)
            _lc.version      = _version
            _lc.version_info = _version_info
            _lc._patched     = True
            logger.info(f"oscrypto patched: {_version}")
except Exception as _patch_err:
    logger.warning(f"oscrypto patch skipped: {_patch_err}")
# ── end oscrypto patch ─────────────────────────────────────────────────────────

IMPORT_ERRORS = {}
SKILL_ERROR   = None
skill_handler = None

# ── imports ────────────────────────────────────────────────────────────────────
try:
    from flask import Flask, request, jsonify
except Exception:
    IMPORT_ERRORS["flask"] = traceback.format_exc()

try:
    from ask_sdk_core.skill_builder import SkillBuilder
    from ask_sdk_core.utils import is_request_type, is_intent_name
    from ask_sdk_model.interfaces.audioplayer import (
        PlayDirective, PlayBehavior, AudioItem, Stream,
    )
    from ask_sdk_webservice_support.webservice_handler import WebserviceSkillHandler
except Exception:
    IMPORT_ERRORS["ask_sdk"] = traceback.format_exc()

try:
    from chatbot import ChatBot
except Exception:
    IMPORT_ERRORS["chatbot"] = traceback.format_exc()

try:
    from model import FirstLayerDMM
except Exception:
    IMPORT_ERRORS["model"] = traceback.format_exc()

try:
    from realtime_search import RealtimeSearchEngine
except Exception:
    IMPORT_ERRORS["realtime_search"] = traceback.format_exc()

try:
    from automation import handle_automation
except Exception:
    IMPORT_ERRORS["automation"] = traceback.format_exc()

try:
    from music_player import get_youtube_stream
except Exception:
    IMPORT_ERRORS["music_player"] = traceback.format_exc()

for mod, err in IMPORT_ERRORS.items():
    logger.error(f"IMPORT FAILED [{mod}]:\n{err}")

USERNAME       = os.environ.get("Username", "Sir")
ASSISTANT_NAME = os.environ.get("AssistantName", "Jarvis")
app = Flask(__name__)


# ── Core routing function ──────────────────────────────────────────────────────

def _route_query(query: str, handler_input):
    """
    Everything flows here.
    1. Automations check (open/close/reminder etc.)
    2. Cohere classifies
    3. Route: play -> YouTube, realtime -> Google+Groq, general -> Groq
    """
    logger.info(f"Routing query: '{query}'")

    # Step 1: automations
    auto = handle_automation(query.lower())
    if auto:
        return handler_input.response_builder.speak(auto).ask("Aur kuch?").response

    # Step 2: Cohere classifies
    decisions = FirstLayerDMM(query)
    logger.info(f"Cohere decisions: {decisions}")

    answer = ""

    for d in decisions:

        # ── Music ──────────────────────────────────────────────────────────────
        if d.startswith("play "):
            song = d.removeprefix("play ").strip()
            stream_url, title, _ = get_youtube_stream(song)
            if stream_url:
                return (
                    handler_input.response_builder
                    .speak(f"Bajata hoon {title}.")
                    .add_directive(
                        PlayDirective(
                            play_behavior=PlayBehavior.REPLACE_ALL,
                            audio_item=AudioItem(
                                stream=Stream(
                                    token=title,
                                    url=stream_url,
                                    offset_in_milliseconds=0,
                                )
                            ),
                        )
                    )
                    .set_should_end_session(True)
                    .response
                )
            answer = f"Sorry {USERNAME}, {song} nahi chal pa raha abhi."

        # ── Realtime (Google Search + Groq) ───────────────────────────────────
        elif d.startswith("realtime "):
            answer = RealtimeSearchEngine(d.removeprefix("realtime ").strip())

        # ── General (Groq LLM only) ───────────────────────────────────────────
        elif d.startswith("general "):
            answer = ChatBot(d.removeprefix("general ").strip())

        # ── Google Search ─────────────────────────────────────────────────────
        elif d.startswith("google search "):
            answer = handle_automation(d)

        # ── YouTube Search ────────────────────────────────────────────────────
        elif d.startswith("youtube search "):
            answer = handle_automation(d)

        # ── Content writing ───────────────────────────────────────────────────
        elif d.startswith("content "):
            answer = handle_automation(d)

        # ── Exit ──────────────────────────────────────────────────────────────
        elif d == "exit":
            return (
                handler_input.response_builder
                .speak(f"Alvida {USERNAME}! Take care.")
                .set_should_end_session(True)
                .response
            )

        # ── Unknown fallback ──────────────────────────────────────────────────
        else:
            answer = ChatBot(query)

    return (
        handler_input.response_builder
        .speak(answer or "Samajh nahi aaya, dobara boliye.")
        .ask("Aur kuch?")
        .response
    )


# ── Build Alexa skill ──────────────────────────────────────────────────────────
if not IMPORT_ERRORS:
    try:
        sb = SkillBuilder()

        @sb.request_handler(can_handle_func=is_request_type("LaunchRequest"))
        def launch_handler(handler_input):
            speech = f"Namaste {USERNAME}! Main {ASSISTANT_NAME} hoon. Kya seva kar sakta hoon?"
            return (
                handler_input.response_builder
                .speak(speech)
                .ask("Haan boliye, main sun raha hoon.")
                .response
            )

        @sb.request_handler(can_handle_func=is_intent_name("QueryIntent"))
        def query_handler(handler_input):
            slots = handler_input.request_envelope.request.intent.slots
            query = slots["query"].value if slots.get("query") else None
            if not query:
                return (
                    handler_input.response_builder
                    .speak("Haan boliye, kya jaanna chahte hain?")
                    .ask("Batao.")
                    .response
                )
            return _route_query(query, handler_input)

        @sb.request_handler(can_handle_func=is_intent_name("AMAZON.FallbackIntent"))
        def fallback_handler(handler_input):
            return (
                handler_input.response_builder
                .speak("Samajh nahi aaya, dobara boliye.")
                .ask("Dobara boliye.")
                .response
            )

        @sb.request_handler(can_handle_func=is_intent_name("AMAZON.StopIntent"))
        def stop_handler(handler_input):
            return (
                handler_input.response_builder
                .speak(f"Theek hai {USERNAME}.")
                .set_should_end_session(True)
                .response
            )

        @sb.request_handler(can_handle_func=is_intent_name("AMAZON.CancelIntent"))
        def cancel_handler(handler_input):
            return handler_input.response_builder.set_should_end_session(True).response

        @sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
        def help_handler(handler_input):
            speech = (
                f"Main {ASSISTANT_NAME} hoon. "
                "Gana bajane ke liye boliye 'Sahiba gana chalado'. "
                "Koi bhi sawaal poochh sakte hain jaise 'Virat Kohli kon hai'. "
                "News ke liye 'aaj ka news kya hai'."
            )
            return (
                handler_input.response_builder
                .speak(speech)
                .ask("Kya help chahiye?")
                .response
            )

        @sb.request_handler(can_handle_func=is_intent_name("AMAZON.PauseIntent"))
        def pause_handler(handler_input):
            return handler_input.response_builder.response

        @sb.request_handler(can_handle_func=is_intent_name("AMAZON.ResumeIntent"))
        def resume_handler(handler_input):
            return handler_input.response_builder.response

        @sb.request_handler(can_handle_func=is_request_type("SessionEndedRequest"))
        def session_ended_handler(handler_input):
            error = getattr(handler_input.request_envelope.request, "error", None)
            if error:
                logger.error(f"SessionEnded error: {error}")
            return handler_input.response_builder.response

        # ── AudioPlayer events ────────────────────────────────────────────────

        @sb.request_handler(can_handle_func=is_request_type("AudioPlayer.PlaybackStarted"))
        def playback_started(h): return h.response_builder.response

        @sb.request_handler(can_handle_func=is_request_type("AudioPlayer.PlaybackFinished"))
        def playback_finished(h): return h.response_builder.response

        @sb.request_handler(can_handle_func=is_request_type("AudioPlayer.PlaybackStopped"))
        def playback_stopped(h): return h.response_builder.response

        @sb.request_handler(can_handle_func=is_request_type("AudioPlayer.PlaybackFailed"))
        def playback_failed(h):
            logger.error("AudioPlayer.PlaybackFailed")
            return h.response_builder.response

        @sb.request_handler(can_handle_func=is_request_type("PlaybackController.PlayCommandIssued"))
        def playback_command(h): return h.response_builder.response

        # ── Catch-all for any unhandled request type ──────────────────────────

        @sb.request_handler(can_handle_func=lambda input: True)
        def catch_all_handler(handler_input):
            request_type = handler_input.request_envelope.request.object_type
            logger.warning(f"Unhandled request type: {request_type}")
            return (
                handler_input.response_builder
                .speak("Haan boliye, main sun raha hoon.")
                .ask("Kya help chahiye?")
                .response
            )

        # ── Global error handler ──────────────────────────────────────────────

        @sb.exception_handler(can_handle_func=lambda i, e: True)
        def error_handler(handler_input, exception):
            logger.error(f"Skill error: {exception}", exc_info=True)
            return (
                handler_input.response_builder
                .speak("Kuch gadbad ho gayi. Dobara try karein.")
                .ask("Dobara boliye.")
                .response
            )

        skill_handler = WebserviceSkillHandler(
            skill=sb.create(),
            verify_signature=False,
            verify_timestamp=False,
        )
        logger.info("✅ Alexa skill built successfully")

    except BaseException as e:
        SKILL_ERROR = traceback.format_exc()
        logger.error(f"SKILL BUILD FAILED:\n{SKILL_ERROR}")


# ── Flask routes ───────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def health():
    if IMPORT_ERRORS or SKILL_ERROR:
        problems = list(IMPORT_ERRORS.keys()) + (["skill_build"] if SKILL_ERROR else [])
        return f"❌ Errors in: {', '.join(problems)}. Check /debug for details.", 500
    return (
        f"✅ {ASSISTANT_NAME} AI skill is running!\n"
        f"Alexa endpoint: /alexa\n"
        f"Test music: /test-music?song=Sahiba\n"
        f"Debug info: /debug"
    )


@app.route("/debug", methods=["GET"])
def debug():
    return jsonify({
        "import_errors": IMPORT_ERRORS,
        "skill_error":   SKILL_ERROR,
        "skill_ready":   skill_handler is not None,
        "env_vars_set": {
            "GroqAPIKey":    bool(os.environ.get("GroqAPIKey")),
            "CohereApiKey":  bool(os.environ.get("CohereApiKey")),
            "RapidAPIKey":   bool(os.environ.get("RapidAPIKey")),
            "Username":      bool(os.environ.get("Username")),
            "AssistantName": bool(os.environ.get("AssistantName")),
        }
    })


@app.route("/alexa", methods=["POST"])
def alexa_endpoint():
    if skill_handler is None:
        logger.error("skill_handler is None — skill not initialized")
        return jsonify({"error": "skill not initialized — check /debug"}), 500
    try:
        response = skill_handler.verify_request_and_dispatch(
            http_request_headers=dict(request.headers),
            http_request_body=request.data.decode("utf-8"),
        )
        if response is None:
            logger.error("verify_request_and_dispatch returned None")
            return jsonify({"error": "null response from skill"}), 500

        if isinstance(response, bytes):
            response = response.decode("utf-8")
        if isinstance(response, dict):
            response = json.dumps(response)

        logger.info(f"Alexa response preview: {str(response)[:300]}")
        return app.response_class(
            response=response,
            status=200,
            mimetype="application/json"
        )
    except BaseException as e:
        logger.error(f"ALEXA ENDPOINT ERROR: {type(e).__name__}: {e}", exc_info=True)
        return jsonify({"error": f"{type(e).__name__}: {str(e)}"}), 500


@app.route("/test-music", methods=["GET"])
def test_music():
    if "music_player" in IMPORT_ERRORS:
        return jsonify({"error": IMPORT_ERRORS["music_player"]}), 500
    song = request.args.get("song", "Sahiba")
    url, title, _ = get_youtube_stream(song)
    if url:
        return jsonify({"status": "ok", "title": title, "url": url[:80] + "..."})
    return jsonify({
        "status": "error",
        "message": f"Stream not found for '{song}'",
        "tip": "Check RapidAPIKey is set in Vercel env vars.",
    }), 500


application = app
handler     = app
