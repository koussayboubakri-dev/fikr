/**
 * fikr-xp.js — Shared XP & Level System for Fikr Platform
 * Import this in every lesson file and in index.html dashboard
 *
 * Usage in lessons:
 *   import { FikrXP } from './fikr-xp.js';
 *   const xpSystem = await FikrXP.init(user, db);
 *   await xpSystem.add(20, 'Completed quiz');
 *
 * Usage in dashboard:
 *   import { FikrXP } from './fikr-xp.js';
 *   await FikrXP.renderDashboard(user, db, containerElement);
 */

// ── LEVEL DEFINITIONS ──
export const LEVELS = [
  { level: 1, min: 0,    max: 200,  ar: 'مبتدئ',   en: 'Beginner',      emoji: '🌱', color: '#16a34a' },
  { level: 2, min: 200,  max: 500,  ar: 'متعلّم',   en: 'Learner',       emoji: '📚', color: '#2563eb' },
  { level: 3, min: 500,  max: 1000, ar: 'مبرمج',   en: 'Programmer',    emoji: '💻', color: '#7c3aed' },
  { level: 4, min: 1000, max: 2000, ar: 'محترف',   en: 'Professional',  emoji: '🚀', color: '#c8922a' },
  { level: 5, min: 2000, max: 9999, ar: 'خبير',    en: 'Expert',        emoji: '⭐', color: '#dc2626' },
];

export function getLevel(xp) {
  return LEVELS.find(l => xp >= l.min && xp < l.max) || LEVELS[LEVELS.length - 1];
}

export function getProgress(xp) {
  const lvl = getLevel(xp);
  const range = lvl.max - lvl.min;
  const earned = xp - lvl.min;
  return Math.min(Math.round((earned / range) * 100), 100);
}

// ── STREAK LOGIC ──
export function calcStreak(lastLoginDate, currentStreak) {
  if (!lastLoginDate) return { streak: 1, isNew: true };
  const last = new Date(lastLoginDate);
  const today = new Date();
  const diffDays = Math.floor((today - last) / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return { streak: currentStreak, isNew: false };       // same day
  if (diffDays === 1) return { streak: currentStreak + 1, isNew: true };    // consecutive
  return { streak: 1, isNew: true };                                         // streak broken
}

// ── FIREBASE CONFIG (shared) ──
const FIREBASE_CFG = {
  apiKey: "AIzaSyBeD4ng-pNWSLgkrNmK1Re8FYnmCNCMBU8",
  authDomain: "fikr-app-fbdf7.firebaseapp.com",
  projectId: "fikr-app-fbdf7",
  storageBucket: "fikr-app-fbdf7.firebasestorage.app",
  messagingSenderId: "378212535527",
  appId: "1:378212535527:web:99331970433b4428dd2642"
};

// ── MAIN XP CLASS ──
export class FikrXP {
  constructor(user, db, docRef) {
    this.user   = user;
    this.db     = db;
    this.ref    = docRef;
    this.xp     = 0;
    this.streak = 0;
    this.level  = LEVELS[0];
    this._pill  = null;
    this._queue = [];      // pending XP writes (batched)
    this._timer = null;
  }

  /** Initialize: load XP from Firestore, update streak, return FikrXP instance */
  static async init(user, db) {
    const { doc, getDoc, updateDoc, serverTimestamp } = await import(
      "https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js"
    );
    const ref  = doc(db, 'users', user.uid);
    const snap = await getDoc(ref);
    const data = snap.data() || {};

    const instance = new FikrXP(user, db, ref);
    instance.xp = data.xp || 0;

    // Update streak
    const { streak, isNew } = calcStreak(data.lastLogin, data.streak || 0);
    instance.streak = streak;

    if (isNew) {
      await updateDoc(ref, {
        streak,
        lastLogin: new Date().toISOString(),
      });
    }

    instance.level = getLevel(instance.xp);
    return instance;
  }

  /** Bind the in-lesson XP pill element so it auto-updates */
  bindPill(el) {
    this._pill = el;
    this._render();
  }

  /** Add XP for completing an action — writes to Firestore immediately */
  async add(amount, reason = '') {
    this.xp += amount;
    this.level = getLevel(this.xp);
    this._render();
    this._scheduleWrite();
    console.log(`[FikrXP] +${amount} XP (${reason}) → total: ${this.xp}`);
  }

  /** Force-save to Firestore right now */
  async save() {
    clearTimeout(this._timer);
    await this._write();
  }

  /** Internal: debounced Firestore write (300ms) */
  _scheduleWrite() {
    clearTimeout(this._timer);
    this._timer = setTimeout(() => this._write(), 300);
  }

  async _write() {
    try {
      const { updateDoc } = await import(
        "https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js"
      );
      await updateDoc(this.ref, { xp: this.xp });
    } catch (e) {
      console.warn('[FikrXP] Write failed:', e.message);
    }
  }

  /** Update the pill display */
  _render() {
    if (!this._pill) return;
    const lvl = getLevel(this.xp);
    this._pill.textContent = lvl.emoji + ' ' + this.xp + ' XP';
    this._pill.style.transform = 'scale(1.35)';
    setTimeout(() => { if(this._pill) this._pill.style.transform = ''; }, 350);
  }

  /** Render a full XP widget into a container DOM element (for dashboard) */
  static renderWidget(containerEl, xp, streak) {
    const lvl      = getLevel(xp);
    const progress = getProgress(xp);
    const nextLvl  = LEVELS[lvl.level] || lvl;   // next level object
    const xpToNext = nextLvl.min - xp;

    containerEl.innerHTML = `
      <div class="xp-widget" style="
        background:var(--white);
        border:1.5px solid var(--border);
        border-radius:20px;
        padding:24px 28px;
        box-shadow:0 4px 20px rgba(0,0,0,0.07);
        display:flex;
        flex-direction:column;
        gap:16px;
      ">
        <!-- Top row: level badge + streak -->
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
          <div style="display:flex;align-items:center;gap:12px">
            <div style="
              width:52px;height:52px;border-radius:50%;
              background:${lvl.color}18;
              border:2.5px solid ${lvl.color}40;
              display:flex;align-items:center;justify-content:center;
              font-size:1.5rem;
            ">${lvl.emoji}</div>
            <div>
              <div style="font-family:var(--font-ui);font-size:0.75rem;color:var(--text-soft);font-weight:600;margin-bottom:2px">المستوى ${lvl.level} — ${lvl.en}</div>
              <div style="font-family:var(--font-ui);font-size:1.1rem;font-weight:900;color:var(--text)">${lvl.ar}</div>
            </div>
          </div>
          <!-- Streak -->
          <div style="
            display:flex;align-items:center;gap:8px;
            background:#fff7ed;border:1.5px solid #fed7aa;
            border-radius:99px;padding:8px 16px;
          ">
            <span style="font-size:1.2rem">🔥</span>
            <div>
              <div style="font-family:var(--font-ui);font-size:1rem;font-weight:900;color:#ea580c;line-height:1">${streak}</div>
              <div style="font-family:var(--font-ui);font-size:0.68rem;color:#9a3412;font-weight:600">يوم متواصل</div>
            </div>
          </div>
        </div>

        <!-- XP total -->
        <div style="display:flex;align-items:baseline;gap:6px">
          <span style="font-family:var(--font-ui);font-size:2rem;font-weight:900;color:${lvl.color}">${xp}</span>
          <span style="font-family:var(--font-ui);font-size:0.88rem;color:var(--text-soft);font-weight:600">XP</span>
          ${lvl.level < 5 ? `<span style="font-family:var(--font-ui);font-size:0.78rem;color:var(--text-soft);margin-right:auto">← ${xpToNext} XP للمستوى التالي</span>` : '<span style="font-family:var(--font-ui);font-size:0.78rem;color:#c8922a;margin-right:auto">🏆 المستوى الأعلى!</span>'}
        </div>

        <!-- Progress bar -->
        <div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px">
            <span style="font-family:var(--font-ui);font-size:0.72rem;color:var(--text-soft);font-weight:600">المستوى ${lvl.level}</span>
            <span style="font-family:var(--font-ui);font-size:0.72rem;color:var(--text-soft);font-weight:600">${progress}%</span>
            <span style="font-family:var(--font-ui);font-size:0.72rem;color:var(--text-soft);font-weight:600">المستوى ${Math.min(lvl.level + 1, 5)}</span>
          </div>
          <div style="height:10px;background:#f1f5f9;border-radius:99px;overflow:hidden">
            <div style="
              height:100%;
              width:${progress}%;
              background:linear-gradient(90deg,${lvl.color},${lvl.color}cc);
              border-radius:99px;
              transition:width 1s cubic-bezier(.4,0,.2,1);
            "></div>
          </div>
        </div>

        <!-- Level milestones -->
        <div style="display:flex;gap:4px">
          ${LEVELS.map(l => `
            <div title="Level ${l.level}: ${l.ar}" style="
              flex:1;height:4px;border-radius:99px;
              background:${xp >= l.min ? l.color : '#e2e8f0'};
              transition:background .4s;
            "></div>
          `).join('')}
        </div>
      </div>
    `;
  }
}

// ── STANDALONE INIT (for lessons that can't use top-level await) ──
export async function initFikrXP(pillEl) {
  try {
    const { initializeApp, getApps } = await import(
      "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js"
    );
    const { getAuth, onAuthStateChanged } = await import(
      "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js"
    );
    const { getFirestore } = await import(
      "https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js"
    );
    const app  = getApps().length ? getApps()[0] : initializeApp(FIREBASE_CFG);
    const auth = getAuth(app);
    const db   = getFirestore(app);

    const user = await new Promise(r => {
      const unsub = onAuthStateChanged(auth, u => { unsub(); r(u); });
    });

    if (!user) {
      window.location.href = 'index.html';
      return null;
    }

    const xpSystem = await FikrXP.init(user, db);
    if (pillEl) xpSystem.bindPill(pillEl);

    // Expose globally so inline onclick handlers can call window.fikrXP.add()
    window.fikrXP = xpSystem;
    return xpSystem;

  } catch (e) {
    console.error('[FikrXP] Init failed:', e);
    return null;
  }
}
