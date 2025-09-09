---
title: Care Count Inventory
emoji: 📦
sdk: streamlit
python_version: 3.11
app_file: streamlit_app.py
pinned: false
license: mit
sdk_version: 1.48.1
---
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/tolani007/care-count-starter)

## 🔑 Secrets Setup
- Copy `.env.example` to `.env`
- Fill in:
  - `SUPABASE_URL` (from Supabase project → Settings → API)
  - `SUPABASE_KEY` (Anon key, not service role for safety)
  - `HF_TOKEN` (create in Hugging Face → Settings → Access Tokens)

⚠️ Never commit `.env` — it’s in `.gitignore`.
Use Hugging Face Space or Streamlit Cloud settings to add these secrets when deploying.

Demo app (Vercel redirect):
👉 https://care-count-app-demo.vercel.app

Code repo:
👉 https://github.com/tolani007/care-count-starter

Issues board (for blockers):
👉 https://github.com/tolani007/care-count-starter/issues

## Live Demo
- Vercel: (https://care-count-app-demo.vercel.app/)  (redirects to the live app)
- Status: MVP demo for a small group. If access is blocked, DM me your HF username and I’ll add you.

## Cloud Collaboration (no local setup)
- Click **Code → Open with Codespaces → New codespace** to edit in-browser.
- Make a branch, open a PR. On merge to `main`, Vercel redeploys automatically (redirect stays the same).
- If you change the app host URL, update `vercel.json` accordingly.

Care Count — BLIP-assisted inventory logging with Supabase (Streamlit).

# Care Count App

## What this app is supposed to do
Care Count is meant to be a simple but powerful tool for food banks.  
The vision:  
- Volunteers take a picture of donated items.  
- The app figures out the item name (using vision or text recognition).  
- It logs that item into a Supabase database.  
- From there, we can track inventory, volunteer hours, and monthly reports.  

Basically, it’s supposed to be a **BLIP-assisted inventory logger with Streamlit + Supabase**.  

---

## What it does so far
- I have a **Streamlit frontend** running.  
- The UI has a basic volunteer interface with a placeholder for scanning barcodes / uploading images.  
- The Supabase connection boilerplate is in place (so I can save data once it’s ready).  
- README + setup files are working with Python 3.11 and Streamlit SDK pinned.  

So right now it’s more like a **starter shell**: UI + database hooks, but not yet the full intelligence part.  

---

## Where I am stuck
- The big block is getting **the model connection working**.  
- I keep hitting errors like: *“model not found”* or *“fallback mode missing.”*  
- Hugging Face Spaces didn’t let me just enable internet access (that option isn’t visible).  
- My goal is: take an image → get food item name (either OCR text or vision model guess).  

So I’m stuck at the **core loop**:  
Image → Item name → Save to Supabase.  

---

## Paths I’ve already tried
- **BLIP model** → integrated but fails with model not found.  
- **Tried Hugging Face image-to-text** → works for captions but not consistent for item names.  
- **OCR approach** → only useful if the packaging has readable text (not for loose produce).  
- **Looked for “Hardware & resources → internet access” in Hugging Face Spaces** → doesn’t exist.  
- **Tried patching `streamlit_app.py` with fallback modes** → still errors.  

Right now the blocker is **reliable model access** inside the app.  

---

## Feynman summary (in plain words)
This project is about making food bank inventory logging automatic.  
- A person uploads a photo.  
- The computer should answer one simple question: **“What food item is this?”**  
- If the app knows the name, it saves it into a database for tracking.  

The tricky part:  
- Sometimes the name is written (like “Kellogg’s Cornflakes”), so OCR works.  
- Sometimes there’s no text (like apples), so we need a vision model.  
- The app needs to switch between both methods.  

Right now the UI and database parts are ready, but the brain (image → item name) is where I’m still stuck.  

---

## Next steps
- Fix model access so the app can call Hugging Face models properly.  
- Build fallback logic: OCR first, then vision model if no text is found.  
- Push working code so volunteers can test with real food items.


## How to collaborate (no local setup needed)

If you want to help me move this project forward, you don’t need to install anything on your laptop.  
The repo is already set up so you can work **directly in the cloud**. Here are the easiest paths:  

### 1. GitHub Codespaces (recommended)
- Click the green **Code** button at the top of this repo.  
- Select **Open with Codespaces → New codespace**.  
- This will open a full VS Code dev environment in your browser.  
- Everything you need (Python, Streamlit, git) is preinstalled.  
- From there you can run:
  ```bash
  streamlit run streamlit_app.py
2. Hugging Face Spaces

This repo is linked to a Hugging Face Space (the live app host).

You can sync changes to Hugging Face by pushing to main.

Hugging Face will automatically rebuild and redeploy the app.

To test your edits:

Make a branch

Open a pull request

Once merged into main, the Hugging Face Space redeploys with your update.

3. Streamlit Cloud (optional)

Another option is to connect this repo to Streamlit Cloud.

Anyone with access can deploy changes instantly to a shared app link.

Future Contributors:
No need to install Python locally unless you want to.

Best path: open a Codespace → edit → push changes → see them live on Hugging Face.

If you add new packages, also update requirements.txt so Hugging Face/Streamlit can rebuild properly.

If you try new model integrations (OCR or vision), please write in the README what you tried so we don’t repeat the same dead ends.
