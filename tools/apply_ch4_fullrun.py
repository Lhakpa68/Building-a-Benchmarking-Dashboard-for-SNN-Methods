"""Chapter 4 revision for the full-reference-budget campaign.

Reads the nine training rows from the results database, refuses to run unless
all nine are present, and refuses to run if the measured accuracies contradict
the argument the replacement prose is built around. Every inserted or altered
run is highlighted yellow.

Usage:  python3 apply_ch4_fullrun.py <benchmarks.db> <in.docx> <out.docx>
"""
import sys, re, sqlite3, copy, difflib
from docx import Document
from docx.text.paragraph import Paragraph
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn

DB, SRC, DST = sys.argv[1], sys.argv[2], sys.argv[3]

# Table 4.4 / 4.5 as they stand: 6,000 train / 1,000 test, 3 epochs, hidden 256.
# key -> (s per epoch, accuracy %, measured cost per image s, projected total s)
BASE = {
    'nengo/reference':       (0.87,    85.50, 0.000145,  9.0),
    'spikingjelly/cpu':      (13.79,   94.10, 0.002299, 23.0*60),
    'snntorch/cpu':          (14.50,   93.20, 0.002416, 24.2*60),
    'nest/threads4':         (131.10,   7.40, 0.021850, 3.64*3600),
    'nest/threads2':         (226.88,   7.50, 0.037814, 6.30*3600),
    'nest/threads1':         (407.89,   7.50, 0.067982, 11.33*3600),
    'brian2/cython':         (1062.34,  7.70, 0.177058, 29.5*3600),
    'brian2/numpy':          (1591.98,  7.80, 0.265330, 44.2*3600),
    'brian2/cpp_standalone': (1606.18,  7.80, 0.267697, 44.6*3600),
}
ORDER = ['nengo/reference', 'spikingjelly/cpu', 'snntorch/cpu',
         'nest/threads4', 'nest/threads2', 'nest/threads1',
         'brian2/cython', 'brian2/numpy', 'brian2/cpp_standalone']
LABEL = {'nengo/reference': 'Nengo / reference', 'spikingjelly/cpu': 'SpikingJelly / CPU',
         'snntorch/cpu': 'snnTorch / CPU', 'nest/threads4': 'NEST / 4 threads',
         'nest/threads2': 'NEST / 2 threads', 'nest/threads1': 'NEST / 1 thread',
         'brian2/cython': 'Brian2 / Cython', 'brian2/numpy': 'Brian2 / NumPy',
         'brian2/cpp_standalone': 'Brian2 / C++ standalone'}

# --------------------------------------------------------- measured full run
def load():
    # The mirror on D: is made with a plain copy every 30 s, which is not atomic
    # for a live SQLite file: a copy taken mid-write is a torn file. One was
    # observed at 12:38 on 14 Sep (131,024 bytes against 327,680, "database disk
    # image is malformed"). Reading a torn copy could silently yield partial
    # rows, so check the file before trusting a single number out of it.
    TORN = ("ABORT: the results database is unreadable or malformed (%s). This is "
            "almost certainly a torn mirror copy rather than lost data - the mirror "
            "is a plain copy taken every 30 s, which is not atomic for a live SQLite "
            "file. Wait for the next mirror cycle and re-stage; do NOT treat this as "
            "a failed campaign.")
    try:
        c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
        ic = c.execute("PRAGMA integrity_check").fetchone()[0]
        if ic != "ok":
            sys.exit(TORN % ic)
        nr = c.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        nc = c.execute("SELECT COUNT(*) FROM conditions").fetchone()[0]
    except sqlite3.DatabaseError as e:
        sys.exit(TORN % e)
    if nr < 666 or nc < 138:
        sys.exit("ABORT: database has %d runs / %d conditions, fewer than the 666 / "
                 "138 already recorded. The store is append-only, so this indicates a "
                 "truncated copy rather than real data. Re-stage." % (nr, nc))
    c.row_factory = sqlite3.Row
    rows = c.execute("SELECT framework, backend, runtime_median_s, accuracy_pct, notes "
                     "FROM conditions WHERE task='training' ORDER BY id").fetchall()
    out = {}
    for r in rows:
        n = r['notes'] or ''
        ep  = int(re.search(r'epochs=(\d+)',  n).group(1))
        tn  = int(re.search(r'train_n=(\d+)', n).group(1))
        hid = int(re.search(r'hidden=(\d+)',  n).group(1))
        if (tn, ep, hid) != (60000, 10, 256):
            sys.exit("ABORT: unexpected row %s/%s at train_n=%d epochs=%d hidden=%d"
                     % (r['framework'], r['backend'], tn, ep, hid))
        key = "%s/%s" % (r['framework'], r['backend'])
        per = r['runtime_median_s']                              # MEAN SECONDS PER EPOCH
        neff = 1 if r['framework'] == 'nengo' else ep            # Nengo: one solve
        total = per * neff
        out[key] = dict(per_epoch=per, total=total, acc=r['accuracy_pct'],
                        per_image=total / (tn * neff))
    return out

M = load()
missing = [k for k in ORDER if k not in M]
if missing:
    sys.exit("ABORT: %d of 9 training rows present. Still missing: %s"
             % (len(M), ", ".join(missing)))

# The prose asserts both plasticity families stay below chance and that a tenfold
# budget buys about one point. Verify against the data; never assume.
PLAS = [k for k in ORDER if k.startswith(('nest/', 'brian2/'))]
over = [k for k in PLAS if M[k]['acc'] >= 10.0]
if over:
    sys.exit("ABORT: %s reached or passed the 10%% chance level (%s). The drafted "
             "argument does not hold and the text must be rewritten before insertion."
             % (", ".join(over), ", ".join("%.2f" % M[k]['acc'] for k in over)))
gain = max(M[k]['acc'] - BASE[k][1] for k in PLAS)
if gain > 3.0:
    sys.exit("ABORT: largest plasticity gain is %.2f points, which contradicts the "
             "drafted 'about one percentage point'. Rewrite before insertion." % gain)
for k in ('snntorch/cpu', 'spikingjelly/cpu'):
    if M[k]['acc'] <= BASE[k][1]:
        sys.exit("ABORT: %s did not improve at the larger budget (%.2f vs %.2f); the "
                 "Section 4.6 passage claims a three-to-four point gain." % (k, M[k]['acc'], BASE[k][1]))

def band(keys, f):
    v = sorted(f(k) for k in keys)
    return "%.2f" % v[0] if abs(v[0] - v[-1]) < 0.005 else "%.2f–%.2f" % (v[0], v[-1])

NEST = [k for k in ORDER if k.startswith('nest/')]
BR2  = [k for k in ORDER if k.startswith('brian2/')]
nest_was, nest_now = band(NEST, lambda k: BASE[k][1]), band(NEST, lambda k: M[k]['acc'])
br2_was,  br2_now  = band(BR2,  lambda k: BASE[k][1]), band(BR2,  lambda k: M[k]['acc'])
# The sentence claims the thread counts agree with each other and the
# code-generation backends agree with each other -- not that the two
# families agree. At the full budget they no longer do (NEST 8.3-8.4,
# Brian2 9.9), so the spread is computed within each family.
spread = max(max(M[k]['acc'] for k in g) - min(M[k]['acc'] for k in g)
             for g in (NEST, BR2))
sj, st = M['spikingjelly/cpu']['acc'], M['snntorch/cpu']['acc']
conv_now, conv_was = abs(sj - st), abs(BASE['spikingjelly/cpu'][1] - BASE['snntorch/cpu'][1])
nest_ratio_err = max(abs(BASE[k][3] / M[k]['total'] - 1) for k in NEST)

# ---------------------------------------------------------- verify the baseline
def verify_baseline_against_document(path):
    """Cross-check every hardcoded fixed-budget number against the thesis tables.

    BASE was transcribed by hand from Tables 4.4 and 4.5. A transcription error
    there would put a fabricated number into the revision, so it is checked
    against the source rather than trusted.
    """
    src_doc = Document(path)
    t44, t45 = src_doc.tables[11], src_doc.tables[12]
    def num(s):
        s = s.strip().replace(',', '')
        return float(s) if re.match(r'^-?\d+(\.\d+)?$', s) else None
    a = {r.cells[0].text.strip(): (num(r.cells[4].text), num(r.cells[5].text))
         for r in t44.rows[1:]}
    b = {r.cells[0].text.strip(): num(r.cells[3].text) for r in t45.rows[1:]}
    bad = []
    for k in ORDER:
        lab = LABEL[k]
        se, ac, pi, _ = BASE[k]
        if lab not in a or lab not in b:
            bad.append("%s missing from the tables" % lab); continue
        if abs(a[lab][0] - se) > 1e-6: bad.append("%s s/epoch %s != %s" % (lab, a[lab][0], se))
        if abs(a[lab][1] - ac) > 1e-6: bad.append("%s accuracy %s != %s" % (lab, a[lab][1], ac))
        if abs(b[lab]    - pi) > 1e-9: bad.append("%s per-image %s != %s" % (lab, b[lab], pi))
    if bad:
        sys.exit("ABORT: the fixed-budget baseline does not match the thesis tables:\n  "
                 + "\n  ".join(bad))

verify_baseline_against_document(SRC)

# ------------------------------------------- verify the claims the prose makes
# Each drafted sentence below asserts something about the measured numbers. If
# the data stops supporting a sentence, the sentence must change, so the claim
# is checked here rather than assumed to have survived.
def claim(ok, text):
    if not ok:
        sys.exit("ABORT: the data no longer supports a drafted claim -- %s" % text)

nest_ratios = [BASE[k][3] / M[k]['total'] for k in NEST]
claim(any(r > 1 for r in nest_ratios) and any(r < 1 for r in nest_ratios),
      "'the three ratios fall on both sides of unity' for NEST: %s"
      % ", ".join("%.2f" % r for r in nest_ratios))
claim(max(abs(r - 1) for r in nest_ratios) < 0.10,
      "'accurate to within [single digits] per cent at every thread count': worst is %.1f%%"
      % (100 * max(abs(r - 1) for r in nest_ratios)))
for k in ('snntorch/cpu', 'spikingjelly/cpu'):
    r = BASE[k][3] / M[k]['total']
    claim(1.3 <= r <= 1.9, "'overestimates by about half again' for %s: %.2fx" % (k, r))
rn = BASE['nengo/reference'][3] / M['nengo/reference']['total']
claim(2.2 <= rn <= 2.9, "'by a factor of two and a half' for Nengo: %.2fx" % rn)
for k in ('snntorch/cpu', 'spikingjelly/cpu'):
    g = M[k]['acc'] - BASE[k][1]
    claim(2.5 <= g <= 4.5, "'gain three to four percentage points' for %s: %.2f" % (k, g))
claim(conv_now < conv_was,
      "'they converge on each other': %.2f apart at full budget vs %.2f at reduced"
      % (conv_now, conv_was))
claim(abs(M['nengo/reference']['acc'] - BASE['nengo/reference'][1]) < 0.5,
      "'Nengo does not move at all': %.2f vs %.2f"
      % (M['nengo/reference']['acc'], BASE['nengo/reference'][1]))
claim(M['snntorch/cpu']['per_image'] < BASE['snntorch/cpu'][2],
      "snnTorch per-image cost falls between budgets: %.3f -> %.3f ms"
      % (BASE['snntorch/cpu'][2] * 1000, M['snntorch/cpu']['per_image'] * 1000))

_n4 = ((M['nest/threads4']['per_epoch'] * 10)
       + M['nest/threads4']['per_image'] * (60000 + 10000)) / 3600
claim(3.4 <= _n4 < 4.0,
      "Section 4.8's 'just under four hours' for NEST at four threads: measured %.2f h" % _n4)
claim(_n4 > (200 * 60) / 3600,
      "Section 4.8's claim that the full-budget run exceeds the 3.33 h ceiling: %.2f h" % _n4)
_fix = (BASE['nest/threads4'][0] * 3 + BASE['nest/threads4'][2] * (6000 + 1000)) / 60
claim(7 <= _fix <= 12,
      "Section 4.8's 'about nine minutes' at the fixed budget: %.1f min" % _fix)

# What a tenfold budget buys is NOT uniform across the plasticity rules.
# Measured: NEST gains 0.82-0.99 points; Brian2/Cython gains 2.21 and lands at
# 9.91 per cent, 0.3 standard errors below the ten per cent chance level on a
# 10,000-image test set -- indistinguishable from chance rather than below it.
# An earlier draft of this revision said "about one percentage point" and
# "still below chance" for all six rows. The data supports neither as a blanket
# statement, so both are derived here rather than asserted.
import math

def _gain_band(keys):
    g = sorted(M[k]['acc'] - BASE[k][1] for k in keys)
    return ("%.2f" % g[0]) if abs(g[0] - g[-1]) < 0.005 else "%.2f to %.2f" % (g[0], g[-1])

def _se(pct, n=10000):
    p = pct / 100.0
    return math.sqrt(p * (1 - p) / n) * 100.0

nest_gain, br2_gain = _gain_band(NEST), _gain_band(BR2)
plas_gain_lo = min(M[k]['acc'] - BASE[k][1] for k in PLAS)
plas_gain_hi = max(M[k]['acc'] - BASE[k][1] for k in PLAS)
_closest = max(M[k]['acc'] for k in PLAS)
_closest_se = (10.0 - _closest) / _se(_closest)
# "below chance" is only honest while every row is clear of it. Within two
# standard errors the accurate verb is "does not exceed".
CHANCE_VERB = ("every configuration remains below the ten per cent chance level"
               if _closest_se >= 2.0 else
               "no configuration exceeds the ten per cent chance level, though the "
               "closest now sits within measurement noise of it")

# The Table 4.5 passage called the projection "a sound upper bound". That holds
# only while every ratio is at least 1. Brian2/Cython measured 35.03 h against a
# 29.50 h projection (0.84x), so the claim is derived from the ratios instead.
_ratios = {k: BASE[k][3] / M[k]['total'] for k in ORDER}
PROJ_UNDER = sorted((k for k, r in _ratios.items() if r < 0.98),
                    key=lambda k: _ratios[k])

def _join(items):
    xs = list(items)
    if len(xs) <= 1: return "".join(xs)
    if len(xs) == 2: return " and ".join(xs)
    return ", ".join(xs[:-1]) + " and " + xs[-1]

def hm(s):
    if s >= 3600: return "%.2f h" % (s / 3600)
    if s >= 60:   return "%.1f m" % (s / 60)
    return "%.2f s" % s

# ------------------------------------------------------------------- helpers
def hl(run):
    run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return run

def new_para_after(anchor, text):
    """Insert a paragraph after `anchor`, copying ONLY its pPr.

    Deep-copying the anchor's whole w:p drags its citation fields along, which
    produced a spurious '[12][86][10][41][42]' prefix on an earlier attempt.
    """
    p = copy.deepcopy(anchor._p)
    for child in list(p):
        if child.tag != qn('w:pPr'):
            p.remove(child)
    anchor._p.addnext(p)
    para = Paragraph(p, anchor._parent)
    hl(para.add_run(text))
    return para

def replace_whole(para, text):
    for child in list(para._p):
        if child.tag != qn('w:pPr'):
            para._p.remove(child)
    hl(para.add_run(text))

def sub_in_runs(para, old, new):
    """Swap text inside a single run, highlighting only that run, so that
    citation fields elsewhere in the paragraph are left untouched."""
    for r in para.runs:
        if old in r.text:
            r.text = r.text.replace(old, new)
            hl(r); return True
    raise AssertionError("anchor text not found in any single run: %r" % old[:70])

def append_run(para, text):
    hl(para.add_run(text))

def set_cell(cell, text):
    for p in cell.paragraphs[1:]:
        p._p.getparent().remove(p._p)
    p = cell.paragraphs[0]
    for child in list(p._p):
        if child.tag != qn('w:pPr'):
            p._p.remove(child)
    hl(p.add_run(text))

def add_column(tbl, width_twips=1200):
    """Append one cell to every row and one gridCol to the grid."""
    grid = tbl._tbl.find(qn('w:tblGrid'))
    gc = copy.deepcopy(grid.findall(qn('w:gridCol'))[-1])
    gc.set(qn('w:w'), str(width_twips)); grid.append(gc)
    for row in tbl.rows:
        tc = copy.deepcopy(row.cells[-1]._tc)
        row._tr.append(tc)

def clone_row(tbl, src_row):
    tr = copy.deepcopy(src_row._tr)
    tbl._tbl.append(tr)
    return tbl.rows[-1]

def set_table_widths(tbl, widths):
    """Pin a table to an explicit fixed layout.

    Both tables edited here shipped with tblW=auto and a grid that disagreed
    with the per-cell widths (Table 4.5's cells summed to 10,935 twips against a
    text column of 8,750). Word and LibreOffice then autofit from content, which
    made cloned rows render at different widths from the originals and crushed
    the two new columns. Setting the grid, the table width and every cell to the
    same numbers removes the guesswork.
    """
    from docx.oxml import OxmlElement
    total = sum(widths)
    pr = tbl._tbl.find(qn('w:tblPr'))
    for tag, attrs in (('w:tblW', {'w:w': str(total), 'w:type': 'dxa'}),
                       ('w:tblLayout', {'w:type': 'fixed'})):
        el = pr.find(qn(tag))
        if el is None:
            el = OxmlElement(tag); pr.append(el)
        for k, v in attrs.items():
            el.set(qn(k), v)
    grid = tbl._tbl.find(qn('w:tblGrid'))
    for gc in grid.findall(qn('w:gridCol')):
        grid.remove(gc)
    for w in widths:
        gc = OxmlElement('w:gridCol'); gc.set(qn('w:w'), str(w)); grid.append(gc)
    for row in tbl.rows:
        for tc, w in zip(row._tr.findall(qn('w:tc')), widths):
            tcPr = tc.find(qn('w:tcPr'))
            if tcPr is None:
                tcPr = OxmlElement('w:tcPr'); tc.insert(0, tcPr)
            tcW = tcPr.find(qn('w:tcW'))
            if tcW is None:
                tcW = OxmlElement('w:tcW'); tcPr.append(tcW)
            tcW.set(qn('w:w'), str(w)); tcW.set(qn('w:type'), 'dxa')

# ------------------------------------------------------------------ the edits
doc = Document(SRC)
assert len(doc.tables) == 25, "expected 25 tables, found %d" % len(doc.tables)
before = [p.text for p in doc.paragraphs]
ps = doc.paragraphs

# --- 1. paragraph 542: the sample-budget clause is now disproved -------------
replace_whole(ps[542],
 "The correct interpretation of these six rows is that they measure the absence of those "
 "mechanisms, not the capability of NEST or Brian2, nor the difference between their "
 "thread counts or code-generation backends, each of which agrees with the others in its "
 "own family to within {sp} of a percentage point. An earlier version of this paragraph "
 "also named the size of the "
 "sample budget as a cause. That explanation has since been tested and can be discarded: "
 "re-running the same configurations at the full reference budget of 60,000 training "
 "images over ten epochs moves NEST from {nw} per cent to {nn} per cent and Brian2 from "
 "{bw} per cent to {bn} per cent, and leaves the ordering among thread counts and "
 "code-generation backends unchanged. What the extra data buys is not uniform: NEST gains "
 "{ng} points and Brian2 {bg}, so ten times the sample budget is worth between {glo} and "
 "{ghi} percentage points depending on the rule, and {cv}. "
 "Both frameworks implement spike-timing-dependent plasticity correctly; what is missing "
 "is the surrounding architecture that makes the rule discriminative, and a larger budget "
 "does not substitute for it. This is noted explicitly in the dashboard next to the rows "
 "it affects, with the sample budget each row actually used printed in the same table, "
 "since an accuracy figure reported without its budget invites exactly the misreading "
 "these rows would otherwise produce.".format(
    sp=("a tenth" if spread < 0.1 else
        "%.1f" % spread if spread >= 1.0 else "%.2f" % spread),
    nw=nest_was, nn=nest_now, bw=br2_was, bn=br2_now,
    ng=nest_gain, bg=br2_gain, cv=CHANCE_VERB,
    glo="%.2f" % plas_gain_lo, ghi="%.2f" % plas_gain_hi))

# --- 2. paragraph 541: separate the budget from the mechanisms ---------------
append_run(ps[541],
 " The published procedure pairs those three mechanisms with a much larger sample budget, "
 "and it is worth separating the two. The budget alone was tested here by executing the "
 "full reference configuration, and it is not what carries the result: across the six rows "
 "accuracy rises by between %.2f and %.2f percentage points, and %s. The mechanisms, "
 "not the budget, are what these rows are missing."
 % (plas_gain_lo, plas_gain_hi, CHANCE_VERB))

# --- 3. projection becomes execution (paragraphs 377 and 655) ----------------
sub_in_runs(ps[377],
 "is computed by projection from measured per-image cost rather than execution, and "
 "presented as a projection in Table 4.5.",
 "was first computed by projection from measured per-image cost rather than execution, and "
 "presented as a projection in Table 4.5; it has since been executed in full for all nine "
 "backends, and Table 4.5 now reports the measured cost beside the projection.")

sub_in_runs(ps[655],
 "is shown in Table 4.5 as a projection from measured per-image cost rather than an actual "
 "run, because for the plasticity-based rules that configuration implies between roughly "
 "three and a half and forty-five hours of machine time on this platform, depending on the "
 "backend.",
 "was originally reported in Table 4.5 as a projection from measured per-image cost rather "
 "than an actual run, because for the plasticity-based rules that configuration implies "
 "between roughly three and a half and forty-five hours of machine time on this platform, "
 "depending on the backend. It has since been executed in full, and Table 4.5 now carries "
 "the measured cost beside the projection it replaces.")

# --- 4. Table 4.4: append the nine full-budget rows --------------------------
t44 = doc.tables[11]
src_by_label = {r.cells[0].text.strip(): r for r in t44.rows[1:]}
for k in ORDER:
    src = src_by_label[LABEL[k]]
    rule = src.cells[1].text.strip()
    row = clone_row(t44, src)
    m = M[k]
    set_cell(row.cells[0], LABEL[k])
    set_cell(row.cells[1], rule)
    set_cell(row.cells[2], "60,000 / 10,000, one solve" if k == 'nengo/reference'
                           else "60,000 / 10,000, 10 epochs")
    set_cell(row.cells[3], "256")
    set_cell(row.cells[4], "{:,.2f}".format(m['per_epoch']))
    set_cell(row.cells[5], "%.2f" % m['acc'])
    set_cell(row.cells[6], "-")

append_run(ps[529],
 " The table now carries both budgets. The fixed-budget rows are what make the "
 "cross-framework comparison controlled, since every backend is allocated the same work; "
 "the rows beneath them report the full reference budget of 60,000 training and 10,000 "
 "test images over ten epochs, which is what the specification asks for and which was "
 "executed for all nine backends after the fixed-budget campaign closed.")

# --- 5. Table 4.5: measured and ratio columns, plus the passage that reads them
t45 = doc.tables[12]
add_column(t45); add_column(t45)
set_cell(t45.rows[0].cells[5], "Measured cost, same run")
set_cell(t45.rows[0].cells[6], "Projected ÷ measured")
for r in t45.rows[1:]:
    lab = r.cells[0].text.strip()
    key = next(k for k in ORDER if LABEL[k] == lab)
    set_cell(r.cells[5], hm(M[key]['total']))
    set_cell(r.cells[6], "%.2f×" % (BASE[key][3] / M[key]['total']))

sub_in_runs(ps[536],
 "and the cost of the full reference specification extrapolated from it.",
 "and the cost of the full reference specification, projected from it and then measured by "
 "executing it.")

new_para_after(ps[537],
 "Setting the projection beside the execution shows where per-image extrapolation is "
 "trustworthy. For NEST it is accurate to within %d per cent at every thread count, and "
 "the three ratios fall on both sides of unity: the cost of that rule genuinely is one "
 "simulation call per image, so multiplying a per-image figure by the image count is the "
 "right model, and the measured per-image cost barely moves between budgets. For the two "
 "gradient libraries the projection overestimates by about half again, and for Nengo's "
 "closed-form solve by a factor of two and a half, because in both cases a share of the "
 "per-image cost measured at the smaller budget is fixed overhead that does not recur: "
 "snnTorch costs %.3f milliseconds per image at 6,000 images and %.3f at 60,000. The "
 "projection is therefore not a safe upper bound. For the plasticity rules it errs in "
 "both directions, between %.2f and %.2f times the measured cost: for %s the measured "
 "cost exceeds the projection, by %d per cent in the worst case, while the remaining "
 "plasticity backends fall between %.2f and %.2f. Those are the expensive rules, where "
 "the number decides whether a run is attempted at all, so a projection built from "
 "per-image cost at a small budget should be read there as an estimate with an error of "
 "roughly a fifth either way, not as a ceiling."
 % (int(nest_ratio_err * 100) + 1,
           BASE['snntorch/cpu'][2] * 1000, M['snntorch/cpu']['per_image'] * 1000,
           min(_ratios[k] for k in PLAS), max(_ratios[k] for k in PLAS),
           _join(LABEL[k] for k in PROJ_UNDER) if PROJ_UNDER else "no backend",
           int(round((max(M[k]['total'] / BASE[k][3] for k in PROJ_UNDER) - 1) * 100))
             if PROJ_UNDER else 0,
           min(_ratios[k] for k in PLAS if k not in PROJ_UNDER),
           max(_ratios[k] for k in PLAS if k not in PROJ_UNDER)))

# --- 6. Section 4.6: what the larger budget separates ------------------------
new_para_after(ps[540],
 "Raising the budget separates the rules by what limits them. The two surrogate-gradient "
 "libraries gain three to four percentage points, SpikingJelly reaching %.2f per cent and "
 "snnTorch %.2f, and they converge on each other: %.2f points apart at the full budget "
 "against %.2f at the reduced one, which is further evidence that the harness is measuring "
 "the shared procedure rather than two implementations of it. Nengo does not move at all, "
 "%.2f against %.2f, which is the expected behaviour for a closed-form solve whose ceiling "
 "is set by how well an ensemble of a given width can represent a 784-dimensional space "
 "rather than by how many examples it is shown. The plasticity rules gain between %.2f and "
 "%.2f points, and %s. Three different limits are therefore visible in one table: sample "
 "efficiency for the gradient rules, representational capacity for the decoder solve, and "
 "a missing homeostatic mechanism for the plasticity rules."
 % (sj, st, conv_now, conv_was, M['nengo/reference']['acc'],
       BASE['nengo/reference'][1], plas_gain_lo, plas_gain_hi, CHANCE_VERB))

# --- 7. paragraph 477: coverage ---------------------------------------------
append_run(ps[477],
 " That coverage describes the fixed-budget campaign. The full reference configuration was "
 "subsequently executed for the same nine backends, and both budgets are reported: the "
 "fixed-budget rows because they are what makes the cross-framework comparison controlled, "
 "and the full-budget rows because they are what the specification asks for.")

# --- 8. Section 4.8: the attempt-ceiling defect ------------------------------
sub_in_runs(ps[549],
 "This campaign identified four defects in the harness and the adapters, three of which "
 "invalidate results",
 "This campaign identified five defects in the harness and the adapters, three of which "
 "invalidate results")

t46 = doc.tables[13]
row = clone_row(t46, t46.rows[1])
set_cell(row.cells[0],
 "The cap on the number of isolated worker attempts used to train NEST was sized against "
 "the fixed sample budget and never revisited: two hundred attempts of sixty seconds, a "
 "ceiling of three hours and twenty minutes of total work.")
set_cell(row.cells[1],
 "No previously reported result is affected. At the full reference budget the cap stopped "
 "the four-thread and single-thread configurations and reported the failure in NEST's "
 "name, which a reader would take as a defect in NEST.")
set_cell(row.cells[2],
 "The ceiling was raised to a thousand attempts of five minutes and all three NEST "
 "configurations then completed normally.")

new_para_after(ps[551],
 "A fifth defect belongs with the four above, and it was found only by running the "
 "experiment at its full size. The harness isolates each NEST training attempt in a "
 "disposable subprocess, for the reason Section 3.9 gives, and caps the number of "
 "attempts. The cap was two hundred, and an attempt ends at a sixty-second deadline "
 "whether or not anything has gone wrong, so the ceiling on total work was three hours "
 "and twenty minutes. At the fixed budget of Table 4.4 the four-thread configuration "
 "needs about nine minutes of that ceiling, or one twentieth of it, which is why the "
 "limit was never reached during the first campaign. At the full reference budget the "
 "same configuration needs just under four hours once the labelling and test passes are "
 "counted alongside the ten epochs, and the ceiling stops it before it can finish. It "
 "stopped during the labelling pass, having completed all ten training epochs, and the "
 "single-thread configuration was stopped by the same cap; the two-thread configuration "
 "was not. What the harness then reported was that subprocess isolation could not "
 "complete training for that backend after two hundred worker attempts. The message "
 "names NEST, and a reader would reasonably conclude that NEST had failed. Nothing had "
 "failed except the instrument's own retry budget, which had been sized against the old "
 "sample count and never revisited when the sample count changed. The ceiling was raised "
 "to a thousand attempts of five minutes and the three NEST configurations then completed "
 "normally. The general form of this defect is worth stating, because it is not specific "
 "to NEST: a resilience mechanism whose limits are tuned to one problem size will, at a "
 "larger size, fail in a way that attributes the fault to the system under test rather "
 "than to the measuring apparatus.")

# --- 9. consistency sweep: passages elsewhere that my edits would contradict --
# Found by searching the whole document for claims about the projection, the
# defect counts and the shape of Table 4.4, rather than by trusting the draft's
# own list of anchors.

# 9a. Section 4.2 overview and the Chapter 4 summary both count the defects.
sub_in_runs(ps[472], "It documents nine defects in the measurement and reporting instruments found",
                     "It documents ten defects in the measurement and reporting instruments found")
sub_in_runs(ps[472], "four in the harness, three of which invalidate results reported in earlier "
                     "drafts of this work, and five in the recording and reporting layer",
                     "five in the harness, three of which invalidate results reported in earlier "
                     "drafts of this work, and five in the recording and reporting layer")
sub_in_runs(ps[608], "nine defects were found and corrected in the measuring and reporting "
                     "instruments: four in the harness",
                     "ten defects were found and corrected in the measuring and reporting "
                     "instruments: five in the harness")

# 9b. Table 4.4 no longer has one row per combination.
sub_in_runs(ps[530], "one row per framework/backend combination with support for training.",
                     "two rows per framework/backend combination with support for training: one at "
                     "the fixed budget that makes the comparison controlled, and one at the full "
                     "reference budget.")
sub_in_runs(ps[533], "at the same budget, the training times in Table 4.4 span",
                     "at the same fixed budget, the training times in Table 4.4 span")
sub_in_runs(ps[543],
 "What Table 4.4 captures is a snapshot of two convergence curves with different shapes, "
 "taken at three epochs for surrogate-gradient and plasticity alike",
 "What Table 4.4's fixed-budget rows capture is a snapshot of two convergence curves with "
 "different shapes, taken at three epochs for surrogate-gradient and plasticity alike, and "
 "what its full-budget rows add is a second snapshot of the same two curves at ten")

# 9c. Paragraph 534 asserted the projection rather than a run answers the question.
replace_whole(ps[534],
 "For this machine, the projection is computed from measured per-image cost, not a fitted "
 "curve, with the per-image figure given alongside so a reader can recompute it for their "
 "own budget. The full reference configuration costs a matter of seconds for some of the "
 "nine rows and the better part of two days for others. The projection was what answered "
 "the design question at the time it was made, and it has since been checked against "
 "execution rather than left to stand on its own: the configuration was run in full, and "
 "the two figures are set side by side in Table 4.5 so that the projection can be judged "
 "instead of trusted.")

sub_in_runs(ps[535], " and projected cost per image.",
                     " and projected cost per image, with the projection checked against the "
                     "executed run.")

# 9d. Section 6.5 proposed as future work the run this thesis now reports.
sub_in_runs(ps[661],
 "The least novel but most immediately useful extension is to carry out Experiment 2 at the "
 "indicated scale. The necessary infrastructure is there and checkpointed across process "
 "restarts, so the work is a machine time issue, not a development one. It should",
 "Experiment 2 has since been carried out at the indicated scale, and its results are "
 "reported in Section 4.6 beside the fixed-budget campaign: the infrastructure was already "
 "there and checkpointed across process restarts, so the work was a machine time issue "
 "rather than a development one. What that run settled was the cost, and one prediction; "
 "what it did not settle is the converged comparison this extension was really for. "
 "Repeating it should")
sub_in_runs(ps[661],
 " confirming that cheaply avoids spending many hours arriving at the same conclusion.",
 " confirming that cheaply avoids spending many hours arriving at the same conclusion. That "
 "prediction has since been tested from the expensive direction and held: the full-scale run "
 "was executed without the three mechanisms, and ten times the data moved the plasticity "
 "rules by about one percentage point without reaching chance.")

# 9f. Two passages outside Chapter 4 still asserted costs the full-budget run
# has now measured, found by searching the whole thesis for projected or
# estimated durations after the campaign closed (19 Sep).
_pl_lo = min(M[k]['total'] for k in PLAS) / 3600
_pl_hi = max(M[k]['total'] for k in PLAS) / 3600
_gr_lo = min(M[k]['total'] for k in ('snntorch/cpu', 'spikingjelly/cpu')) / 60
_gr_hi = max(M[k]['total'] for k in ('snntorch/cpu', 'spikingjelly/cpu')) / 60
_ne_lo = min(M[k]['total'] for k in NEST) / 3600
_ne_hi = max(M[k]['total'] for k in NEST) / 3600
_b2_lo = min(M[k]['total'] for k in BR2) / 3600
_b2_hi = max(M[k]['total'] for k in BR2) / 3600

# Section 3.7: "That is the correct deliverable" described the projection as the
# deliverable; the executed run now is.
sub_in_runs(ps[377],
 "That is the correct deliverable: the measured per-image cost suggests a full run of "
 "roughly three and a half to forty-five hours for the plasticity-based rules depending "
 "on backend, versus under half an hour for the gradient-based libraries and seconds for "
 "Nengo's single solve — running all of them would have eaten the budget the scalability "
 "sweep needed.",
 "That was the right deliverable when the design was made: the measured per-image cost "
 "suggested a full run of roughly three and a half to forty-five hours for the "
 "plasticity-based rules depending on backend, versus under half an hour for the "
 "gradient-based libraries and seconds for Nengo's single solve, and running all of them "
 "then would have consumed the machine time the scalability sweep needed. Executed "
 "afterwards, the full configuration cost between %.1f and %.1f hours for the "
 "plasticity-based rules, %.1f to %.1f minutes for the gradient-based libraries and %.2f "
 "seconds for Nengo's solve." % (_pl_lo, _pl_hi, _gr_lo, _gr_hi, M['nengo/reference']['total']))

# Section 6.5: "a projected cost of roughly twenty hours per plasticity-based
# framework at the full specification" is contradicted by the measurement.
sub_in_runs(ps[660],
 "at a projected cost of roughly twenty hours per plasticity-based framework at the full "
 "specification.",
 "at a cost the executed full-budget run now bounds from below: at the 25-millisecond "
 "presentation window used here, the full specification cost between %.1f and %.1f hours "
 "per NEST configuration and between %.1f and %.1f hours per Brian2 backend, and the "
 "longer presentation window of the reference method would lengthen every run further."
 % (_ne_lo, _ne_hi, _b2_lo, _b2_hi))
claim(_pl_lo < 20 < _pl_hi, "the replaced 'roughly twenty hours' is contradicted on both sides by the measurement")

# 9e. The abstract and the contributions list also count the defects, and the
# Table 4.4 lead-in asserted the projection answers the question -- which would
# have contradicted the sentence appended to that same paragraph.
sub_in_runs(ps[84], "Nine defects found and corrected are documented",
                    "Ten defects found and corrected are documented")
sub_in_runs(ps[235], "a description of nine defects found in the measurement instruments — four "
                     "in the harness and five in the recording and reporting layer",
                     "a description of ten defects found in the measurement instruments — five "
                     "in the harness and five in the recording and reporting layer")
sub_in_runs(ps[529],
 "extrapolates this forward to the standard reference configuration of 60,000 training "
 "and 10,000 test images over ten epochs; it is that projection, not an executed run, "
 "that answers what the full configuration would cost.",
 "extrapolates this forward to the standard reference configuration of 60,000 training "
 "and 10,000 test images over ten epochs, and sets that projection beside the measured "
 "cost of the run that was subsequently executed.")

# --- 10. pin both edited tables to a fixed layout that fits the text column ---
set_table_widths(doc.tables[11], [1150, 1650, 1400, 800, 1300, 1100, 1350])   # 8750
set_table_widths(doc.tables[12], [1100, 1250, 1750, 1000, 1250, 1200, 1200]) # 8750

claim(any(_ratios[k] < 1 for k in PLAS) and any(_ratios[k] > 1 for k in PLAS),
      "Table 4.5 passage says the plasticity projection errs in both directions")
claim(max(abs(_ratios[k] - 1) for k in PLAS) <= 0.25,
      "Table 4.5 passage says 'roughly a fifth either way': worst is %.0f%%"
      % (100 * max(abs(_ratios[k] - 1) for k in PLAS)))

# ---------------------------------------------------------------- verification
doc.save(DST)

chk = Document(DST)
assert len(chk.tables) == 25, "table count changed: %d" % len(chk.tables)
assert len(chk.tables[11].rows) == 19, "Table 4.4 rows: %d" % len(chk.tables[11].rows)
assert len(chk.tables[12].columns) == 7, "Table 4.5 cols: %d" % len(chk.tables[12].columns)
assert len(chk.tables[13].rows) == 6, "Table 4.6 rows: %d" % len(chk.tables[13].rows)

after = [p.text for p in chk.paragraphs]
print("paragraphs %d -> %d  (expected +3)" % (len(before), len(after)))
nhl = sum(1 for p in chk.paragraphs for r in p.runs
          if r.font.highlight_color == WD_COLOR_INDEX.YELLOW)
print("yellow runs in body: %d" % nhl)
print("\n--- paragraph diff ---")
for line in difflib.unified_diff(before, after, lineterm='', n=0):
    if line.startswith(('+++', '---', '@@')):
        print(line)
    else:
        print(line[:1] + " " + line[1:220])
print("\nSaved", DST)
