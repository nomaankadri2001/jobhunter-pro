# JobHunter Pro — Setup Guide

## Option A: Run locally (no internet needed)
1. Double-click `START_local.bat`
2. App opens at http://localhost:7432
3. Enter your Groq key in the setup screen

---

## Option B: Deploy to Railway (access from ANYWHERE, always online)

### Step 1 — Push to GitHub
1. Create a free account at github.com
2. Click "New repository" → name it "jobhunter-pro" → Create
3. Upload ALL files in this folder to the repo
   (drag & drop them onto the GitHub page)

### Step 2 — Deploy on Railway
1. Go to railway.app → Sign up with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your "jobhunter-pro" repo
4. Railway auto-detects Python and deploys it

### Step 3 — Add your Groq API key to Railway
1. In Railway dashboard, click your project
2. Go to "Variables" tab
3. Add variable:  Name: GROQ_API_KEY  Value: your gsk_... key
4. Railway restarts automatically

### Step 4 — Get your public URL
1. Go to "Settings" tab in Railway
2. Click "Generate Domain"
3. You get a URL like: https://jobhunter-pro-xxx.up.railway.app
4. Bookmark it — access from any device, anywhere!

---

## Features
- Resume Tailor — AI rewrites resume to match any JD
- Drag & drop resume upload (PDF, DOCX, TXT)
- ATS Keywords extractor
- Gap analysis
- Recruiter outreach emails
- Cover letter generator (manual + from full resume)
- Application tracker

## Notes
- Free Railway plan: 500 hours/month (enough for daily use)
- Groq API: free, 14,400 requests/day, works in India
- Your application data is stored in browser localStorage
