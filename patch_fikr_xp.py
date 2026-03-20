#!/usr/bin/env python3
"""
Fikr XP System v2 — Universal Patcher
======================================
Drop this file into your Fikr project directory
(same folder as index.html, lesson1.html, etc.)
then run:

    python3 patch_fikr_xp.py

It will:
  • Back up all originals to fikr_backup_TIMESTAMP/
  • Add XP level system CSS to every lesson + index.html
  • Replace local addXP() with global window.addXP() that writes to Firestore
  • Load real XP from Firestore on lesson start (shows correct number from first second)
  • Add streak tracking (consecutive days)
  • Add XP widget to dashboard (level badge + progress bar + streak flame)
"""
import re, os, shutil
from datetime import datetime

BACKUP_DIR = f'fikr_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

# ─────────────────────────────────────────────────────────────────
# LEVELS CSS  — injected into every HTML file
# ─────────────────────────────────────────────────────────────────
LEVELS_CSS = """
    /* ── XP WIDGET (fikr-xp v2) ── */
    .xp-widget-inner{background:var(--white);border:1.5px solid var(--border);border-radius:20px;padding:22px 26px;box-shadow:0 4px 20px rgba(0,0,0,0.07);display:flex;flex-direction:column;gap:14px;margin-bottom:24px}
    .xp-top-row{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
    .xp-level-badge{display:flex;align-items:center;gap:12px}
    .xp-level-icon{width:50px;height:50px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.4rem;border:2.5px solid;flex-shrink:0}
    .xp-level-info-sub{font-family:var(--font-ui);font-size:0.72rem;color:var(--text-soft);font-weight:600;margin-bottom:2px}
    .xp-level-info-name{font-family:var(--font-ui);font-size:1.05rem;font-weight:900;color:var(--text)}
    .xp-streak{display:flex;align-items:center;gap:8px;background:#fff7ed;border:1.5px solid #fed7aa;border-radius:99px;padding:8px 16px}
    .xp-streak-num{font-family:var(--font-ui);font-size:1rem;font-weight:900;color:#ea580c;line-height:1}
    .xp-streak-label{font-family:var(--font-ui);font-size:0.68rem;color:#9a3412;font-weight:600}
    .xp-total-row{display:flex;align-items:baseline;gap:6px}
    .xp-total-num{font-family:var(--font-ui);font-size:2rem;font-weight:900}
    .xp-total-unit{font-family:var(--font-ui);font-size:0.88rem;color:var(--text-soft);font-weight:600}
    .xp-to-next{font-family:var(--font-ui);font-size:0.78rem;color:var(--text-soft);margin-right:auto}
    .xp-bar-labels{display:flex;justify-content:space-between;margin-bottom:5px}
    .xp-bar-label{font-family:var(--font-ui);font-size:0.7rem;color:var(--text-soft);font-weight:600}
    .xp-bar-track{height:10px;background:#f1f5f9;border-radius:99px;overflow:hidden}
    .xp-bar-fill{height:100%;border-radius:99px;transition:width 1.2s cubic-bezier(.4,0,.2,1)}
    .xp-milestones{display:flex;gap:4px}
    .xp-milestone{flex:1;height:4px;border-radius:99px;transition:background .5s}
"""

# ─────────────────────────────────────────────────────────────────
# UNIFIED LESSON INIT — replaces the old auth guard IIFE
# ─────────────────────────────────────────────────────────────────
UNIFIED_BASE = """
// ── FIKR XP SYSTEM v2 ──
const LEVELS_L=[
  {level:1,min:0,max:200,emoji:'\U0001f331'},
  {level:2,min:200,max:500,emoji:'\U0001f4da'},
  {level:3,min:500,max:1000,emoji:'\U0001f4bb'},
  {level:4,min:1000,max:2000,emoji:'\U0001f680'},
  {level:5,min:2000,max:9999,emoji:'\u2b50'},
];
function getLvl(xp){return LEVELS_L.find(l=>xp>=l.min&&xp<l.max)||LEVELS_L[LEVELS_L.length-1];}
function calcStreakL(lastLogin,cur){
  if(!lastLogin) return {streak:1,changed:true};
  const diff=Math.floor((new Date()-new Date(lastLogin))/86400000);
  if(diff===0) return {streak:cur||1,changed:false};
  if(diff===1) return {streak:(cur||0)+1,changed:true};
  return {streak:1,changed:true};
}
let _xp=0,_uid=null,_db=null;
function updateXPPill(){
  const pill=document.getElementById('xp');
  if(!pill) return;
  const lvl=getLvl(_xp);
  pill.textContent=lvl.emoji+' '+_xp+' XP';
  pill.style.transform='scale(1.4)';
  setTimeout(()=>pill.style.transform='',350);
}
window.addXP=async function(amount,reason){
  _xp+=amount;
  updateXPPill();
  if(_uid&&_db){
    try{
      const{doc,updateDoc}=await import("https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js");
      await updateDoc(doc(_db,'users',_uid),{xp:_xp});
    }catch(e){console.warn('[XP] write failed',e.message);}
  }
};
(async()=>{
  try{
    const{initializeApp,getApps}=await import("https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js");
    const{getAuth,onAuthStateChanged}=await import("https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js");
    const{getFirestore,doc,getDoc,updateDoc}=await import("https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js");
    const cfg={apiKey:"AIzaSyBeD4ng-pNWSLgkrNmK1Re8FYnmCNCMBU8",authDomain:"fikr-app-fbdf7.firebaseapp.com",projectId:"fikr-app-fbdf7",storageBucket:"fikr-app-fbdf7.firebasestorage.app",messagingSenderId:"378212535527",appId:"1:378212535527:web:99331970433b4428dd2642"};
    const app=getApps().length?getApps()[0]:initializeApp(cfg);
    const auth=getAuth(app);
    _db=getFirestore(app);
    const user=await new Promise(r=>{const u=onAuthStateChanged(auth,x=>{u();r(x);});});
    if(!user){window.location.href='index.html';return;}
    _uid=user.uid;
    const snap=await getDoc(doc(_db,'users',_uid));
    const data=snap.data()||{};
    _xp=data.xp||0;
    updateXPPill();
    const{streak,changed}=calcStreakL(data.lastLogin,data.streak||0);
    if(changed){updateDoc(doc(_db,'users',_uid),{streak,lastLogin:new Date().toISOString()}).catch(()=>{});}"""

INIT_FREE = UNIFIED_BASE + """
  }catch(e){console.error('[FikrXP] init failed',e);}
})();
"""

INIT_PAID = UNIFIED_BASE + """
    if(data.subscription!=='active'){window.location.href='index.html';return;}
  }catch(e){console.error('[FikrXP] init failed',e);}
})();
"""

# ─────────────────────────────────────────────────────────────────
# DASHBOARD — new loadDashboard for index.html
# ─────────────────────────────────────────────────────────────────
LOAD_DASHBOARD_NEW = """
  // ── LEVEL SYSTEM (dashboard) ──
  const LEVELS_D=[
    {level:1,min:0,max:200,ar:'\u0645\u0628\u062a\u062f\u0626',en:'Beginner',emoji:'\U0001f331',color:'#16a34a'},
    {level:2,min:200,max:500,ar:'\u0645\u062a\u0639\u0644\u0651\u0645',en:'Learner',emoji:'\U0001f4da',color:'#2563eb'},
    {level:3,min:500,max:1000,ar:'\u0645\u0628\u0631\u0645\u062c',en:'Programmer',emoji:'\U0001f4bb',color:'#7c3aed'},
    {level:4,min:1000,max:2000,ar:'\u0645\u062d\u062a\u0631\u0641',en:'Professional',emoji:'\U0001f680',color:'#c8922a'},
    {level:5,min:2000,max:9999,ar:'\u062e\u0628\u064a\u0631',en:'Expert',emoji:'\u2b50',color:'#dc2626'},
  ];
  function getLvlD(xp){return LEVELS_D.find(l=>xp>=l.min&&xp<l.max)||LEVELS_D[LEVELS_D.length-1];}
  function getProgressD(xp){const l=getLvlD(xp);return Math.min(Math.round(((xp-l.min)/(l.max-l.min))*100),100);}
  function calcStreakD(lastLogin,cur){
    if(!lastLogin) return {streak:1,changed:true};
    const diff=Math.floor((new Date()-new Date(lastLogin))/86400000);
    if(diff===0) return {streak:cur||1,changed:false};
    if(diff===1) return {streak:(cur||0)+1,changed:true};
    return {streak:1,changed:true};
  }
  function renderXPWidget(mount,xp,streak){
    const lvl=getLvlD(xp),progress=getProgressD(xp),nextLvl=LEVELS_D[lvl.level]||lvl,xpToNext=nextLvl.min-xp;
    const toNext=lvl.level<5?`<span class="xp-to-next">\\u2190 ${xpToNext} XP \\u0644\\u0644\\u0645\\u0633\\u062a\\u0648\\u0649 \\u0627\\u0644\\u062a\\u0627\\u0644\\u064a (${LEVELS_D[lvl.level].ar} ${LEVELS_D[lvl.level].emoji})</span>`:'<span class="xp-to-next" style="color:#c8922a">\\U0001f3c6 \\u0623\\u0639\\u0644\\u0649 \\u0645\\u0633\\u062a\\u0648\\u0649!</span>';
    const nextLabel=lvl.level<5?LEVELS_D[lvl.level].emoji+' '+LEVELS_D[lvl.level].ar:'\\U0001f3c6';
    mount.innerHTML=`
      <div class="xp-widget-inner">
        <div class="xp-top-row">
          <div class="xp-level-badge">
            <div class="xp-level-icon" style="background:${lvl.color}18;border-color:${lvl.color}55">${lvl.emoji}</div>
            <div><div class="xp-level-info-sub">\\u0627\\u0644\\u0645\\u0633\\u062a\\u0648\\u0649 ${lvl.level} \\u00b7 ${lvl.en}</div><div class="xp-level-info-name">${lvl.ar}</div></div>
          </div>
          <div class="xp-streak"><span style="font-size:1.2rem">\\U0001f525</span><div><div class="xp-streak-num">${streak||1}</div><div class="xp-streak-label">\\u064a\\u0648\\u0645 \\u0645\\u062a\\u0648\\u0627\\u0635\\u0644</div></div></div>
        </div>
        <div class="xp-total-row"><span class="xp-total-num" style="color:${lvl.color}">${xp}</span><span class="xp-total-unit">XP</span>${toNext}</div>
        <div>
          <div class="xp-bar-labels"><span class="xp-bar-label">${lvl.emoji} ${lvl.ar}</span><span class="xp-bar-label">${progress}%</span><span class="xp-bar-label">${nextLabel}</span></div>
          <div class="xp-bar-track"><div class="xp-bar-fill" id="xp-bar-fill" style="width:0%;background:linear-gradient(90deg,${lvl.color},${lvl.color}99)"></div></div>
        </div>
        <div class="xp-milestones">${LEVELS_D.map(l=>`<div class="xp-milestone" style="background:${xp>=l.min?l.color:'#e2e8f0'}" title="${l.ar}"></div>`).join('')}</div>
      </div>`;
    requestAnimationFrame(()=>requestAnimationFrame(()=>{const fill=document.getElementById('xp-bar-fill');if(fill)fill.style.width=progress+'%';}));
  }
  function loadDashboard(user) {
    const name = (user.displayName || user.email).split(' ')[0];
    document.getElementById('dash-username').textContent     = `\\u0645\\u0631\\u062d\\u0628\\u0627\\u060c ${name}`;
    document.getElementById('dash-welcome-name').textContent = `\\u0645\\u0631\\u062d\\u0628\\u0627\\u060c ${name} \\U0001f44b`;
    getDoc(doc(db, 'users', user.uid)).then(snap => {
      const data = snap.data() || {};
      const xp = data.xp || 0;
      const mount = document.getElementById('xp-widget-mount');
      if (mount) {
        const { streak, changed } = calcStreakD(data.lastLogin, data.streak || 0);
        renderXPWidget(mount, xp, streak);
        if (changed) updateDoc(doc(db, 'users', user.uid), { streak, lastLogin: new Date().toISOString() }).catch(() => {});
      }
      const completed = data.lessonsCompleted || [];
      const sub = data.subscription || 'trial';
      if (sub === 'active') {
        [3,4].forEach(n=>{const c=document.getElementById('lcard-'+n);const b=document.getElementById('lbadge-'+n);if(c){c.classList.remove('locked');c.classList.add('free');c.onclick=()=>openLesson(n,c.querySelector('.lesson-title').textContent);}if(b){b.textContent='\\u0645\\u0634\\u062a\\u0631\\u0643';b.className='lesson-badge free-badge';}});
        [6,7,8].forEach(n=>{const c=document.getElementById('lcard-'+n);const b=document.getElementById('lbadge-'+n);if(c){c.classList.remove('locked');c.classList.add('free');c.onclick=()=>openLesson(n,c.querySelector('.lesson-title').textContent);}if(b){b.textContent='\\u0645\\u0634\\u062a\\u0631\\u0643';b.className='lesson-badge free-badge';}});
        [9,10,11,12].forEach(n=>{const c=document.getElementById('lcard-'+n);const b=document.getElementById('lbadge-'+n);if(c){c.classList.remove('locked');c.classList.add('free');c.onclick=()=>openLesson(n,c.querySelector('.lesson-title').textContent);}if(b){b.textContent='\\u0645\\u0634\\u062a\\u0631\\u0643';b.className='lesson-badge free-badge';}});
      }
      completed.forEach(key=>{
        const km={'lesson1':'1','lesson2':'2','lesson3':'3','lesson4':'4','lesson-m1':'5','lesson-m2':'6','lesson-m3':'7','lesson-m4':'8','lesson-k1':'9','lesson-k2':'10','lesson-k3':'11','lesson-k4':'12'};
        const num=km[key];if(!num)return;
        const badge=document.getElementById('lbadge-'+num);const card=document.getElementById('lcard-'+num);
        if(badge){badge.textContent='\\u2705 \\u0645\\u0643\\u062a\\u0645\\u0644';badge.style.cssText='background:#dcfce7;color:#16a34a';}
        if(card){card.style.borderColor='rgba(22,163,74,0.4)';}
      });
    }).catch(()=>{});
  }
"""

# ─────────────────────────────────────────────────────────────────
# LESSON CONFIG: which files require subscription
# ─────────────────────────────────────────────────────────────────
LESSON_CONFIG = {
    'lesson1.html':   False,   # free
    'lesson2.html':   False,   # free
    'lesson3.html':   True,    # paid
    'lesson4.html':   True,    # paid
    'lesson-m1.html': False,   # free (first in mutawassit)
    'lesson-m2.html': True,
    'lesson-m3.html': True,
    'lesson-m4.html': True,
    'lesson-k1.html': True,
    'lesson-k2.html': True,
    'lesson-k3.html': True,
    'lesson-k4.html': True,
}

# ─────────────────────────────────────────────────────────────────
# PATCH FUNCTIONS
# ─────────────────────────────────────────────────────────────────

def patch_lesson_file(html, paid=False):
    """Apply XP patches to a lesson HTML file."""
    log = []

    # 1. Remove local addXP() — replaced by window.addXP
    new_html, n = re.subn(
        r'\nfunction addXP\(a\)\s*\{[^}]+\}\n',
        '\n// addXP \u2192 window.addXP (fikr-xp v2)\n',
        html
    )
    if n:
        log.append('removed local addXP')
    html = new_html

    # 2. Insert XP CSS before the last </style>
    idx = html.rfind('</style>')
    if idx != -1:
        html = html[:idx] + LEVELS_CSS + '\n' + html[idx:]
        log.append('inserted XP CSS')

    # 3. Replace the standalone auth guard IIFE
    #    Look for (async()=>{...})(); that contains onAuthStateChanged
    #    but skip finish() which contains arrayUnion/lessonsCompleted
    init = INIT_PAID if paid else INIT_FREE
    iife_pat = re.compile(
        r'\(async\s*\(\s*\)\s*=>\s*\{[\s\S]*?\}\s*\)\s*\(\s*\)\s*;',
        re.DOTALL
    )
    replaced = False
    for m in iife_pat.finditer(html):
        s = m.group(0)
        # Skip finish() body
        if 'arrayUnion' in s or 'lessonsCompleted' in s:
            continue
        if 'onAuthStateChanged' not in s:
            continue
        html = html[:m.start()] + init + html[m.end():]
        log.append('replaced auth guard')
        replaced = True
        break

    if not replaced:
        log.append('\u26a0 AUTH GUARD NOT FOUND')

    return html, log


def patch_index_file(html):
    """Apply XP widget patches to index.html dashboard."""
    log = []

    # 1. Add CSS
    idx = html.rfind('</style>')
    if idx != -1:
        html = html[:idx] + LEVELS_CSS + '\n' + html[idx:]
        log.append('inserted XP CSS')

    # 2. Add updateDoc to the import in <script type="module">
    if 'updateDoc' not in html[:html.find('function loadDashboard')]:
        html = html.replace('getDoc, getDocs,', 'getDoc, getDocs, updateDoc,', 1)
        log.append('added updateDoc import')

    # 3. Add xp-widget-mount div after the welcome subtitle
    html, n = re.subn(
        r'(id="dash-welcome-name"[^>]*>[^<]*</div>)',
        r'\1\n    <div id="xp-widget-mount"></div>',
        html, count=1
    )
    if n:
        log.append('added xp-widget-mount div')

    # 4. Replace loadDashboard
    # Try with the comment marker first
    pat1 = re.compile(
        r'// ── DASHBOARD LOADER ──\s*\n\s*function loadDashboard\(user\)[\s\S]*?'
        r'(?=\n  // ── AUTH STATE|\n  // ── INIT|\n  onAuthStateChanged)',
        re.DOTALL
    )
    new_html, n = pat1.subn(LOAD_DASHBOARD_NEW, html, count=1)
    if n:
        html = new_html
        log.append('replaced loadDashboard (with marker)')
    else:
        # Fallback: find the function by its signature
        pat2 = re.compile(
            r'function loadDashboard\(user\)\s*\{[\s\S]*?\n  \}(?=\n)',
            re.DOTALL
        )
        new_html, n = pat2.subn(LOAD_DASHBOARD_NEW, html, count=1)
        if n:
            html = new_html
            log.append('replaced loadDashboard (fallback)')
        else:
            log.append('\u26a0 loadDashboard NOT REPLACED')

    return html, log


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    all_html = [f for f in os.listdir('.') if f.endswith('.html')]
    targets  = [f for f in all_html if f in LESSON_CONFIG or f == 'index.html']

    if not targets:
        print('No Fikr HTML files found in current directory.')
        print('Run this script from the same folder as index.html and lesson*.html')
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    print(f'Backing up originals to {BACKUP_DIR}/')

    patched, failed = [], []

    for fname in sorted(targets):
        with open(fname, 'r', encoding='utf-8') as f:
            html = f.read()

        shutil.copy(fname, os.path.join(BACKUP_DIR, fname))

        if fname == 'index.html':
            new_html, log = patch_index_file(html)
        else:
            paid = LESSON_CONFIG.get(fname, False)
            new_html, log = patch_lesson_file(html, paid=paid)

        issues = [l for l in log if '\u26a0' in l]
        if issues:
            failed.append((fname, issues))

        with open(fname, 'w', encoding='utf-8') as f:
            f.write(new_html)

        kb = len(new_html.encode('utf-8')) // 1024
        status = '\u2705' if not issues else '\u26a0'
        print(f'  {status} {fname} ({kb}KB) — {", ".join(log)}')
        patched.append(fname)

    print(f'\n\u2705 Done! {len(patched)} files processed.')
    if failed:
        print('\n\u26a0 Manual attention needed:')
        for fname, issues in failed:
            print(f'  {fname}: {", ".join(issues)}')
    print(f'\n\U0001f4c1 Originals in: {BACKUP_DIR}/')


if __name__ == '__main__':
    main()
