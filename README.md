# Fikr XP System v2 — Installation Package

## What's in this package

| File | Purpose |
|------|---------|
| `fikr-xp.js` | Shared ES module — import in any future lesson |
| `patch_fikr_xp.py` | **Run this** to patch your existing files |

## How to install

1. Drop `fikr-xp.js` and `patch_fikr_xp.py` into your Fikr project folder  
   (same directory as `index.html`, `lesson1.html`, etc.)

2. Run:
   ```bash
   python3 patch_fikr_xp.py
   ```

3. The script will:
   - Back up all originals to `fikr_backup_TIMESTAMP/`
   - Patch all 12 lesson files + `index.html`
   - Print what it changed

## What gets changed

### Every lesson file (lesson1.html through lesson-k4.html)
- ✅ Loads **real XP** from Firestore on page start (pill shows correct number immediately)
- ✅ `addXP(n)` now writes to Firestore within 300ms (no more lost XP on page close)
- ✅ XP pill shows level emoji: 🌱 0–200, 📚 200–500, 💻 500–1000, 🚀 1000–2000, ⭐ 2000+
- ✅ Streak tracked and updated each login day

### index.html dashboard
- ✅ XP widget appears below the welcome message showing:
  - Level badge (emoji + Arabic name + English name)
  - 🔥 Streak counter (consecutive days)
  - XP total with color matching current level
  - Progress bar toward next level
  - 5 colored milestone dots across all levels

## Level system

| Level | XP Range | Arabic | Emoji | Color |
|-------|----------|--------|-------|-------|
| 1 | 0–200 | مبتدئ | 🌱 | Green |
| 2 | 200–500 | متعلّم | 📚 | Blue |
| 3 | 500–1000 | مبرمج | 💻 | Purple |
| 4 | 1000–2000 | محترف | 🚀 | Gold |
| 5 | 2000+ | خبير | ⭐ | Red |
