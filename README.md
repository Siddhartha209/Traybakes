# Traybakes AI Marketing Assistant

A desktop app that uses a team of AI agents to create on-brand marketing content. Describe what you want to promote, and the app researches competitors, writes captions, generates images and lets you fine-tune the result in a built-in editor. Designed to work with short and vague prompts as well as longer descriptive prompts.

---

## Contents

1. [What it does](#what-it-does)
2. [How it works](#how-it-works)
3. [Tech stack](#tech-stack)
4. [Quick start](#quick-start)
5. [Get your API keys (step by step)](#get-your-api-keys-step-by-step)
6. [Where to put your keys](#where-to-put-your-keys)
7. [Run from source](#run-from-source)
8. [Using the app](#using-the-app)
9. [Adding or changing products and brand style](#adding-or-changing-products-and-brand-style)
10. [Build the Windows executable](#build-the-windows-executable)
11. [Project structure](#project-structure)
12. [Files the app creates](#files-the-app-creates)
13. [Running the tests](#running-the-tests)
14. [Troubleshooting](#troubleshooting)
15. [Known issues](#known-issues)
16. [Future work](#future-work)

---

## What it does

| Feature | Description |
|---|---|
| **Smart planning** | An orchestrator reads your request and decides which agents are actually needed, so you don't pay for work you didn't ask for. |
| **Competitor research** | Finds competitors, collects evidence from the web, and reports patterns, gaps and ranked opportunities. |
| **Caption generation** | Produces three caption options per request, with tone control, banned-phrase filtering and iterative self-refinement. |
| **Learning from feedback** | Past liked captions are retrieved and used as examples. Thumbs up/down ratings and your manual edits shape future captions. |
| **Image generation** | Picks the right Traybakes product photos and generates a new marketing image from them with Google Gemini. |
| **Image tweaks** | Ask for a change to a generated image without starting over. |
| **Canvas editor** | Combine images and text, restyle text, reorder layers, undo/redo, save projects (`.tray`) and export images. |
| **Dashboard** | Shows how the assistant is performing (time, usage, cost estimates) and the latest research findings. |

---

## How it works

When you click generate, your request becomes a shared `AgentState` that passes through these stages:

```
Create Content page (PySide6)
        |  runs on a background thread so the window stays responsive
        v
Planner (LLM)  --  decides which subsystems the request needs
        |
        v
Dispatcher  --  runs the chosen subsystems in a fixed order:
        |
        |   1. knowledge_lookup   checks cached research (reused if recent and relevant)
        |   2. research_agent     LangGraph pipeline (only if fresh research is needed)
        |   3. image_generator    product selection -> prompt -> Gemini image
        |   4. caption_generator  retrieval of liked captions -> 3 captions
        v
Results saved to SQLite (data/campaigns.db)
        |
        v
Review, rate and edit in the app  -->  Export image
```

**The research agent** is a LangGraph pipeline of eight steps, each wrapped so one failure doesn't stop the rest:

`discover -> collect -> metrics -> trends -> patterns -> gaps -> ranking -> report`

**Learning loop:** when you rate or edit captions, the app stores your feedback in SQLite. On the next request it retrieves similar past liked campaigns using TF-IDF cosine similarity (with recency weighting and suppression of disliked ones) and passes them to the caption model as examples. Words you repeatedly edit out are collected as "phrases to avoid".

---

## Tech stack

| Purpose | Technology |
|---|---|
| Language | Python |
| Desktop interface | PySide6 (Qt) |
| Research pipeline | LangGraph |
| Text AI (planner, captions, research, image prompts) | Groq, using `openai/gpt-oss-120b` and `openai/gpt-oss-20b` |
| Web research | Tavily |
| Image generation | Google Gemini (`gemini-3.1-flash-image`) |
| Feedback retrieval | scikit-learn TF-IDF |
| Storage | SQLite |
| Packaging | PyInstaller |

---

## Quick start

**.I just want to use the app (Windows)**

1. Get the packaged `Traybakes` folder from the releases page (located within the dist.zip).
2. [Get your three API keys](#get-your-api-keys-step-by-step).
3. Create a `.env` file **in the same folder as `Traybakes.exe`** ([instructions](#where-to-put-your-keys)).
4. Double-click `dist/Traybakes/Traybakes.exe`.

## Get your API keys (step by step)

The app needs **three keys**. Each is a long string of letters and numbers that identifies your account to that service. Treat them like passwords.

| Service | What it powers | Cost |
|---|---|---|
| **Groq** | Planning, captions, research analysis, image prompts | Free tier available (rate limited) |
| **Tavily** | Web search for competitor research | Free tier of 1,000 credits per month, no card needed |
| **Google Gemini** | Image generation | **Paid.** The image model needs billing enabled |

> Websites change their layouts over time. If a button has moved, look for the nearest equivalent ("API keys", "Get API key").

### 1. Groq key (`GROQ_API_KEY`)

1. Go to **https://console.groq.com** and sign up with an email address or a Google account.
2. Once signed in, open **https://console.groq.com/keys** (or click **API Keys** in the menu).
3. Click **Create API Key**.
4. Give it a name such as `traybakes-assistant` and click **Submit**.
5. **Copy the key immediately.** It starts with `gsk_` and Groq only shows it once. If you lose it, delete it and create a new one.
6. Paste it somewhere safe for now (you will put it in `.env` shortly).

Free-tier usage is capped. Current limits are listed at https://console.groq.com/docs/rate-limits. If you hit them, wait a little or upgrade your Groq plan.

### 2. Tavily key (`TAVILY_API_KEY`)

1. Go to **https://app.tavily.com** and sign up (email or GitHub). No credit card is needed for the free plan.
2. After signing in, your default API key is shown on the dashboard home page.
3. Click the copy button. The key starts with `tvly-`.
4. Paste it somewhere safe.

The free plan includes 1,000 credits per month. A search request costs at least 1 credit (more for advanced searches), and a single research run makes several searches, so heavy use can use up the allowance. Credits reset on the first day of each month. Tavily has said it offers free access for students; contact `support@tavily.com` for eligibility.

### 3. Google Gemini key (`GEMINI_API_KEY`)

1. Go to **https://aistudio.google.com/apikey** and sign in with a Google account.
2. Accept the terms if prompted.
3. Click **Create API key**, then choose **Create API key in new project** (or select an existing project).
4. Copy the key. Google keys start with `AIza`.
5. **Enable billing on that project.** The image-generation model used by this app is not available on the free tier. In Google AI Studio, open your project's billing settings and link a billing account.
6. **Create the key (or re-create it) after billing is active**, then use that key. Some users have reported that a key made before billing was enabled kept being treated as free tier.
7. Set a budget alert in Google Cloud so costs can't surprise you.

The app's built-in cost tracker assumes roughly **$0.03 per generated image**. Check Google's current pricing page, as prices and model names change.

### Keep your keys safe

- Never post a key in a chat, email, screenshot or GitHub repository.
- Never share a `.env` file that contains real keys.
- If a key is ever exposed, delete it in that service's dashboard and create a new one.
- Use a separate set of keys for each person or deployment so one can be revoked without affecting the others.

---

## Where to put your keys

The app reads its keys from a file called **`.env`** (the name starts with a dot and has nothing before it).

It must contain exactly these three lines, with your real keys in place of the placeholders and **no spaces and no quote marks**:

```
GROQ_API_KEY=YOUR_GROQ_KEY
TAVILY_API_KEY=YOUR_TAVILY_KEY
GEMINI_API_KEY=YOUR_GEMINI_KEY
```

### Where the file goes

| How you run the app | Put `.env` here |
|---|---|
| Packaged app (`Traybakes.exe`) | In the **same folder as `Traybakes.exe`** |

```
dist/Traybakes/
├── Traybakes.exe
├── .env              <-- here
└── _internal/
```

### Creating the file on Windows

Notepad likes to secretly rename files to `.env.txt`, which the app will not find. The safest method:

1. Open the folder, then click **View > Show > File name extensions** so extensions are visible.
2. Right-click in the folder, choose **New > Text Document**, and name it `.env` (delete the `.txt` part). Click **Yes** when Windows warns about changing the extension.
3. Right-click the file, choose **Open with > Notepad**, paste the three lines above with your keys, and save.

Alternatively, in Notepad choose **File > Save As**, set **Save as type** to **All files**, and type `.env` as the file name.

### Checking it worked

Launch the app and generate something small. If a key is missing or wrong, see [Troubleshooting](#troubleshooting).

---


## Using the app

The sidebar has three pages.

### Create Content

1. **Describe your goal** in plain English, for example: *"Promote our vegan flapjack to independent cafés ahead of winter."*
2. Choose a **Content type** (Instagram Post, Facebook Post, Poster or Banner) and a **Tone** (Professional, Minimal or Warm). Both are optional.
3. Choose one or more **products** using the product picker.
4. Optionally add a **style reference** image (Recommended for specifying a specific background image).
5. Click generate. Progress runs in the background, so the window stays usable.
6. Review the **three caption options** and the **generated image**. Select the caption you prefer.
7. Rate captions with thumbs up or down. Edit a caption if you want to change its wording. The app learns from both.
8. Use the tweak option to ask for a change to the image without regenerating everything.

### Editor

A canvas for finishing touches:

- Insert images and text, move, resize and rotate them
- Change font, size, colour and style
- Reorder layers (forward, backward, front, back)
- Undo and redo
- **Save** your work as a `.tray` project and **Open** it again later
- **Export** the canvas as an image

### Dashboard

Shows how the assistant has been performing (request counts, timings, estimated cost) and the latest research findings: patterns, gaps and opportunities.

> Tip for new users: be specific. A goal that names the product, the audience and the situation gives noticeably better results than a vague one.

---

## Adding or changing products and brand style

### Products and photos

Product photos live in `img_gen/products/`. There is **one folder per product**, and the folder name is the product's key:

```
img_gen/products/
├── vegan_flapjack/
│   ├── tray.jpg
│   ├── sharing_slice.jpg
│   ├── stacked_sharing.jpg
│   ├── single_slice.jpg
│   └── single_box.jpg
├── rocky_road/
└── ...
```

The five file names are the five **presentations** the app understands:

| File name | Meaning |
|---|---|
| `tray` | Large catering tray for sharing |
| `sharing_slice` | A wrapped sharing slice |
| `stacked_sharing` | Several wrapped sharing slices stacked |
| `single_slice` | One individually wrapped slice |
| `single_box` | A box of individually wrapped slices |

To add a product:

1. Create a new folder in `img_gen/products/` with a lowercase name using underscores.
2. Add photos named as above (`.jpg` or `.JPG`).
3. Add a one-line description to the `PRODUCTS` dictionary in `img_gen/data.py`, using exactly the same key as the folder name.
4. Restart the app. The product picker reads the folder list automatically.

### Brand voice and photography style

`img_gen/data.py` holds the brand description and photography style text that is sent to the image model (`BRAND_IDENTITY`, `PHOTOGRAPHY_STYLE`). Edit these to change how generated images look.

Caption wording rules (tone guidance, openers, banned phrases such as "indulge in") are in `caption_generation/caption_generation.py`.

### Models

All model names are set at the top of their files, for example `img_gen/config.py` (`IMAGE_GEN_MODEL`) and `caption_generation/caption_generation.py` (`CAPTION_MODEL`). If a provider renames or retires a model, change the name there.

---

## Build the Windows executable

These steps turn the project into a folder you can give to non-technical users. Run them from the project root with your virtual environment active.

### 1. Install PyInstaller

```bash
pip install pyinstaller
```

### 2. Build

```bash
pyinstaller --noconfirm --windowed --name Traybakes --icon traybakes-logo.ico ^
  --add-data "img_gen/products;img_gen/products" ^
  --add-data "data;data" ^
  --add-data "research_agent/clean_output.json;research_agent" ^
  main.py
```

- The `^` continues the command on the next line in Windows Command Prompt. In PowerShell use a backtick `` ` ``, and on macOS/Linux use `\` and replace `;` inside `--add-data` with `:`.
- Do **not** add `--onefile`. The one-folder build keeps the database and settings in a normal folder. A one-file build unpacks itself to a temporary folder each launch, so new feedback saved to `data/campaigns.db` would be lost.
- If the app fails to start with a `ModuleNotFoundError`, add `--hidden-import <module name>` for the missing module and rebuild.
- This command has been written from reading the code. **Test the built app on a clean machine** before handing it to anyone.

### 3. Add the keys

The finished app is in `dist/Traybakes/`. Create the `.env` file **next to `Traybakes.exe`** as described [above](#where-to-put-your-keys). Do not bundle your real `.env` into the build, or anyone with the app can extract your keys.

### 4. Share it

Zip the whole `dist/Traybakes/` folder and share that. The `.exe` does not work on its own: it needs the files next to it. The `build/` folder is not needed and can be deleted.

---

## Project structure

```
.
├── main.py                       # Entry point (starts the PySide6 app)
├── knowledge_lookup.py           # Checks cached research for reuse
├── requirements.txt              # Python dependencies
├── .env.example                  # Template for your API keys
├── traybakes-logo.ico            # App icon
│
├── app/                          # Desktop interface
│   ├── main_window.py            # Window shell: sidebar + pages
│   ├── backend.py                # Connects the UI to the orchestrator
│   ├── styles.py                 # Colours and stylesheet
│   ├── pages/                    # Dashboard, Create Content, Editor
│   ├── editor/                   # Canvas, items, undo/redo commands
│   ├── widgets/                  # Caption cards, product picker, sidebar...
│   └── workers/                  # Background threads (generation, tweaks)
│
├── orchestrator/                 # The "brain"
│   ├── orchestrator.py           # Runs a request end to end, tracks cost/time
│   ├── planner.py                # LLM decides which subsystems to run
│   ├── dispatcher.py             # Runs subsystems in order
│   ├── state.py                  # Shared AgentState
│   └── campaign_store.py         # SQLite storage and TF-IDF retrieval
│
├── research_agent/               # LangGraph competitor research pipeline
│   ├── research_agent.py         # Graph definition
│   ├── discover.py collect.py metrics.py trends.py
│   ├── patterns.py gaps.py ranking.py report.py
│   ├── llm.py                    # Groq clients (plain and JSON mode)
│   ├── json_utils.py             # JSON extraction/repair helpers
│   ├── json_normaliser.py
│   └── test_*.py                 # Unit tests
│
├── caption_generation/           # Caption writing and refinement
├── img_gen/                      # Image generation
│   ├── generator.py              # Calls Gemini, handles retries
│   ├── selector.py               # Chooses product photos
│   ├── prompt_builder.py         # Builds the image prompt
│   ├── data.py                   # Product list, brand and photo style text
│   ├── config.py                 # Clients, paths, model names
│   └── products/                 # Product photography (one folder each)
│
└── data/
    └── campaigns.db              # SQLite database (campaigns, ratings, edits)
```

---

## Files the app creates

| File or folder | What it is |
|---|---|
| `data/campaigns.db` | Campaign history, caption ratings and your caption edits. This is the app's memory. Back it up. |
| `research_agent/clean_output.json` | The most recent research result, reused for 14 days if the new goal is similar. |
| `dashboard_metrics.json` | Dashboard statistics. Created in the folder the app is launched from. |
| `img_gen/outputs/` | Every generated image (large PNGs). This folder grows quickly. |
| `*.tray` | Editor projects you choose to save. |

---

## Running the tests

With your virtual environment active, from the project root:

```bash
pip install pytest
pytest research_agent -v
```

There are 27 unit tests covering the JSON extraction and normalisation helpers used by the research agent.

---

## Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| The app opens, but generating shows a backend or import error | A key is missing. The search and AI clients are created when the app starts, so a missing key can stop the backend loading. Check that `.env` exists in the right folder (see [Where to put your keys](#where-to-put-your-keys)) and that all three lines are present. |
| `.env` seems to be ignored | Check the file isn't really named `.env.txt` (turn on file extensions in Windows). Make sure there are no spaces around `=` and no quote marks. Restart the app after editing it. |
| `401` or "invalid API key" | The key was copied incompletely or has been deleted. Create a new one and replace it. |
| `429` or "rate limit" from Groq | You hit the free-tier limit. Wait a minute and retry, or upgrade your Groq plan. |
| Tavily `432` or a quota message | You used up the month's 1,000 credits. They reset on the 1st, or upgrade your plan. |
| Gemini says quota exceeded with a limit of `0` | The image model needs a billed project. Enable billing, create a new key afterwards, and use the new key. Allow a little time for billing to take effect. |
| Images fail but captions work | Almost always the Gemini key or billing. Check the key and the model name in `img_gen/config.py`. |
| Product not shown in the picker | Its folder is missing from `img_gen/products/` or contains no photos. Restart after adding it. |
| Packaged app can't find products | The `--add-data` for `img_gen/products` was missing when building. Rebuild with the full command above. |
| Packaged app forgets feedback | You built with `--onefile`. Rebuild without it. |
| `ModuleNotFoundError` when running from source | The virtual environment isn't active or dependencies aren't installed. Re-run the install steps. |
| Slow first run | The first request may do fresh research and generate an image. Later requests reuse cached research when the goal is similar. |

If something else goes wrong, note the exact error message shown in the app or terminal. Running from source (`python main.py`) prints more detail than the packaged app.

---

## Known issues

- **Cost estimates are approximate:** the pricing tables in `orchestrator/orchestrator.py` are hard-coded and some model names in them don't match the models currently used. Treat dashboard costs as a guide. This is due to the deprecation of a previously used model which was changed close to the deadline which affects caption regeneration.
- **No direct posting:** the app exports images and text for you to post yourself. It does not publish to social media after human review.
- **Single research cache:** only the latest research result is kept, so alternating between two different topics repeats research.
- **Image Generation Accuracy:** The Gemini image model struggles to preserve the fine-text of the product packaging. Maybe consider alternative/newer image models.

---

## Future work

Ideas for taking the project further, roughly from quickest wins to larger projects.

### Reliability and polish
- **Fix the known issues above**, starting with the package marker, product naming and a single place that loads configuration. Consider using alternative image models that better preserve fine text.
- **In-app settings screen** where staff paste their API keys, so nobody has to create a `.env` file by hand. Store them with the operating system's secure credential store rather than a plain text file.
- **Friendly error messages** when a key is missing, a quota is hit or the network is down, with a clear "what to do next".
- **Store user data in the user's app-data folder** (database, outputs, metrics) instead of beside the program, so upgrades never overwrite it.
- **Automatic clean-up** or an in-app "clear old images" button for `img_gen/outputs/`.
- **More features to the Editor Page** Polish the user interface and add more useful features.

### Performance and cost
- **Run independent steps in parallel.** Image generation and caption writing do not depend on each other and could run at the same time, shortening waiting time.
- **Better research caching:** keep several cached research results in the database, match them by topic, and allow a manual "refresh research" button. Older results disregarded.
- **Usage limits and budget warnings** inside the app, so a month's spend on Gemini and Tavily is visible and capped.
- **Live pricing and model configuration** read from a settings file rather than hard-coded and displayed to the live dashboard page.

### Features
- **Publish directly** to Instagram and Facebook, with scheduling and a review step.
- **Learn from real results:** connect post engagement data so that feedback is based on what actually performed, not only on ratings from staff.
- **More content formats:** carousels, short video storyboards, email newsletters and product-sheet copy.
- **Brand management:** make the brand configuration (`brand_config.json` template) drive prompts, so a second client can be set up without editing code, with logos, colours and fonts applied automatically. Ensure the prompts that are inside the codebase fit the Traybakes branding.
- **Safeguards on generated images:** automatic checks that the right product, packaging and label appear, and flagging of outputs that drift from brand style.
- **Seasonal and calendar awareness:** suggest campaigns around holidays, trade shows and the wholesale buying calendar.
- **Alternative providers:** a thin layer so Groq, Gemini or Tavily can be swapped for other services, or for local models, without rewriting the agents.




