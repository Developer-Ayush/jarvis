# 🤖 JARVIS AI — ALEXA SKILL
## "Alexa, Bhaiya Ji, Sahiba gana chalado"
### Free Forever | No Credit Card | Always On

---

## WHAT THIS DOES

| Feature | How it works |
|---|---|
| 🎵 Music (ad-free) | yt-dlp proxy OR YouTube API + RapidAPI |
| 🔍 Real-time search | Google Search + Groq LLM |
| 🤖 AI answers | Groq (llama-3.1-8b-instant) |
| 🧠 Smart routing | Cohere decides: play/search/chat/etc |
| 🇮🇳 Hindi commands | Full support — bajao, sunao, chalado, etc |

---

## MUSIC MODE — CHOOSE ONE

You have two options for music. Pick whichever suits you.

### Option A: yt-dlp Proxy (RECOMMENDED — no extra keys needed)
- Deploy a second Vercel project (jarvis-ytdlp-proxy folder)
- Set `MUSIC_MODE=proxy` and `YTDLP_PROXY_URL=https://your-proxy.vercel.app`
- No YouTube API key, no RapidAPI key needed
- See Part 1B below

### Option B: YouTube API + RapidAPI
- Get YouTube Data API v3 key (free, Google Cloud Console)
- Get RapidAPI key (free tier, youtube-mp36 API)
- Set `MUSIC_MODE=rapidapi`, `YoutubeAPIKey`, `RapidAPIKey`
- See Part 1C below

---

## PART 0 — GET YOUR FREE API KEYS

### Always needed (both music modes):
| Key | Get it at | Free limit |
|---|---|---|
| Groq | https://console.groq.com | 14,400 req/day |
| Cohere | https://dashboard.cohere.com | 1000 req/month |

### Only for Option B (RapidAPI music):
| Key | Get it at | Free limit |
|---|---|---|
| YouTube Data API v3 | https://console.cloud.google.com → APIs → YouTube Data API v3 | 10,000 units/day |
| RapidAPI (youtube-mp36) | https://rapidapi.com/search/youtube-mp36 → Subscribe free | 500 conversions/month |

---

## PART 1A — DEPLOY MAIN JARVIS SKILL ON VERCEL

### Step 1 — GitHub repo
1. Go to https://github.com → **+** → **New repository**
2. Name: `jarvis-bhaiya` | Set **Private** | Click **Create**

### Step 2 — Upload files
Upload ALL files from the `jarvis-bhaiya` folder:
```
api/index.py
interactionModels/custom/en-US.json
chatbot.py
realtime_search.py
model.py
automation.py
music_player.py
skill.json
vercel.json
requirements.txt
.python-version
```

### Step 3 — Deploy on Vercel
1. Go to https://vercel.com → **Sign Up with GitHub** (no card!)
2. **Add New** → **Project** → find `jarvis-bhaiya` → **Import**
3. Click **Deploy** (leave all defaults)
4. Copy your URL: `https://jarvis-bhaiya.vercel.app`

### Step 4 — Add Environment Variables on Vercel
Go to: Vercel Dashboard → your project → **Settings** → **Environment Variables**

**Always add these:**
| Name | Value |
|---|---|
| `GroqAPIKey` | your-groq-key |
| `CohereApiKey` | your-cohere-key |
| `Username` | Sir |
| `AssistantName` | Jarvis |

**For yt-dlp proxy mode (Option A):**
| Name | Value |
|---|---|
| `MUSIC_MODE` | `proxy` |
| `YTDLP_PROXY_URL` | `https://your-proxy.vercel.app` |

**For RapidAPI mode (Option B):**
| Name | Value |
|---|---|
| `MUSIC_MODE` | `rapidapi` |
| `YoutubeAPIKey` | your-youtube-key |
| `RapidAPIKey` | your-rapidapi-key |

After adding all vars → **Deployments** → 3 dots → **Redeploy**

### Step 5 — Verify
Open: `https://jarvis-bhaiya.vercel.app/`
You should see: `✅ Jarvis AI skill is running!`

If you see ❌, open: `https://jarvis-bhaiya.vercel.app/debug`
It will show exactly what's wrong.

Test music: `https://jarvis-bhaiya.vercel.app/test-music?song=Sahiba`

---

## PART 1B — DEPLOY yt-dlp PROXY (Option A only)

### Step 1 — New GitHub repo
Name it: `jarvis-ytdlp-proxy`

### Step 2 — Upload files from `jarvis-ytdlp-proxy` folder:
```
api/index.py
requirements.txt
vercel.json
```

### Step 3 — Deploy on Vercel
Same steps as main skill. No env vars needed.
Copy the proxy URL: `https://jarvis-ytdlp-proxy.vercel.app`

### Step 4 — Update main skill env vars
In your `jarvis-bhaiya` Vercel project, add:
- `MUSIC_MODE` = `proxy`
- `YTDLP_PROXY_URL` = `https://jarvis-ytdlp-proxy.vercel.app`

Then redeploy the main skill.

---

## PART 1C — GET YouTube + RapidAPI KEYS (Option B only)

### YouTube Data API v3:
1. Go to https://console.cloud.google.com
2. Create a new project (or use existing)
3. Search for **YouTube Data API v3** → Enable
4. Go to **Credentials** → **Create Credentials** → **API Key**
5. Copy the key

### RapidAPI (youtube-mp36):
1. Go to https://rapidapi.com
2. Sign up (free)
3. Search for **youtube-mp36**
4. Subscribe to the **Basic** (free) plan
5. Go to the API page → copy your **X-RapidAPI-Key**

---

## PART 2 — CREATE ALEXA SKILL

### Step 1 — Amazon Developer Account
1. Go to https://developer.amazon.com
2. Sign in with your **same Amazon account** as your Echo device
3. No payment needed

### Step 2 — Create Skill
1. Go to https://developer.amazon.com/alexa/console/ask
2. Click **Create Skill**
3. Fill in:
   - Skill name: `Bhaiya Ji`
   - Primary locale: **English (US)**
   - Model: **Custom**
   - Backend: **Provision your own**
4. Click **Create skill** → **Start from scratch** → **Continue**

### Step 3 — Set Invocation Name
1. Left sidebar → **Invocations** → **Skill Invocation Name**
2. Type: `bhaiya ji`
3. Click **Save Model**

### Step 4 — Import Voice Model
1. Left sidebar → **JSON Editor**
2. Select ALL and DELETE existing text
3. Open `interactionModels/custom/en-US.json`
4. Copy ALL contents → paste into JSON Editor
5. Click **Save Model**
6. Click **Build Model** (takes ~2 minutes)

### Step 5 — Enable Audio Player (REQUIRED for music)
1. Left sidebar → **Interfaces**
2. Find **Audio Player** → toggle **ON**
3. **Save Interfaces** → **Build Model** again

### Step 6 — Set Endpoint
1. Left sidebar → **Endpoint**
2. Select **HTTPS**
3. Paste in **Default Region** box:
   ```
   https://jarvis-bhaiya.vercel.app/alexa
   ```
4. SSL Certificate: select **"My development endpoint has a certificate from a trusted certificate authority"**
5. Click **Save Endpoints**

### Step 7 — Test
1. Click **Test** tab → change dropdown to **Development**
2. Type: `open bhaiya ji`
3. You should hear: "Namaste Sir! Main Jarvis hoon."
4. Type: `Sahiba gana chalado`
5. Music plays!

### Step 8 — Enable on Echo Device
1. Open **Alexa app** on phone
2. **More** → **Skills & Games** → **Your Skills** → **Dev** tab
3. Tap **Bhaiya Ji** → **Enable**

Now say on your Echo:
```
"Alexa, Bhaiya Ji, Sahiba gana chalado"
```

---

## ALL VOICE COMMANDS

| Say this | What happens |
|---|---|
| `Alexa, Bhaiya Ji` | Opens skill, greets in Hindi |
| `Sahiba gana chalado` | Streams Sahiba ad-free |
| `Tum Hi Ho bajao` | Streams Tum Hi Ho |
| `play Shape of You` | Streams any song |
| `Arijit Singh ka gana sunao` | Plays Arijit Singh song |
| `aaj ka news kya hai` | Real-time news |
| `who is Virat Kohli` | AI answer |
| `search google for best phones` | Reads Google results |
| `write an email to my boss about leave` | Groq writes it |
| `Alexa, pause` | Pauses music |
| `Alexa, resume` | Resumes music |
| `Alexa, stop` | Stops everything |

---

## TROUBLESHOOTING

| Problem | Check |
|---|---|
| Health page shows ❌ | Go to `/debug` — it shows exact errors |
| "There was a problem" on Echo | Env vars missing in Vercel |
| Music not playing | `/test-music?song=Sahiba` to test directly |
| AudioPlayer errors | Re-enable AudioPlayer interface + rebuild model |
| Skill not on Echo | Re-enable in Alexa app → Dev tab |
| Cohere model error | Already fixed in this version — uses fallback models |

**View real-time logs:**
Vercel Dashboard → Project → **Functions** tab → click `/api/index`

---

## COST BREAKDOWN

| Service | Free Limit | Your Usage |
|---|---|---|
| Vercel | 100GB bandwidth/month | ~0.5GB |
| Groq | 14,400 req/day | ~10-50/day |
| Cohere | 1000 req/month | ~10-50/month |
| yt-dlp proxy | Unlimited | Free, open source |
| YouTube API | 10,000 units/day | ~10/day (Option B) |
| RapidAPI mp36 | 500/month | ~10-50/month (Option B) |

**Total cost: ₹0 / $0 forever** ✅
