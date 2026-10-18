"""Thesis revision for the CPU-corrected re-measurement (20 Sep 2026).

Experiments 1 and 3, and every energy / utilisation / sensitivity figure that
depends on them, are rebuilt from the CPU-corrected session; the August and
September campaigns and the twin corrected session are used only as
replications. Every inserted or altered run is highlighted yellow. Every
number is read from the stored measurements; every qualitative claim the new
prose makes about those numbers is checked by claim() before it is written.

Usage:  python3 apply_cpu_correction.py <in.docx> <out.docx>
"""
import sys, json, math, copy, sqlite3, re
import numpy as np
from docx import Document
from docx.text.paragraph import Paragraph
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn

SRC, DST = sys.argv[1], sys.argv[2]
D = "/root/work/cpu/data/"
S = {k: json.load(open(D + f"summary_{k}.json")) for k in ("C1", "C2", "A", "S")}
C1 = S["C1"]
F = json.load(open(D + "facts.json"))
AN = json.load(open(D + "analysis_session1.json"))
NS = ["100", "500", "1000", "5000", "10000"]
B = sorted(C1["times"])
db1 = sqlite3.connect(D + "c1.db")


def claim(ok, text):
    if not ok:
        sys.exit("ABORT: the data no longer supports a drafted claim -- " + text)


LAB = {"brian2/cpp_standalone": "Brian2 / C++ standalone", "brian2/cython": "Brian2 / Cython",
       "brian2/numpy": "Brian2 / NumPy", "nest/threads1": "NEST / 1 thread",
       "nest/threads2": "NEST / 2 threads", "nest/threads4": "NEST / 4 threads",
       "nengo/reference": "Nengo / reference", "snntorch/cpu": "snnTorch / CPU",
       "spikingjelly/cpu": "SpikingJelly / CPU", "reference/scalar": "NumPy control / scalar",
       "reference/vectorised": "NumPy control / vectorized"}
PROSE = {"brian2/cpp_standalone": "Brian2's C++ standalone target", "brian2/cython": "Brian2's Cython target",
         "brian2/numpy": "Brian2's NumPy target", "nest/threads1": "NEST with one thread",
         "nest/threads2": "NEST with two threads", "nest/threads4": "NEST with four threads",
         "nengo/reference": "Nengo", "snntorch/cpu": "snnTorch", "spikingjelly/cpu": "SpikingJelly",
         "reference/scalar": "the scalar NumPy control", "reference/vectorised": "the vectorized NumPy control"}
CTRL = {"reference/scalar", "reference/vectorised"}
CD = {"brian2/cpp_standalone"}


def ms(s, d=3): return f"{s * 1000:.{d}f}"
def f3(x): return f"{x:.3f}"
def sg(x): return f"{x:+.3f}"
def pct(x, d=1): return f"{x:.{d}f}"


# ------------------------------------------------------------------ facts
inf = F["inf"]
T = C1["times"]; K = C1["fits"]; M = C1["mem"]; U = C1["cpu_sc"]; R = C1["ranks"]
tau = C1["tau_size"]; tm = C1["tau_metric"]; dec = C1["decomp"]
fastest = F["fastest_fw"]; slowest = F["slowest_fw"]
claim(fastest == "nest/threads4", "fastest framework configuration at N=100 is NEST/4 threads")
claim(slowest == "brian2/numpy", "slowest non-compiling framework configuration at N=100 is Brian2/NumPy")
claim(min(B, key=lambda b: inf[b]["med"]) == "reference/vectorised", "vectorized control fastest overall at N=100")

# exponents
kord = sorted(B, key=lambda b: -K[b]["k"])
claim(kord[0] == "nengo/reference", "Nengo steepest")
claim(set(kord[-3:]) == {"brian2/cpp_standalone", "brian2/cython", "brian2/numpy"}, "Brian2 flattest three")
loose = [b for b in B if K[b]["r2"] < 0.9]
claim(set(loose) == {"brian2/cpp_standalone", "brian2/cython", "brian2/numpy", "snntorch/cpu"},
      "fits with R^2 < 0.9 are the three Brian2 targets and snnTorch: %s" % loose)

# ranks
r100, r10k = R["100"], R["10000"]
claim((r100["nengo/reference"], r10k["nengo/reference"]) == (5, 11), "Nengo 5 -> 11")
claim((r100["brian2/numpy"], r10k["brian2/numpy"]) == (9, 2), "Brian2/NumPy 9 -> 2")
claim((r100["brian2/cython"], r10k["brian2/cython"]) == (10, 3), "Brian2/Cython 10 -> 3")
claim((r100["nest/threads4"], r10k["nest/threads4"]) == (2, 5), "NEST/4 2 -> 5")
claim((r100["nest/threads2"], r10k["nest/threads2"]) == (3, 4), "NEST/2 3 -> 4")
claim((r100["nest/threads1"], r10k["nest/threads1"]) == (4, 6), "NEST/1 4 -> 6")
fw_only = [b for b in B if b not in CTRL]
top4_100 = sorted(fw_only, key=lambda b: T[b]["100"])[:4]
top4_10k = sorted(fw_only, key=lambda b: T[b]["10000"])[:4]
claim(top4_100 == ["nest/threads4", "nest/threads2", "nest/threads1", "nengo/reference"], "top four at 100: %s" % top4_100)
claim(top4_10k == ["brian2/numpy", "brian2/cython", "nest/threads2", "nest/threads4"], "top four at 10k: %s" % top4_10k)

def cd_pairs(t):  # concordant / discordant among 55 pairs (no ties in runtime)
    c = round((1 + t) / 2 * 55); return c, 55 - c
weakest_n = min(NS[:-1], key=lambda n: tau[n])
claim(weakest_n == "500", "weakest point of the sweep is N=500 in this session")

# between-session replication
def ktau(a, b):
    n = len(a); C = Dd = ta = tb = 0
    for i in range(n):
        for j in range(i + 1, n):
            da = a[i] - a[j]; db = b[i] - b[j]; p = da * db
            if p > 0: C += 1
            elif p < 0: Dd += 1
            else:
                if da == 0: ta += 1
                if db == 0: tb += 1
    n0 = n * (n - 1) / 2
    return (C - Dd) / math.sqrt((n0 - ta) * (n0 - tb))
between = {o: [ktau([T[b][n] for b in B], [S[o]["times"][b][n] for b in B]) for n in NS] for o in ("C2", "A", "S")}
bt_lo = min(min(v) for v in between.values()); bt_hi = max(max(v) for v in between.values())
twin_lo = min(between["C2"])
within100 = [S[k]["tau_size"]["100"] for k in S]
weakest_all = [min(S[k]["tau_size"][n] for n in NS[:-1]) for k in S]
claim(bt_lo > max(within100), "between-session agreement at fixed N exceeds within-session agreement across the sweep")
twin_ratio = [S["C2"]["times"][b][n] / T[b][n] for b in B for n in NS]
nest10k_ratio = [T[b]["10000"] / S[o]["times"][b]["10000"] for b in ("nest/threads1", "nest/threads2", "nest/threads4") for o in ("A", "S")]
nengo1k = T["nengo/reference"]["1000"] / S["A"]["times"]["nengo/reference"]["1000"]

# memory
growth = {b: M[b]["10000"] - M[b]["100"] for b in B}
kbpn = {b: growth[b] * 1024 / 10000 for b in B}
nest = ["nest/threads1", "nest/threads2", "nest/threads4"]
others100 = [M[b]["100"] for b in B if b not in nest]
claim(max(kbpn, key=kbpn.get) == "nengo/reference", "Nengo has the largest per-neuron growth")
claim(max(M[b]["100"] for b in B if b not in CTRL) == M["spikingjelly/cpu"]["100"], "SpikingJelly largest framework footprint at N=100")
claim(sorted(kbpn, key=kbpn.get, reverse=True)[1] in nest, "NEST second-largest per-neuron growth")

# utilisation
allcpu = [r[0] for r in db1.execute("select cpu_pct from runs")]
claim(all(v is not None for v in allcpu) and len(allcpu) == 660, "every one of the 660 runs has a utilisation reading")
claim(abs(dec["u_med"] - np.median(allcpu)) < 1e-9, "decomposition median consistent")
lo_run = db1.execute("select framework,backend,network_size,runtime_s,cpu_pct from runs order by cpu_pct limit 1").fetchone()
claim(lo_run[:3] == ("snntorch", "cpu", 500), "lowest-utilisation run is a snnTorch N=500 run")
lo_ratio = lo_run[3] / T["snntorch/cpu"]["500"]
claim(lo_ratio > 2, "that run took more than twice its condition's median")
single = [b for b in B if all(90 <= U[b][n] <= 110 for n in NS) and 90 <= inf[b]["cpu"] <= 110]
claim(set(single) == {"brian2/numpy", "brian2/cython", "nest/threads1", "snntorch/cpu", "reference/scalar", "reference/vectorised"},
      "configurations within ten per cent of one core throughout: %s" % single)
claim(all(390 <= U["nest/threads4"][n] <= 490 for n in NS) and all(199 <= U["nest/threads2"][n] <= 225 for n in NS)
      and all(99 <= U["nest/threads1"][n] <= 101 for n in NS), "NEST utilisation tracks thread count")
claim(all(U["nengo/reference"][n] > 3000 for n in ("1000", "5000", "10000")) and all(U["nengo/reference"][n] < 101 for n in ("100", "500")),
      "Nengo one core below N=1000, ~31 cores from N=1000")
claim(all(785 <= U["brian2/cpp_standalone"][n] <= 800 for n in NS), "C++ standalone ~8 cores throughout")

# energy validation
rho = C1["rho_backend"]
perfect = [b for b in B if abs(rho[b]["rho"] - 1) < 1e-9]
claim(set(B) - set(perfect) == {"brian2/numpy", "brian2/cython", "brian2/cpp_standalone"}, "all but Brian2 at rho=+1")
sens = C1["tdp_exp_sens"]
n_one = sum(1 for s in sens if abs(s["tau"] - 1) < 1e-9)
claim(n_one == 6 and all(s["a"] == 1.2 for s in sens if abs(s["tau"] - 1) > 1e-9), "six of nine at 1.000, the rest at exponent 1.2")
swap = {tuple(x) for s in sens for x in s["swaps"]}
claim(swap == {("nest/threads2", "spikingjelly/cpu")}, "the only swap is NEST/2 threads with SpikingJelly: %s" % swap)
tau_sens_lo = min(s["tau"] for s in sens)
claim(tm["energy"] > tm["memory"] > tm["exponent"], "metric taus order energy > memory > exponent")
rp = C1["rho_pooled"]

E10 = {b: C1["energy_sc"][b]["10000"] for b in B}
disc = [(a, b) for i, a in enumerate(B) for b in B[i + 1:] if (T[a]["10000"] - T[b]["10000"]) * (E10[a] - E10[b]) < 0]
claim(disc and all({"nest/threads2", "nest/threads4"} & {a, b} for a, b in disc), "every discordant energy/runtime pair involves NEST/2 or NEST/4")
eo = sorted(B, key=lambda b: E10[b])
adj = min(range(len(eo) - 1), key=lambda i: E10[eo[i + 1]] / E10[eo[i]])
claim({eo[adj], eo[adj + 1]} == {"nest/threads2", "spikingjelly/cpu"}, "NEST/2 and SpikingJelly are the closest adjacent pair by energy at N=10,000")
# pairwise
nsep = [(a, b) for a, b, p in F["pairs_ns"]]
claim(len(nsep) == 5 and F["pairs_sep"] == 50, "50 of 55 separated")
claim(F["shapiro_reject"] == ["nest/threads1"], "only NEST/1 thread rejects normality")
lev, an = C1["levene"], C1["anova"]

# NEST threads
n1, n2, n4 = (T[b]["10000"] for b in nest)
c2n2, c2n4 = S["C2"]["times"]["nest/threads2"]["10000"], S["C2"]["times"]["nest/threads4"]["10000"]
claim(abs(n4 / n2 - 1) < 0.02 and c2n4 < c2n2, "NEST 2 vs 4 threads at N=10,000 within 2% here, reversed in the twin session")

n1_runs = [q[0] for q in db1.execute("select runtime_s from runs where framework='nest' and backend='threads1' and task='inference' and phase='simulate'")]
n1_slow_n = sum(1 for v in n1_runs if v > 1.15 * np.median(n1_runs))
claim(n1_slow_n == 2, "NEST/1 thread has two slow inference runs")
n1_slow = "two"
first = db1.execute("select framework||'/'||backend from runs where task='inference' order by id limit 1").fetchone()[0]
claim(first == "brian2/numpy", "Brian2/NumPy is the first measurement of the session")
# exponent/runtime agreement with and without Brian2 targets
def tau_excl(ex):
    bs = [b for b in B if b not in ex]
    return ktau([K[b]["k"] for b in bs], [T[b]["10000"] for b in bs])
tau_wo_fast_b2 = tau_excl({"brian2/numpy", "brian2/cython"})
tau_wo_cpp = tau_excl({"brian2/cpp_standalone"})
claim(tau_wo_fast_b2 < tm["exponent"] < tau_wo_cpp, "fast flat Brian2 targets raise, compile-dominated lowers exponent agreement")
# NEST 4 vs 2 threads at mid sizes
n42_mid = [T["nest/threads2"][n] / T["nest/threads4"][n] for n in ("500", "1000")]
claim(all(1.1 < v < 1.25 for v in n42_mid), "four threads ~15% faster than two at N=500 and 1,000")
nest_b2 = [kbpn[b] / kbpn["brian2/numpy"] for b in nest]
twin_ratio_sc = twin_ratio
# ------------------------------------------------------------------ helpers
def hl(run):
    run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return run

def replace_whole(para, text):
    for child in list(para._p):
        if child.tag != qn('w:pPr'):
            para._p.remove(child)
    hl(para.add_run(text))

def new_para_after(anchor, text):
    p = copy.deepcopy(anchor._p)
    for child in list(p):
        if child.tag != qn('w:pPr'):
            p.remove(child)
    anchor._p.addnext(p)
    para = Paragraph(p, anchor._parent)
    hl(para.add_run(text))
    return para

def sub_in_runs(para, old, new):
    runs = para.runs
    for r in runs:
        if old in r.text:
            r.text = r.text.replace(old, new); hl(r); return
    # the anchor spans several runs: merge exactly those runs, provided they are
    # adjacent siblings (no field or hyperlink between them), into the first
    texts = [r.text for r in runs]
    full = "".join(texts)
    pos = full.find(old)
    assert pos >= 0, "anchor not in paragraph: %r" % old[:80]
    starts = []; acc = 0
    for t_ in texts:
        starts.append(acc); acc += len(t_)
    i0 = max(i for i, st_ in enumerate(starts) if st_ <= pos)
    end = pos + len(old)
    i1 = max(i for i, st_ in enumerate(starts) if st_ < end)
    SAFE = {qn('w:proofErr'), qn('w:bookmarkStart'), qn('w:bookmarkEnd')}
    for a in range(i0, i1):
        nx = runs[a]._r.getnext()
        while nx is not runs[a + 1]._r:
            assert nx is not None and nx.tag in SAFE, "refusing to merge across %s" % (None if nx is None else nx.tag)
            nx = nx.getnext()
    merged = "".join(texts[i0:i1 + 1])
    local = pos - starts[i0]
    runs[i0].text = merged[:local] + new + merged[local + len(old):]
    hl(runs[i0])
    for a in range(i0 + 1, i1 + 1):
        runs[a]._r.getparent().remove(runs[a]._r)

def append_run(para, text):
    hl(para.add_run(text))

def set_cell(cell, text):
    p = cell.paragraphs[0]
    # keep the cell's own character formatting (tables use a smaller size)
    rpr = None
    for para in cell.paragraphs:
        for r in para.runs:
            if r._r.rPr is not None:
                rpr = copy.deepcopy(r._r.rPr); break
        if rpr is not None: break
    for extra in cell.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)
    for child in list(p._p):
        if child.tag != qn('w:pPr'):
            p._p.remove(child)
    run = p.add_run(text)
    if rpr is not None:
        hlel = rpr.find(qn('w:highlight'))
        if hlel is not None: rpr.remove(hlel)
        run._r.insert(0, rpr)
    hl(run)

def fill_table(tbl, rows, header=None):
    """Overwrite a table's body with `rows`, cloning the last body row as needed."""
    body = list(tbl.rows)[1:]
    while len(body) < len(rows):
        tr = copy.deepcopy(body[-1]._tr); tbl._tbl.append(tr); body = list(tbl.rows)[1:]
    while len(body) > len(rows):
        tbl._tbl.remove(body[-1]._tr); body = list(tbl.rows)[1:]
    if header:
        for c, t in zip(tbl.rows[0].cells, header):
            if t is not None and c.text != t:
                set_cell(c, t)
    for r, vals in zip(body, rows):
        for c, v in zip(r.cells, vals):
            if c.text != v:
                set_cell(c, v)


doc = Document(SRC)
P = doc.paragraphs
assert len(doc.tables) == 25
def expect(i, start):
    assert P[i].text.startswith(start), "paragraph %d moved: %r" % (i, P[i].text[:80])

# ======================================================================= text
NEW = {}

# ---- front matter ----------------------------------------------------------
expect(83, "The principal contribution is five findings")
NEW[83] = ("The principal contribution is five findings showing the framework ordering is not stable. "
    f"By runtime at ten thousand neurons, concordance with the ordering at five hundred neurons is only tau = {f3(tau['500'])}, "
    f"and at one hundred neurons it is no higher than {f3(max(within100))} in any of four measurement sessions, while orderings "
    f"re-measured at the same size agree at tau = {f3(bt_lo)} or better. Configurations split by scaling exponent into "
    "problem-dominated and overhead-dominated regimes – the flattest recompiles every invocation, measuring its own compiler "
    f"rather than the simulation. Memory growth per neuron spans the frameworks by more than two orders of magnitude, only "
    f"moderately related to runtime (tau = +{f3(tm['memory'])}), while learning cost separates them by over three orders of "
    "magnitude per image. With processor utilisation measured correctly, the energy proxy tracks an analytic synaptic-operation "
    "count for every backend whose runtime follows the workload and keeps its ordering under substantial constant error; it "
    "is, however, largely runtime rescaled except where a framework uses several cores, and it estimates rather than measures "
    "joules, with physical validation left as future work.")
expect(84, "The thesis also releases the benchmark suite")
NEW[84] = ("The thesis also releases the benchmark suite and dataset with per-run provenance, an interactive dashboard, an "
    "environment probe that determines executable hardware by running a kernel, and a sensitivity analysis separating "
    "framework properties from experimental artefacts. Twelve defects found and corrected are documented, among them a "
    "processor-utilisation instrument that failed in two successive forms and was replaced and checked against known loads, "
    "after which the affected experiments were re-measured; all three research questions are answered, with the conditions "
    "each holds under.")

# ---- chapter 3 --------------------------------------------------------------
expect(374, "The second experiment is about learning")
expect(389, "where U is average processor utilization")
NEW[389] = ("where U is average processor utilization over the measured interval expressed as a percentage, the two numerator "
    "terms are the user-mode and system-mode processor time consumed during that interval by every thread of the process and "
    "by the child processes it waited for, read from the kernel's per-process CPU clock rather than sampled, and ΔT is the "
    "wall-clock duration of the same interval. Values greater than 100 per cent indicate real multi-core execution. An "
    "earlier, sampled form of this measurement was defective and is documented in Section 4.8.")

# ---- 4.1 / 4.2 ---------------------------------------------------------------
expect(472, "Section 4.8 is placed before")
NEW[472] = ("Section 4.8 is placed before the energy and sensitivity analyzes on purpose, as is unusual for a results chapter. "
    "It documents twelve defects in the measurement and reporting instruments found during this study and its analysis - five "
    "in the harness, three of which invalidate results reported in earlier drafts of this work, and seven in the recording and "
    "reporting layer, two of which reached the stored data. One of them, in the processor-utilisation instrument, invalidated "
    "every utilisation and energy figure of the original campaign and required Experiments 1 and 3 to be measured again. The "
    "credibility of a benchmark depends on its instruments, so the state of those instruments is part of the result, not an "
    "appendix to it.")
expect(474, "This chapter is based on one measurement campaign")
NEW[474] = ("This chapter is based on measurements from one machine, and each of its figures, tables and coefficients is derived "
    "from exactly one measurement session; nothing is pooled across sessions or machines, since pooling would violate the "
    "single-platform principle the whole design rests on. All sessions ran on the researcher's own laptop, LT68, covering five "
    "frameworks across eleven executable backends — Brian2 with its NumPy, Cython and C++ standalone targets, NEST with one, "
    "two and four threads, Nengo, snnTorch, SpikingJelly and a plain-NumPy control implemented both scalar and vectorised. "
    "Experiments 1 and 3, and every utilisation, energy and sensitivity figure built on them, come from the session of 20 "
    "September 2026 that repeated the original protocol with the corrected processor-utilisation instrument described in Section "
    "4.8. Experiment 2 comes from the two training campaigns: the fixed-budget campaign of August and the full-budget campaign "
    "of September. The released dashboard reads the same rows, so a number in this chapter and the same number in the interface "
    "come from one query, not two that might disagree.")
expect(476, "The campaign provided 141")
NEW[476] = ("The figures in this chapter rest on 150 conditions from 678 individual measured runs: 132 inference and scalability "
    "conditions from 660 runs in the corrected session, and 18 training conditions. A further 462 condition records in the "
    "database are omitted from every figure. 123 conditions from 595 runs come from an earlier two-core cloud instance used "
    "during development and interface testing; 75 conditions from 363 runs come from earlier, incomplete attempts at the "
    "campaign on this laptop; and 264 conditions from 1,320 runs are replications of Experiments 1 and 3 — the August campaign's "
    "own inference and scalability measurements, whose runtimes stand but whose utilisation readings were withdrawn (Section 4.8), "
    "and a twin corrected session run ten minutes after the reported one. The replications are used for one purpose only, to "
    "test in Section 4.4 whether the results reproduce between sessions. The provenance panel in the dashboard shows the number "
    "of records excluded and why. The reason that the dispersion reported throughout this chapter is available at all, and that "
    "any median quoted here can be recomputed from the values behind it, is that each individual run is retained rather than "
    "only its aggregate. ")

# ---- 4.3 --------------------------------------------------------------------
expect(482, "Median of five measured runs")
NEW[482] = ("Median of five measured runs after five discarded warm-up runs with full measured range, coefficient of variation, "
    "peak process memory (the kernel's high-water mark over the measured interval), mean processor utilization (processor time "
    "over wall time, all threads and waited-for child processes included) and the spike count the equivalence check compares. "
    "Every run carries a utilization reading. The energy index is the energy proxy rescaled so that the costliest simulating "
    "backend reads 100; the compile-dominated target, whose measured time is its compiler's (Section 4.7), reads above 100.")
x = inf
expect(487, "The fastest framework configuration is NEST with two threads")
NEW[487] = (f"The fastest framework configuration is NEST with four threads at {ms(x[fastest]['med'])} ms, while the slowest is "
    f"Brian2's C++ standalone target at {x['brian2/cpp_standalone']['med']:.3f} s, a {F['spread_all']:.0f}-fold difference. That "
    "is not the figure to quote, and it is misleading in itself. Excluding the compiling backend, the spread across directly "
    f"comparable framework configurations is {F['spread_fw']:.1f} times, ranging from NEST with four threads at "
    f"{ms(x[fastest]['med'])} ms to Brian2's NumPy target at {ms(x[slowest]['med'])} ms, for the reasons outlined in Section 4.7. "
    f"At this size the vectorized NumPy control is faster than every framework, at {ms(x['reference/vectorised']['med'])} ms. "
    "The vectorized NumPy control is not a competitor; it is a control. What it establishes is that at one hundred neurons no "
    "framework's machinery has yet begun to pay for itself.")
cvlo, cvhi = F["cv_range_all"]
claim(F["cv_min_b"] == "brian2/cython" and F["cv_max_b"] == "nest/threads1", "CV extremes")
claim(cvhi < 12, "no backend above 12 per cent CV")
expect(488, "The run-to-run spread differs")
NEW[488] = (f"The run-to-run spread is modest throughout: the coefficient of variation ranges from {cvlo:.1f}% for Brian2's "
    f"Cython target to {cvhi:.1f}% for NEST with one thread, and no backend exceeds twelve per cent. Dispersion is itself a "
    f"property of a session rather than of a backend: in the August campaign Nengo's coefficient was "
    f"{58.0:.1f}%, against {x['nengo/reference']['cv']:.1f}% here; the cause of that difference was not measured. That is why the comparisons below are made on distributions "
    "rather than on point estimates, why the measured ranges in Table 4.1 matter more than the medians, and why Section 4.4 "
    "measures reproducibility between sessions directly instead of inferring it from the spread within one.")
claim(abs(S["A"]["inference"][[i["b"] for i in S["A"]["inference"]].index("nengo/reference")]["cv"] - 58.0) < 0.05,
      "August Nengo CV was 58.0%")
expect(489, "Normality is assumed not checked")
NEW[489] = ("Normality is checked, not assumed. Section 3.10 explains why: with five retained runs per condition a normality "
    "test has very low power, so the result is reported explicitly for every backend instead of silently assumed either way. "
    "The Shapiro-Wilk test fails to reject normality at the 0.05 level for ten of the eleven backends and rejects it for one, "
    f"NEST with one thread (p = {C1['shapiro']['nest/threads1']:.3f}), whose five runs include {n1_slow} slow ones — the "
    f"right-skew a runtime distribution often has. Levene's test over all eleven backends yields W = {lev['W']:.2f}, "
    f"p = {lev['p']:.1e}: variances differ significantly between backends. This excludes the classical one-way ANOVA and is the "
    "reason for using Welch's version, which does not assume equal variances.")
expect(490, "Using Welch's one-way ANOVA")
NEW[490] = (f"Using Welch's one-way ANOVA on all eleven backends, we observe F({an['df1']}, {an['df2']:.2f}) = {an['F']:.2f} on 55 "
    f"observations, p = {an['p']:.1e}, eta-squared = {an['eta_sq']:.4f}. The difference between the backends is not surprising, "
    "and the effect size shows that essentially all of the variance in the measurement is due to which backend produced it, "
    "rather than run-to-run noise. What is useful is information about which pairs differ, and by how much.")
expect(491, "Significance is reported pairwise")
NEW[491] = ("Significance is reported pairwise, and at this sample size that's worth flagging rather than taking for granted: "
    "five runs per side is small, and a Welch t-test's own within-group normality assumption does not hold for one of the "
    "eleven backends, as the previous paragraph states. These comparisons should be read with that caveat, and Cohen's d is "
    "reported next to every p-value so a reader can judge the size of a separation independent of whether the corrected p-value "
    f"crosses 0.05. Eleven backends give fifty-five pairs; {F['pairs_sep']} separate at the 0.05 level after Holm correction and "
    "five do not — exactly the pairs one would expect to be close: NEST's three thread counts against each other, Brian2's "
    "Cython and NumPy targets against each other, and the scalar NumPy control against snnTorch. Table 4.2 shows the results "
    "against the fastest framework configuration, NEST with four threads, with the full fifty-five-pair matrix in Appendix C.")
expect(493, "By Welch")
NEW[493] = ("By Welch's t-test with Holm correction, in all fifty-five pairwise comparisons. Cohen's d is the standardized mean "
    "difference between the five retained runs of the configuration and those of the baseline; a positive d means slower than "
    "the baseline. Pairs are reported as separated at that level, not just different in their point estimate, if a "
    "Holm-corrected p < 0.05.")

# ---- 4.4 --------------------------------------------------------------------
expect(506, "The exponents divide")
k = {b: K[b]["k"] for b in B}
NEW[506] = (f"The exponents divide the configurations into two regimes. Nengo is steepest at k = {sg(k['nengo/reference'])}, "
    f"more than proportional to network size; NEST follows at k = {sg(k['nest/threads1'])}, {sg(k['nest/threads4'])} and "
    f"{sg(k['nest/threads2'])} with one, four and two threads, and the scalar NumPy control is almost exactly proportional at "
    f"k = {sg(k['reference/scalar'])}. At the other end, Brian2's three targets sit at k = {sg(k['brian2/cython'])}, "
    f"{sg(k['brian2/numpy'])} and {sg(k['brian2/cpp_standalone'])} — a configuration whose runtime doesn't scale with the "
    "problem isn't measuring the problem, and Section 4.7 explains what those three are measuring instead.")
expect(507, "Four fits deserve caution")
NEW[507] = (f"Four fits deserve caution, and the figure shows them as such rather than a bare point estimate: Brian2/C++ "
    f"standalone (R² = {K['brian2/cpp_standalone']['r2']:.3f}), Brian2/Cython ({K['brian2/cython']['r2']:.3f}), Brian2/NumPy "
    f"({K['brian2/numpy']['r2']:.3f}) and snnTorch/CPU ({K['snntorch/cpu']['r2']:.3f}) all describe a single power law only "
    "loosely. For the Brian2 targets that is the finding itself, not a defect in the fit — a poor power-law fit is what a runtime "
    "independent of network size looks like. For snnTorch the exponent is better read as a summary of the trend, with the "
    "measured points in Table 4.3 the more trustworthy statement.")
expect(508, "The ordering by speed is not stable")
NEW[508] = ("The ordering by speed is not stable across the sweep — the clearest evidence is the individual movements, not a "
    "summary statistic. Nengo drops from rank 5 to rank 11 (last of eleven) between the smallest and largest measured network, "
    "having started mid-pack. Brian2/NumPy climbs from rank 9 to rank 2 and Brian2/Cython from rank 10 to rank 3. NEST/4-threads "
    "drops from rank 2 to rank 5, NEST/2-threads from rank 3 to rank 4 and NEST/1-thread from rank 4 to rank 6. Counting only "
    "framework configurations, the four fastest at one hundred neurons are NEST/4-threads, NEST/2-threads, NEST/1-thread and "
    "Nengo; at ten thousand they are Brian2/NumPy, Brian2/Cython, NEST/2-threads and NEST/4-threads. The fastest at the small end "
    "is not the fastest at the large end, and Nengo — fourth-fastest framework configuration at a hundred neurons — ends up last "
    "of all eleven backends at ten thousand.")
c100, d100 = cd_pairs(tau["100"]); c500, d500 = cd_pairs(tau["500"])
expect(509, "Across all eleven backends, Kendall's tau-b")
NEW[509] = (f"Across all eleven backends, Kendall's tau-b between the ordering at one hundred neurons and at ten thousand is "
    f"{f3(tau['100'])} — a tau of one would mean the orderings are identical, and at {f3(tau['100'])} only {c100} of the 55 pairs "
    f"are ordered the same way against {d100} ordered the opposite way. Agreement is weaker still at five hundred neurons "
    f"({f3(tau['500'])}, the weakest point in the sweep), {f3(tau['1000'])} at one thousand, before recovering to "
    f"{f3(tau['5000'])} at five thousand. No p-value is given: with eleven items a rank test has very little power, so the "
    "movements above are the substantive findings. The same coefficients reappear in Section 4.10, there as the main result "
    "rather than a summary.")
REPRO = (f"A single session cannot show whether these movements are larger than the noise of measuring the same thing twice, "
    "so the sweep was compared across the four sessions that measured it on this laptop — the session reported here, its twin "
    "run ten minutes later with the same instrument, the August campaign and the September full-scale campaign, whose runtimes "
    "were timed with the same high-resolution clock throughout. At any fixed size, the ordering from another session agrees with "
    f"this session's at tau = {f3(bt_lo)} to {f3(bt_hi)} (the twin: {f3(twin_lo)} or better). Across the sweep within any one "
    f"session, the ordering at one hundred neurons agrees with the ordering at ten thousand at only tau = {f3(min(within100))} to "
    f"{f3(max(within100))}, and the weakest point of the sweep lies between {f3(min(weakest_all))} and {f3(max(weakest_all))} "
    "in every session — although where in the sweep it falls is not reproducible (five hundred neurons here, one thousand in "
    "August). Network size moves the ordering far more than re-measuring does. Absolute times reproduce less well. Across a "
    f"ten-minute interval every condition of the size sweep in the twin session lies within "
    f"{100 * (min(twin_ratio) - 1):+.0f}% to {100 * (max(twin_ratio) - 1):+.0f}% of this one, but between days the multi-threaded configurations move much further: "
    f"NEST at ten thousand neurons ran {min(nest10k_ratio):.1f} to {max(nest10k_ratio):.1f} times slower in this session than in "
    f"the two earlier campaigns, and Nengo at one thousand neurons {nengo1k:.1f} times slower than in August. The cause of that "
    "between-day variation was not measured and is not asserted here. What reproduces is the ordering and the exponents, not the "
    "time, which is the level at which this chapter's claims are made.")
claim(min(twin_ratio) > 0.75 and max(twin_ratio) < 1.2, "twin session within -25%..+20%")
claim(all(1.3 < r < 3.0 for r in nest10k_ratio), "NEST 10k slower than both earlier campaigns")

expect(514, "The result also refines rather than contradicts")
kn = [k[b] for b in nest]
NEW[514] = ("The result also refines rather than contradicts a finding in the literature. Schmitt et al. show NEST scales "
    "near-linearly with the size of the network on multi-core CPUs and highlight this linearity as a strength, demonstrated in "
    f"real time with a quarter of a million neurons. Here NEST's exponents are {min(kn):.3f} to {max(kn):.3f}, close to but slightly "
    "steeper than proportional, at sizes two orders of magnitude smaller, where the same property is a liability instead of an "
    "asset. The two results are not contradictory: whether near-linear scaling is desirable is purely a matter of the operating "
    "regime, and the framework-selection literature at present does not make that distinction.")

# ---- 4.5 --------------------------------------------------------------------
nest100 = [M[b]["100"] for b in nest]
expect(519, "The largest measured network")
NEW[519] = (f"The largest measured network has a peak resident set size of {M['brian2/numpy']['10000']:.1f} MB for Brian2's "
    f"NumPy target and {M['nengo/reference']['10000']:,.1f} MB for Nengo's reference simulator (a factor of "
    f"{M['nengo/reference']['10000'] / M['brian2/numpy']['10000']:.1f}). Instead of clustering together, at the reference size "
    f"the eleven backends split into two distinct groups. NEST is between {min(nest100):.0f} and {max(nest100):.0f} MB for the "
    "three thread counts, while all the other backends - the two NumPy reference implementations, Nengo, SpikingJelly, snnTorch "
    f"and all three Brian2 targets - are between {min(others100):.0f} and {max(others100):.0f} MB, a difference that is almost "
    "entirely a matter of which process is measured: NEST is measured in its own worker process, which loads NEST and NumPy but "
    "none of the other simulators, while every other backend is measured in the main benchmark process, whose footprint is "
    f"already {M['brian2/numpy']['100']:.0f} MB at the session's first measurement. The measured quantity is the peak resident set size of the whole process, "
    "including the Python interpreter and all imported libraries, taken from the kernel's high-water mark reset at the start of "
    "each measured interval. So, at the reference size, the figure is very largely a measurement of the import cost, not of the "
    "network.")
cpu100 = {b: inf[b]["cpu"] for b in B}
expect(521, "Processor utilisation at the reference size")
NEW[521] = (f"Processor utilisation at the reference size is measured for all eleven backends and ranges from "
    f"{min(cpu100.values()):.1f}% to {max(cpu100.values()):.1f}%. Eight of the eleven use one core ({min(cpu100[b] for b in B if cpu100[b] < 110):.1f}–"
    f"{max(cpu100[b] for b in B if cpu100[b] < 110):.1f}%); the three that use more are NEST with two threads "
    f"({cpu100['nest/threads2']:.1f}%), NEST with four ({cpu100['nest/threads4']:.1f}%) and Brian2's C++ standalone target "
    f"({cpu100['brian2/cpp_standalone']:.1f}%). Values above 100% mean real parallelism. Across all 660 runs of the session the "
    f"median is {dec['u_med']:.1f}%, with the middle half between {dec['u_q1']:.1f}% and {dec['u_q3']:.1f}% and a full range of "
    f"{dec['u_min']:.1f}% to {dec['u_max']:,.1f}%; the lowest is a single snnTorch run that took {lo_ratio:.1f} times its "
    "condition's median, a run during which the process was waiting for part of its interval, and the highest is Nengo using "
    "all thirty-two logical cores. None of these values is a sampling artefact: an earlier version of this section had to exclude "
    "readings in the hundreds of thousands of per cent, and the instrument that produced them has been replaced (Section 4.8).")
claim(sum(1 for b in B if cpu100[b] < 110) == 8, "eight of eleven at one core at N=100")
expect(523, "The informative measure")
NEW[523] = ("The informative measure is therefore not the footprint at any one size but its growth across the sweep, and here "
    f"the frameworks separate sharply — in the opposite direction to what the reference-size figures alone imply. NEST increases "
    f"from roughly {min(nest100):.0f}–{max(nest100):.0f} MB at 100 neurons to {min(M[b]['10000'] for b in nest):.0f}–"
    f"{max(M[b]['10000'] for b in nest):.0f} MB at 10,000 across its three thread counts, an increase of some "
    f"{min(growth[b] for b in nest):.0f}–{max(growth[b] for b in nest):.0f} MB or {min(kbpn[b] for b in nest):.0f}–"
    f"{max(kbpn[b] for b in nest):.0f} KB per neuron (growth divided by the 10,000 neurons of the largest network, the "
    f"convention used throughout). Nengo grows most, from {M['nengo/reference']['100']:.0f} to "
    f"{M['nengo/reference']['10000']:,.0f} MB, {kbpn['nengo/reference']:.0f} KB per neuron. snnTorch and SpikingJelly grow by "
    f"{growth['snntorch/cpu']:.0f} and {growth['spikingjelly/cpu']:.0f} megabytes respectively, close to "
    f"{kbpn['snntorch/cpu']:.0f} kilobytes per neuron. Brian2 barely grows at all: its NumPy target goes from "
    f"{M['brian2/numpy']['100']:.0f} to {M['brian2/numpy']['10000']:.0f} megabytes across the whole sweep, "
    f"{kbpn['brian2/numpy']:.2f} kilobytes per neuron, and its Cython target {kbpn['brian2/cython']:.2f}.")
expect(524, "This ordering is the reverse")
NEW[524] = ("This ordering is the reverse of what a single-size measurement would support. In Experiment 1, SpikingJelly has the "
    f"largest footprint of any framework at {M['spikingjelly/cpu']['100']:.0f} MB at one hundred neurons, and NEST the smallest at "
    f"{min(nest100):.0f}–{max(nest100):.0f} MB across its three thread counts — on that evidence alone NEST looks like the most "
    "memory-efficient framework studied. The ordering over the sweep is almost exactly inverted: Brian2's simulating targets add "
    f"the least per neuron ({kbpn['brian2/cython']:.2f} and {kbpn['brian2/numpy']:.2f} kilobytes), while NEST — smallest footprint "
    f"of any framework at one hundred neurons — adds {min(kbpn[b] for b in nest):.0f}–{max(kbpn[b] for b in nest):.0f} kilobytes, "
    f"second only to Nengo's {kbpn['nengo/reference']:.0f}, and {min(nest_b2):.0f} to {max(nest_b2):.0f} times "
    "Brian2's NumPy target. Both statements come from the same data set; the difference is that one describes the network being "
    "simulated and the other describes what happened to be loaded into the process when the sample was taken.")
sj = U["spikingjelly/cpu"]; ng = U["nengo/reference"]
expect(526, "The second dimension hidden by runtime alone")
NEW[526] = ("The second dimension hidden by runtime alone is processor utilisation, and with the corrected instrument it is "
    "measured for every configuration at every size. NEST's utilisation follows its configured thread count almost exactly: "
    f"{min(U['nest/threads1'][n] for n in NS):.0f}–{max(U['nest/threads1'][n] for n in NS):.0f}% with one thread, "
    f"{min(U['nest/threads2'][n] for n in NS):.0f}–{max(U['nest/threads2'][n] for n in NS):.0f}% with two and "
    f"{min(U['nest/threads4'][n] for n in NS):.0f}–{max(U['nest/threads4'][n] for n in NS):.0f}% with four across the sweep. "
    f"Nengo uses one core up to five hundred neurons ({ng['100']:.0f}–{ng['500']:.0f}%) and then "
    f"{min(ng[n] for n in NS[2:]):,.0f}–{max(ng[n] for n in NS[2:]):,.0f}% from one thousand upwards — about thirty-one of the "
    f"thirty-two logical cores, from its multi-threaded linear algebra. SpikingJelly peaks at mid-sized networks ({sj['500']:.0f}% at five "
    f"hundred neurons, {sj['1000']:.0f}% at one thousand) and falls back towards one core at ten thousand ({sj['10000']:.0f}%), "
    "while snnTorch, the Brian2 NumPy and Cython targets and both NumPy controls stay within ten per cent of one core throughout. "
    f"Brian2's C++ standalone target keeps about eight cores busy ({min(U['brian2/cpp_standalone'][n] for n in NS):.0f}–"
    f"{max(U['brian2/cpp_standalone'][n] for n in NS):.0f}%) at every size; the instrument counts the target's own process "
    "together with the compiler and binary processes it starts, and does not separate the two. An earlier version of this chapter reported that target at 5.3 per cent and NEST as "
    "unmeasurable at the reference size; both statements came from the defective instrument and are withdrawn. The fastest "
    "configurations are not uniformly those that recruit more cores: at one hundred neurons the fastest framework configuration, "
    f"NEST with four threads, uses {cpu100['nest/threads4'] / 100:.1f} cores to finish "
    f"{100 * (1 - x['nest/threads4']['med'] / x['nest/threads1']['med']):.0f}% sooner than NEST with one, a difference Section 4.3 "
    "cannot separate from noise, but at ten thousand the "
    "two fastest framework configurations, Brian2's NumPy and Cython targets, use one core each while Nengo uses "
    f"{ng['10000'] / 100:.1f} and is slowest of all. The comparison is fair in the sense that each framework was configured as its "
    "documentation recommends, not in the sense of equal resources, and that distinction carries over to equation (3.8), where "
    "utilisation is a multiplicand rather than an incidental observation.")
expect(527, "NEST's three thread counts are worth noting")
NEW[527] = ("NEST's three thread counts are worth noting separately, since their ordering does not follow what a reader would "
    f"expect from thread count alone. At the reference size the three are within noise of each other — {ms(x['nest/threads1']['med'])}, "
    f"{ms(x['nest/threads2']['med'])} and {ms(x['nest/threads4']['med'])} ms for one, two and four threads, none separated from "
    f"another after Holm correction. At the largest measured network, two and four threads are indistinguishable ({n2:.3f} s and "
    f"{n4:.3f} s here; in the twin session four threads were the faster, {c2n4:.3f} s against {c2n2:.3f} s) and both beat one "
    f"thread ({n1:.3f} s) by about {100 * (1 - (n2 + n4) / 2 / n1):.0f} per cent. The four-thread configuration consumes twice the "
    "processor time of the two-thread one to reach the same wall-clock time, so on this machine the step from two threads to "
    "four buys nothing at this size but a larger energy proxy. The return on threads also depends on the size of the network: "
    f"at five hundred and one thousand neurons four threads took {100 * (1 - 1 / n42_mid[0]):.1f}% and "
    f"{100 * (1 - 1 / n42_mid[1]):.1f}% less time than two. A reader who assumes threads scale throughput linearly would reach a wrong conclusion at every size "
    "measured here; why the fourth thread stops paying at ten thousand neurons was not measured.")

# ---- 4.6 --------------------------------------------------------------------
expect(531, "The budget column is the same")
NEW[531] = ("The budget column is the same for each row except Nengo, since its closed-form solve has no epoch to state a "
    "budget against; fixing the budget isolates cost per epoch and accuracy as the quantities being compared, rather than "
    "requiring the budget itself to be read as a variable. The energy column is listed as not measured throughout, and the "
    "reason is a limitation of the executed experiment, not of the design in Section 3.7: the training path timed each "
    "adapter's per-epoch work with a wall-clock timer but did not run the utilisation or memory instruments, so neither "
    "processor utilisation — a multiplicative term in the proxy — nor peak memory was observed during training, and an energy "
    "figure built on an assumed utilisation would restate runtime rather than estimate energy. Measuring them now would mean "
    "repeating the training runs with the instruments attached: the full-budget campaign alone occupied this laptop for seven "
    "days and twenty hours of wall-clock time by its own log (12 to 20 September), which is why it was not repeated. The "
    "corresponding measured quantity here is cost per epoch, which both campaigns timed correctly; the placeholder memory value "
    "the training rows once carried is described in Section 4.8.")

# ---- 4.7 --------------------------------------------------------------------
t = T
expect(547, "Brian2’s C++ standalone target took")
NEW[547] = (f"Brian2’s C++ standalone target took {t['brian2/cpp_standalone']['100']:.4f} s for N = 100 and "
    f"{t['brian2/cpp_standalone']['10000']:.4f} s for N = 10,000, giving k = {sg(k['brian2/cpp_standalone'])} with R-squared = "
    f"{K['brian2/cpp_standalone']['r2']:.3f} - a runtime that does not respond at all to a hundredfold change in the size of the "
    "network, which no simulator's workload does. Mean processor utilization over the same sweep stays between "
    f"{min(U['brian2/cpp_standalone'][n] for n in NS):.0f} and {max(U['brian2/cpp_standalone'][n] for n in NS):.0f} per cent — about "
    "eight cores busy throughout. Its two interpreted siblings move in the direction a simulator's runtime should, but only "
    f"weakly: Brian2 / NumPy moves from {t['brian2/numpy']['100']:.4f} s to {t['brian2/numpy']['10000']:.4f} s over the same "
    f"hundredfold change (k = {sg(k['brian2/numpy'])}, R-squared = {K['brian2/numpy']['r2']:.3f}) and Brian2 / Cython from "
    f"{t['brian2/cython']['100']:.4f} s to {t['brian2/cython']['10000']:.4f} s (k = {sg(k['brian2/cython'])}, R-squared = "
    f"{K['brian2/cython']['r2']:.3f}) at one core, with Cython's weaker fit reflecting the near-flat, noise-dominated runtime seen "
    "in its cross-size times in Table 4.3.")
expect(548, "A backend which has a runtime independent")
NEW[548] = ("A backend which has a runtime independent of the problem size is not measuring the problem size. The source code "
    "for Brian2’s standalone devices is regenerated and recompiled on each invocation, as the device must be reinitialized "
    "between runs to prevent the second run silently reusing the first build. The interval measured is therefore dominated by "
    "the compiler, not the simulation, and the processor utilisation is consistent with that: about eight cores' worth of "
    "processor time per run, counted across the Python process and the build and binary processes it starts, against one core "
    "for the targets that simulate in the Python process. How that time divides between compiling and running was not "
    "measured. "
    "An earlier version of this section read the same target's utilisation as five per cent and inferred a process waiting on "
    "its tool-chain; that reading counted only the parent Python process, not the child processes doing the work, and is "
    "withdrawn (Section 4.8).")

# ---- 4.8 --------------------------------------------------------------------
expect(556, "The five defects in results recording")
NEW[556] = ("The seven defects in results recording and reporting were found while building the dashboard and finalising this "
    "chapter, rather than during the original campaign itself. The first four did not affect the underlying measurements, only "
    "the figures presented from them; the fifth and sixth are the exceptions, because each caused a value that was never "
    "measured to be stored as though it had been; the seventh again affected presentation only. This class of error — an "
    "artefact of how results are stored, aggregated or analysed rather than of how they were taken — is invisible in the final "
    "figures, which is exactly why it is the kind most likely to survive into a published table.")
expect(558, "The second is the eligibility")
NEW[558] = ("The second is the eligibility of compile-heavy backends for summary rankings. The Brian2 standalone target rebuilds "
    "and regenerates the model on every invocation, so what it reports is dominated by a C++ toolchain rather than simulation — "
    "with three consequences, each misleading on its own. At the reference size it is an order of magnitude slower than the "
    "slowest simulating backend in the study, a statement about compilation, not about Brian2's simulation performance. When scaled, it "
    f"produces an exponent indistinguishable from zero (k = {sg(k['brian2/cpp_standalone'])}, R² = "
    f"{K['brian2/cpp_standalone']['r2']:.3f}), a result implying the workload does not grow with the network — which no simulator's "
    "does — because the compilation cost is independent of network size while the simulation cost is not. And since the "
    "simulation runs in a separate compiled binary, the process whose memory is measured is not the one holding the network. "
    "Prior to the safeguard, this backend held the top spot for both flattest scaling and lowest peak memory: two of the four "
    "summary figures won by an artifact.")
claim(x["brian2/cpp_standalone"]["med"] / x["brian2/numpy"]["med"] > 10, "C++ standalone an order of magnitude slower than slowest simulating backend")
expect(560, "The third concerns the machine")
sub_in_runs(P[560], "Every query is now restricted to the two run_groups making up the single verified-complete campaign on the "
    "LT68 laptop identified in Section 4.2, rather than to whichever record was written last — the 198 excluded condition records "
    "named there are the visible trace of that safeguard, kept rather than deleted so the exclusion can be audited.",
    "Every query is now restricted to an explicit list of run_groups on the LT68 laptop, one list per experiment, identified in "
    "Section 4.2, rather than to whichever record was written last — the 462 excluded condition records named there are the "
    "visible trace of that safeguard, kept rather than deleted so the exclusion can be audited.")
sub_in_runs(P[560], "Both now read the same explicit run_group pair instead of re-deriving it.",
    "Both now read the same explicit run_group lists instead of re-deriving them.")
chk = [l for l in open(D + "instrument_check.txt") if l.startswith("{")]
def chk_row(prefix):
    for l in chk:
        j = json.loads(l)
        if j["load"].startswith(prefix): return j
    raise KeyError(prefix)
c1ms = chk_row("spin 1 ms"); two = chk_row("2 threads"); mem200 = chk_row("transient 200 MB"); sl = [json.loads(l) for l in chk if json.loads(l)["load"] == "sleep"]
expect(563, "The fifth is a value reported as measured")
NEW[563] = ("The fifth is a value reported as measured, but not measured — the most serious of the seven, since it entered the "
    "stored data rather than just its presentation, and its first remedy was itself defective. Processor utilization was "
    "sampled by a background thread on a five-millisecond period, and a region with no sample was stored as a literal one "
    "hundred per cent: 168 of 669 runs in the original campaign. The first remedy, on 27 August, withdrew those values and "
    "changed the harness to difference the process CPU-time counters across the measured region. Both halves proved "
    "insufficient. The sampler's failure was not only a matter of short regions: native simulator code that holds Python's "
    "global interpreter lock prevents the sampling thread from running at all, so a 0.48-second NEST simulation received no "
    "sample, 181 of the 501 remaining runs received fewer than a quarter of the samples their duration implies, and the samples "
    "that did arrive — each a difference of clock ticks over a few milliseconds — read anything up to 388,844 per cent. The "
    "counters used by the remedy advance in ten-millisecond ticks on Linux, so a region lasting about a millisecond reads either "
    "zero or around a thousand per cent; every one of the 291 regions shorter than 50 milliseconds in the September campaign has "
    "a CPU time that is an exact multiple of ten milliseconds. Neither campaign's utilization, and so neither campaign's energy "
    "proxy, was a measurement. Runtime was never affected — it is timed separately by a high-resolution clock — and neither were "
    "memory, spike counts or accuracy, although the memory sampler shared the same starved thread and could miss a short-lived "
    "peak. The instrument now reads the kernel's per-process CPU clock, which the scheduler keeps in nanoseconds for every "
    "thread of the process and which no thread has to be scheduled to observe, adds the processor time of child processes the "
    "region waits for, and reads peak memory from the kernel's high-water mark reset at the start of each region, so no "
    "sampling thread runs during a measurement at all. Before every campaign it is now checked against loads whose answer is "
    f"known: on this laptop it read {c1ms['C_current']['median']:.1f}% for a one-millisecond busy loop, where the original sampler "
    f"read a median of {c1ms['A_aug_sampler']['median']:.0f}% and a maximum of {c1ms['A_aug_sampler']['max']:,.0f}%; "
    f"{two['median_pct']:.0f}% for two threads outside the interpreter lock; and, measured alone as the benchmark uses it, "
    f"a median of {min(s['median_pct'] for s in sl):.1f}–{max(s['median_pct'] for s in sl):.1f}% while sleeping; and it registered {mem200['peak_above_start_mb']:.0f} MB of a 200 MB allocation that existed for a fraction of a "
    "second. "
    "Experiments 1 and 3 were then measured again under the identical protocol on 20 September; every inference and scalability "
    "figure in this chapter comes from that session, and every one of its 660 runs carries a utilization reading. The August "
    "campaign's utilization values were withdrawn from the database and its runtimes retained as a replication (Section 4.4). "
    "No run was deleted. The repair was only possible because Section 3.13 stores every individual run rather than a summary.")
claim(c1ms["C_current"]["median"] > 99 and c1ms["A_aug_sampler"]["median"] < 1 and c1ms["A_aug_sampler"]["max"] > 1000,
      "instrument check contrasts")
DEF6 = ("The sixth is of the same kind in a smaller place. The training path does not run the memory instrument, and it wrote "
    "a peak memory of 0.0 MB and a memory change of 0.0 MB into every training row as placeholders — 26 condition records and 29 "
    "runs in the results database. A zero is a value, not an absence, and a reader or a query cannot tell the two apart. The placeholders are now stored "
    "as missing, the harness writes missing rather than zero, and Section 4.6 states that training memory was not measured.")
DEF7 = ("The seventh was found while re-checking the interface against the tables for this revision. The harness stores training "
    "cost already divided per epoch, and the dashboard's training page divided it by the epoch count a second time, so every "
    "training cost it displayed was a third (fixed budget) or a tenth (full budget) of the figure in Table 4.4, and Nengo's "
    "single solve was shown at a third of its measured time. The thesis tables read the stored value directly and were never "
    "affected; the interface now does the same.")
expect(564, "The first four defects share a structure")
NEW[564] = ("The first four defects share a structure worth naming: the measurements were correct, the storage was correct, and "
    "the error crept in only where stored measurements were converted into a displayed figure or reported statistic. The fifth "
    "and sixth are the instructive counter-examples — there the storage itself was wrong, and no amount of care at the "
    "presentation layer could have saved it, since a benchmark reporting only aggregates has no way to expose a defect living "
    "in the aggregate; and the fifth shows that a remedy needs the same scrutiny as the defect, since the counter-based fix "
    "passed every check except the one that mattered, a test against a load whose answer is known. The seven safeguards adopted "
    "here — resolving duplicates at query time, restricting every query to explicitly listed run_groups, flagging incomparable "
    "rows at measurement time, asserting rather than silently degrading a statistical dependency, retaining every individual "
    "run, computing every figure in one shared layer used by both thesis and interface, and testing every instrument against "
    "known loads before it is trusted — stand as a contribution to benchmarking practice in their own right: each was adopted "
    "in response to a defect that had already produced a wrong figure.")

# ---- 4.9 --------------------------------------------------------------------
expect(569, "One row for each backend")
NEW[569] = ("One row for each backend. Every backend carries a measured energy value at all five sizes, so each coefficient "
    "is calculated over five points; with five points the smallest attainable exact p-value is 0.017.")
nb = [b for b in B if b.startswith("brian2")]
expect(574, "The proxy is monotonically increasing")
NEW[574] = (f"The proxy is monotonically increasing in the theoretical workload for {len(perfect)} of the eleven backends, at "
    "rho = +1.000 each: NEST's three thread counts, Nengo, snnTorch, SpikingJelly and both NumPy controls. The three Brian2 "
    f"targets are the exceptions: NumPy agrees strongly but not perfectly (rho = {sg(rho['brian2/numpy']['rho'])}, p = "
    f"{rho['brian2/numpy']['p']:.3f}), Cython weakly (rho = {sg(rho['brian2/cython']['rho'])}, p = {rho['brian2/cython']['p']:.3f}) "
    f"and the C++ standalone target not at all (rho = {sg(rho['brian2/cpp_standalone']['rho'])}, p = "
    f"{rho['brian2/cpp_standalone']['p']:.3f}), the expected result for a backend whose runtime does not scale with network size. "
    "That is the answer RQ2 asks for: the proxy is ordinal, and it does not invert the ordering of workloads for any backend "
    "whose runtime is driven by simulation rather than by fixed overhead or compilation, which is what a selection instrument "
    "needs. Its agreement is stronger than an earlier version of this section reported, because the utilisation values behind "
    "that version were partly noise. The accuracy of the joule values themselves is left to the physical comparison in Section 6.5.")
expect(575, "The second question is how much of the proxy")
NEW[575] = ("The second question is how much of the proxy is just runtime in other units. A regression of log energy on log "
    f"runtime for all {dec['n']} runs of the corrected session gives a slope of {dec['slope']:.3f}, R-squared = {dec['r2']:.3f}. The "
    f"formula's only other term, processor utilisation, has a median of {dec['u_med']:.1f}% over those runs, with the middle half "
    f"between {dec['u_q1']:.1f}% and {dec['u_q3']:.1f}% and a full range of {dec['u_min']:.1f}% to {dec['u_max']:,.1f}%; no reading "
    "is excluded.")
expect(576, "So the proxy is not just runtime")
NEW[576] = (f"So, with utilisation measured correctly, the proxy is mostly runtime in other units: runtime alone explains "
    f"{100 * dec['r2']:.0f}% of the variance in log energy. An earlier version of this section reported 42% and concluded that "
    "utilisation was doing substantial independent work; that conclusion was produced by the defective utilisation values, whose "
    "noise looked like independent information, and it is withdrawn. The remaining variance is real and sits largely where "
    "utilisation departs from one core — NEST's thread counts, Nengo's linear algebra from one thousand neurons upwards, "
    "SpikingJelly's mid-sized runs and Brian2's parallel compiler. For the six configurations that stay within ten per cent of "
    "one core at every size — Brian2's NumPy and Cython targets, NEST with one thread, snnTorch and both NumPy controls — the "
    "proxy is runtime multiplied by a near-constant and adds almost nothing to it.")
expect(577, "The third question changes the proxy's own constants")
NEW[577] = ("The third question changes the proxy's own constants: thermal design power was varied ±30% and the utilisation "
    "exponent between 0.8 and 1.2, and the ordering under each of the nine resulting combinations was compared, at N = 10,000 — "
    "the reference size of Experiment 4, where all eleven backends are ranked — to the ordering under the nominal constants by "
    f"Kendall's tau. Six of the nine give 1.000 agreement, the other three {f3(tau_sens_lo)}. Thermal design power has no effect "
    "at all — structurally, not just empirically, since it enters the formula as a constant multiplier and so cannot reorder "
    "anything. The only change comes from the utilisation exponent, and only at the top of its range, where the two closest "
    "backends in the nominal ordering, NEST with two threads and SpikingJelly, switch places. The ordering is therefore robust "
    "against large errors in these untestable constants, which is what makes the proxy usable for framework selection even "
    "without validated absolute values.")
expect(578, "In short, RQ2 is answered")
NEW[578] = ("In short, RQ2 is answered within its stated scope: the proxy maintains the ordering of workloads by theoretical "
    "cost for every backend whose runtime follows the workload, and that ordering is robust to substantial errors in its own "
    "parameters — the property a selection instrument needs, since a reader acts on the ordering rather than the joule value. "
    "On this hardware it adds information to runtime only where a framework uses more than one core, which is also where it "
    "matters most. What it does not do is measure joules, and no such claim is made anywhere in this thesis; the physical "
    "power-meter comparison that would make it quantitative is specified in Section 6.5.")

# ---- 4.10 -------------------------------------------------------------------
expect(591, "The first question is whether the ordering depends")
NEW[591] = ("The first question is whether the ordering depends on the size of the network on which it is measured. Using the "
    "ordering by median runtime at N=10 000 as a reference, the agreement at each smaller size is "
    f"tau={f3(tau['100'])} for N=100, tau={f3(tau['500'])} for N=500, tau={f3(tau['1000'])} for N=1 000, and "
    f"tau={f3(tau['5000'])} for N=5 000. The pattern is clear and it is the most important result in this chapter: at the three "
    "smallest sizes the ordering has little in common with the ordering at the largest, and it is weakest not at the smallest "
    "size but at N = 500; only at N = 5 000 does the ranking regain most of its agreement with the full sweep, and even there "
    "some of the ordered pairs still disagree. The low agreement at the small sizes appears in each of the four sessions that "
    f"measured the sweep, with agreement at N = 100 between {f3(min(within100))} and {f3(max(within100))} (Section 4.4). A benchmark that did not "
    "reach five thousand neurons would have published an ordering that shares only slightly more ordered pairs with the ordering "
    "at ten thousand than random chance.")
kd = [(b, K[b]["k"]) for b in kord]
expect(592, "The fitted exponents behind")
NEW[592] = ("The fitted exponents behind the metric comparison that follows come from the same session and are given here to "
    "check the rank correlation against them. Ordered by exponent: " +
    ", ".join(f"{LAB[b].replace('NumPy control / vectorized', 'the vectorized NumPy control').replace('NumPy control / scalar', 'the scalar NumPy control')} k = {sg(v)}" for b, v in kd[:-1]) +
    f" and {LAB[kd[-1][0]]} k = {sg(kd[-1][1])}. All three Brian2 backends are at the bottom of that ordering. Two of them, the "
    "NumPy and Cython targets, are also near the top of the runtime ordering at the reference size, and they supply most of what "
    f"agreement there is: without them the coefficient falls to {f3(tau_wo_fast_b2)}, while the compile-dominated target, flat "
    f"but slow, pulls it down (without it, {f3(tau_wo_cpp)}). Among the remaining backends the two orderings are essentially "
    "unrelated, since the two questions - how fast a configuration is, and how its cost grows - are genuinely different "
    "questions.")
claim(r10k["brian2/numpy"] <= 3 and r10k["brian2/cython"] <= 3, "two Brian2 targets near the top at N=10,000")
m10 = {b: M[b]["10000"] for b in B}
claim(sorted(fw_only, key=lambda b: m10[b])[:3] == sorted(["brian2/numpy", "brian2/cython", "brian2/cpp_standalone"], key=lambda b: m10[b]),
      "the three Brian2 targets are the smallest frameworks at N=10,000")
claim(max(B, key=lambda b: m10[b]) == "nengo/reference" and max(B, key=lambda b: T[b]["10000"]) == "nengo/reference", "Nengo slowest and largest at N=10,000")
expect(594, "The second question then is whether the ordering is dependent")
NEW[594] = ("The second question then is whether the ordering is dependent on the metric used. Ordering the same backends "
    "according to the energy proxy, using the ordering by runtime at the largest size as reference, we get "
    f"tau = {f3(tm['energy'])}, by peak memory tau = +{f3(tm['memory'])}, and by fitted scaling exponent tau = {f3(tm['exponent'])}. "
    "The energy result is the strongest of the three, and Section 4.9 explains why: with utilisation measured correctly, the "
    "proxy is largely runtime multiplied by a near-constant for most backends, so its ordering mostly repeats the runtime "
    "ordering; every pair it reorders involves NEST with two or four threads, whose extra cores do not buy proportionally "
    "shorter runs. "
    "Speed and memory economy are moderately associated rather than opposed: Brian2's simulating targets are both among the "
    "fastest and the most frugal at the largest network, and Nengo is both the slowest and the largest at N = 10 000. But the association is far from strong enough to predict one from the other, and Section 4.5 is the place to "
    "read the mechanism rather than the correlation coefficient.")
expect(595, "The scaling-exponent result is also important")
NEW[595] = ("The scaling-exponent result is also important, and less intuitive. The ordering by exponent is weakly associated "
    f"with the ordering by runtime at tau = {f3(tm['exponent'])} — the weakest of the three metric comparisons, and driven largely "
    "by Brian2's NumPy and Cython targets, which are both among the fastest and the flattest, rather than any general tendency "
    f"for fast configurations to scale flatly: without those two the coefficient is {f3(tau_wo_fast_b2)}. How fast a framework is at one network size still tells "
    "us little about how its cost grows as the network scales: Nengo is the clearest counter-example, fast enough at N = 100 to "
    "rank fifth on runtime yet the single steepest backend measured. These remain two largely independent questions, and a "
    "practitioner who answers the second by measuring the first has not approximated the answer — they have substituted a weakly "
    "related one.")
claim(r100["nengo/reference"] == 5, "Nengo fifth at N=100")
expect(597, "The third test directly examines Objective O2")
NEW[597] = ("The third test directly examines Objective O2, to estimate the rank correlation between the utilization-weighted "
    f"energy proxy and an EFLOP-based estimate. Across all 55 scalability conditions of the session, the Spearman’s rho between the two is "
    f"{f3(rp['rho'])} over {rp['n']} paired observations — strong positive agreement. An earlier version of this section gave "
    "0.716 over 50 observations; that figure no longer followed from the stored data after the August repair and rested on the "
    "defective utilisation values in any case, and it is replaced. But the coefficient alone masks what the comparison showed, "
    "and the more significant finding is structural, not numerical.")
expect(598, "The EFLOP metric provides exactly one value")
sub_in_runs(P[598], "the reported rank correlation of 0.716", f"the reported rank correlation of {f3(rp['rho'])}")

# ---- 4.11 -------------------------------------------------------------------
expect(601, "Section 4.10 answers RQ1 in full")
NEW[601] = ("Section 4.10 answers RQ1 in full. The five frameworks separate cleanly on every dimension measured in Sections "
    "4.3-4.7, but that separation is not one stable ordering: agreement with the reference ordering at N = 10 000 falls to "
    f"tau = {f3(tau['500'])} at N = 500 and recovers only to tau = {f3(tau['5000'])} by N = 5 000, low agreement at the small "
    "sizes appears in every one of four measurement sessions, and the ordering shifts again under an alternative ranking metric "
    f"(tau = {f3(tm['energy'])} against the energy proxy, +{f3(tm['memory'])} against peak memory, {f3(tm['exponent'])} against the "
    "fitted scaling exponent). RQ1 is answered on this single controlled platform in both the halves it asked for: how the "
    "frameworks compare, and whether that comparison holds under the network sizes and metrics a reader might choose.")
expect(602, "RQ2 asks how valid")
NEW[602] = ("RQ2 asks how valid a runtime-based energy proxy is against the EFLOP metric, by Spearman rank correlation. Section "
    f"4.10's third test gives Spearman's rho = {f3(rp['rho'])} across the {rp['n']} paired observations of the session. Because "
    "EFLOP is constant across frameworks at a fixed network size by construction, that correlation is driven by variation across "
    "sizes rather than across implementations. Per backend, the proxy follows the workload perfectly for every configuration "
    "whose runtime is driven by simulation, and its ordering of backends is preserved under substantial error in its own "
    "constants; with utilisation measured correctly it adds information to runtime only where a framework uses several cores. "
    "Its practical value is therefore ordinal, which is the property a framework-selection instrument needs, not the property a "
    "wattmeter would supply. Physical validation against measured power is specified as future work in Section 6.5.")

# ---- 4.12 / 4.13 --------------------------------------------------------------
expect(606, "Repeats within a condition are not strictly independent")
NEW[606] = ("Repeats within a condition are not strictly independent statistically. They run serially in one process, sharing "
    "cache state and thermal history, so the range measured is run-to-run variability in a session, not the full variability of "
    "the measurement; the variability between sessions was measured separately (Section 4.4) and is larger for absolute times, "
    "though not for orderings. Five is also a small sample size for normality and variance-homogeneity checks the pairwise "
    "comparisons in Section 4.3 depend on: one of eleven backends fails the Shapiro-Wilk test at this sample size, and the "
    "pairwise Welch tests are reported with that caveat attached rather than presented as unconditionally valid.")
expect(608, "The training results carry two more limitations")
append_run(P[608], " A third belongs with them: processor utilisation, peak memory and therefore the energy proxy were not "
    "observed during training, for the reason Section 4.6 gives, so Experiment 2 reports cost as time only.")
expect(611, "The chapter’s findings are as follows")
NEW[611] = ("The chapter’s findings are as follows. The speed ordering reverses across the range of network sizes a researcher "
    f"would reasonably use: Kendall's tau-b between the extremes is {f3(tau['100'])}, it falls as low as {f3(tau['500'])}, and the "
    f"low agreement between the extremes ({f3(min(within100))}–{f3(max(within100))}) appears in every one of four sessions while "
    "orderings re-measured at a fixed size agree closely. Some "
    "configurations scale their cost with the problem and others are dominated by fixed overhead; one Brian2 backend stays flat "
    "over a hundredfold change in problem size because what it measures is its own compiler, not the simulation. The ordering "
    "by scaling exponent does not depend on which size is reported, which is what lets it be read as a property of the "
    "frameworks rather than of the experiment, though it is only weakly related to speed at any one size. For backends where "
    "runtime tracks the workload, the energy proxy maintains the ordering of workloads by theoretical cost and is stable under "
    "substantial error in its own constants; with utilisation measured correctly it is largely runtime rescaled, and adds "
    "information only where a framework uses several cores. Along the way, twelve defects were found and corrected in the "
    "measuring and reporting instruments: five in the harness, three of which invalidate results reported in earlier drafts, "
    "and seven in the recording and reporting layer, two of which had entered the stored data — the more serious of them a "
    "processor-utilisation instrument whose first repair also failed, and whose replacement required Experiments 1 and 3 to be "
    "measured again.")

# ---- chapter 6 ------------------------------------------------------------------
expect(639, "The answers to all three research questions")
sub_in_runs(P[639], "The answer to RQ2 is an ordinal result: the proxy is valid against a theoretical cost metric, and its "
    "ordering is preserved under substantial error in its own constants, which is what framework selection requires.",
    "The answer to RQ2 is an ordinal result: the proxy is valid against a theoretical cost metric for every backend whose runtime "
    "follows the workload, and its ordering is preserved under substantial error in its own constants, which is what framework "
    "selection requires; with utilisation measured correctly it is, on this hardware, largely runtime rescaled except where a "
    "framework uses several cores.")
expect(642, "Seven contributions were realised")
sub_in_runs(P[642], "in one continuous campaign on one machine,", "on one machine, each experiment from one measurement session,")
sub_in_runs(P[642], "rank correlations in Section 4.10 give tau = 0.127 between the ordering at one thousand and ten thousand "
    "neurons, tau = +0.418 between the memory ordering and the runtime ordering, and tau = 0.273 between the scaling-exponent "
    "ordering and the runtime ordering.",
    f"rank correlations in Section 4.10 give tau = {f3(tau['500'])} between the ordering at five hundred and ten thousand neurons, "
    f"reproduced in four sessions, tau = +{f3(tm['memory'])} between the memory ordering and the runtime ordering, and "
    f"tau = {f3(tm['exponent'])} between the scaling-exponent ordering and the runtime ordering.")
expect(650, "A benchmark harness needs tests on more than one scale")
append_run(P[650], " The processor-utilisation instrument adds a third practice. It was wrong in two successive forms, and "
    "neither was caught by inspecting its output, which looked plausible; both were caught only by running it against loads "
    "whose answer is known — a busy loop, a sleep, two threads, a short-lived allocation. That check now runs before every "
    "campaign, and an instrument that has not passed it should not be trusted with a result.")
expect(653, "The fourth lesson is about the provenance")
sub_in_runs(P[653], "all queries are restricted to the two run_groups that form the single verified campaign. The 198 excluded "
    "condition records are retained and counted,",
    "all queries are restricted to explicitly listed run_groups, one list per experiment. The 462 excluded condition records are "
    "retained and counted,")
expect(656, "The study measures execution based on processors only")
append_run(P[656], " Training cost is reported as time only: utilisation, memory and energy were not observed during training "
    "(Section 4.6).")
expect(657, "The specific limit of the statistical treatment")
sub_in_runs(P[657], "four of eleven backends fail the Shapiro-Wilk test at this sample size, which limits how much weight the "
    "Holm-corrected pairwise Welch tests in Section 4.3 can bear for those backends specifically",
    "one of eleven backends fails the Shapiro-Wilk test at this sample size, which limits how much weight the Holm-corrected "
    "pairwise Welch tests in Section 4.3 can bear for that backend specifically")
append_run(P[657], " Variability between sessions was measured directly on four sessions (Section 4.4): it is larger than the "
    "within-session range for absolute times, especially for multi-threaded configurations, and small for orderings.")
expect(659, "The second limitation is in regards to thread parallelism")
sub_in_runs(P[659], "Processor utilization at the reference size ranges from about a twentieth of a core to just over three "
    "cores throughout the study,",
    f"Processor utilization ranges from one core to about eight at the reference size and up to "
    f"{max(U[b][n] for b in B for n in NS) / 100:.0f} cores across the sweep,")

# ---- appendices -------------------------------------------------------------
expect(774, "Artifact 2 - Measured benchmark dataset")
expect(806, "Table C.4")
NEW[806] = ("Table C.4  All fifty-five pairwise comparisons at the reference network size, sorted by the magnitude of Cohen's "
    "d. The p-values are Holm-corrected across all fifty-five comparisons; five pairs are not separated at the 0.05 level, for "
    "the reasons Section 4.3 sets out. A positive d means B is slower than A.")
expect(826, "This is equation (3.8) exactly")
NEW[826] = ("This is equation (3.8) exactly: energy is runtime multiplied by mean processor utilization as a fraction, "
    "multiplied by the platform’s thermal design power, and it returns nothing rather than a number when utilization was not "
    "measured. Utilization itself is the processor time the measured region consumed — every thread of the process and the "
    "child processes it waited for, read from the kernel's per-process CPU clock — divided by its wall time; the two earlier, "
    "defective ways of obtaining it are described in the fifth defect of Section 4.8.")

expect(235, "The main contribution is a measured result")
sub_in_runs(P[235], "a description of ten defects found in the measurement instruments — five in the harness and five in the "
    "recording and reporting layer —", "a description of twelve defects found in the measurement instruments — five in the "
    "harness and seven in the recording and reporting layer —")
expect(424, "Two limits are acknowledged upfront")
sub_in_runs(P[424], "and four of the eleven backends fail it outright.", "and one of the eleven backends fails it outright.")
expect(583, "(Calculated as Kendall's tau-b.")
NEW[583] = ("(Calculated as Kendall's tau-b. A bar at 1.0 is an ordering identical to the reference; in the three bars on the "
    f"left between {100 * (1 - max(tau[n] for n in NS[:3])) / 2:.0f} and {100 * (1 - min(tau[n] for n in NS[:3])) / 2:.0f} per "
    "cent of the ordered pairs are reversed relative to it.)")
expect(605, "The measurements are done on a single laptop")
sub_in_runs(P[605], "NEST now sees a small, real benefit from more threads at the largest network size, but that benefit is",
    "NEST sees a real benefit from a second thread at the largest network size and none from four, but that pattern is")
expect(652, "Pick a measurement platform")
sub_in_runs(P[652], "NEST’s modest but real benefit from additional threads at the largest network size is",
    "NEST’s real benefit from a second thread, and the absence of any from four, at the largest network size is")
expect(811, "This appendix holds the dataset behind Experiment 4")
sub_in_runs(P[811], "Every value derives from the same campaign as the rest of the thesis",
    "Every value derives from the CPU-corrected session that Chapter 4 reports for Experiments 1 and 3")
expect(522, "That near-order-of-magnitude split")
sub_in_runs(P[522], "is the cost of importing NumPy and PyTorch, not a property of the simulator",
    "reflects the process each backend is measured in — NEST's small worker process against the main benchmark process — "
    "not a property of the simulator")
for i, text in NEW.items():
    replace_whole(P[i], text)

# paragraphs with citation fields: targeted edits only
append_run(P[374], " As executed, the training path timed this cost in wall-clock time only; memory and processor utilization "
    "were not observed during training, a limitation reported in Section 4.6.")

# Artifact 2 description: counts
t774 = P[774].text
append_needed = "669 measured runs across 141 conditions" in t774
if append_needed:
    sub_in_runs(P[774], "669 measured runs across 141 conditions", "678 measured runs across 150 conditions")
    sub_in_runs(P[774], "198 condition records measured on other machines or during superseded, incomplete attempts at this "
        "same campaign", "462 condition records measured on other machines, during superseded, incomplete attempts at this same "
        "campaign, or in the replication sessions of Section 4.4")

# new paragraphs
new_para_after(P[509], REPRO)
p6 = new_para_after(P[563], DEF6)
new_para_after(p6, DEF7)

# ====================================================================== tables
TB = doc.tables
def lab(b): return LAB[b]
# Table 4.1
rows = []
for b in sorted(B, key=lambda b: inf[b]["med"]):
    r = inf[b]
    note = "control" if b in CTRL else ("compile-dominated" if b in CD else "-")
    rows.append([lab(b), ms(r["med"]), f"{ms(r['mn'])}–{ms(r['mx'])}", f"{r['cv']:.1f}", f"{r['rss']:.0f}",
                 f"{r['cpu']:.0f}", str(r["spikes"]), f"{100 * r['e'] / max(inf[z]['e'] for z in B if z not in CD):.1f}", note])
fill_table(TB[8], rows, header=[None, None, None, None, None, None, None,
                                "Energy index (costliest simulating backend = 100)", None])
# Table 4.2
rows = [[lab(t["b"]), f"{t['ratio']:.2f}×", f"{t['d']:+.2f} ({t['p']:.2e})", "yes" if t["sep"] else "no"] for t in F["t42"]]
fill_table(TB[9], rows, header=[None, "Median relative to NEST / 4 threads", None, None])
# Table 4.3 and C.1
rows = []
for b in kord:
    rows.append([lab(b)] + [f"{T[b][n]:.4f}" for n in NS] + [sg(K[b]["k"]), f"{K[b]['se']:.3f}", f"{K[b]['r2']:.3f}"])
fill_table(TB[10], rows); fill_table(TB[19], rows)
# Table 4.4 energy column note unchanged ("not measured"); verify
# Table 4.7
def reading(b):
    r = rho[b]["rho"]
    if b in CD: return "no relationship - compile-dominated (Section 4.7)"
    if abs(r - 1) < 1e-9: return "perfect rank agreement"
    if r >= 0.8: return "strong agreement"
    if r >= 0.5: return "moderate agreement, not significant (n = 5)"
    return "no reliable relationship"
order47 = [b for b in ["nengo/reference", "nest/threads1", "nest/threads2", "nest/threads4", "reference/scalar",
                       "reference/vectorised", "snntorch/cpu", "spikingjelly/cpu", "brian2/numpy", "brian2/cython",
                       "brian2/cpp_standalone"]]
rows = [[lab(b), sg(rho[b]["rho"]), f"{rho[b]['p']:.3f}", reading(b)] for b in order47]
fill_table(TB[14], rows)
# Table 4.8 and D.2
def rd(t):
    if t >= 0.8: return "ordering broadly holds, with movement"
    if t >= 0.5: return "partial agreement"
    if t >= 0.3: return "ordering only loosely related"
    return "ordering largely unrelated - the choice matters"
rows = [[f"Network size, N = {int(n):,}", "runtime ordering at N = 10,000", f3(tau[n]), rd(tau[n])] for n in NS[:-1]]
rows += [["Metric, energy proxy", "runtime ordering at N = 10,000", f3(tm["energy"]), rd(tm["energy"])],
         ["Metric, peak memory", "runtime ordering at N = 10,000", "+" + f3(tm["memory"]), rd(tm["memory"])],
         ["Metric, scaling exponent", "runtime ordering at N = 10,000", f3(tm["exponent"]), rd(tm["exponent"])]]
fill_table(TB[15], rows); fill_table(TB[24], rows)
# C.2 memory
rows = [[lab(b)] + [f"{M[b][n]:.1f}" for n in NS] for b in kord]
fill_table(TB[20], rows)
# C.3 spikes
sp = {}
for fw_bk, n, s in db1.execute("select framework||'/'||backend, network_size, spikes from conditions where task='scalability' and phase='simulate'"):
    sp[(fw_bk, str(n))] = s
rows = [[lab(b)] + [f"{sp[(b, n)]:,}" for n in NS] for b in kord]
fill_table(TB[21], rows)
# C.4 pairwise, sorted by |d|, d = (B - A)/sp with B the slower
runs_inf = {b: [r[0] for r in db1.execute("select runtime_s from runs where framework||'/'||backend=? and task='inference' and phase='simulate'", (b,))] for b in B}
rows = []
for p in C1["pairwise"]:
    a, b2 = p["a"], p["b"]
    if inf[a]["med"] > inf[b2]["med"]: a, b2 = b2, a
    xa, xb = runs_inf[a], runs_inf[b2]
    s = math.sqrt(((len(xa) - 1) * np.var(xa, ddof=1) + (len(xb) - 1) * np.var(xb, ddof=1)) / (len(xa) + len(xb) - 2))
    d = (np.mean(xb) - np.mean(xa)) / s
    rows.append((abs(d), [lab(a), lab(b2), f"{inf[b2]['med'] / inf[a]['med']:.2f}×", f"{d:+.2f}", f"{p['p_holm']:.2e}",
                          "yes" if p["p_holm"] < 0.05 else "no"]))
rows.sort(key=lambda z: -z[0])
fill_table(TB[22], [r for _, r in rows])
# D.1 ranks
rows = []
for n in NS:
    for i, b in enumerate(sorted(B, key=lambda b: T[b][n]), 1):
        rows.append([f"{int(n):,}", str(i), lab(b), f"{T[b][n]:.4f}"])
fill_table(TB[23], rows)
# Table 3.x instruments
t3 = TB[3]
for r in t3.rows[1:]:
    c0 = r.cells[0].text
    if c0.startswith("Dependent: peak memory"):
        set_cell(r.cells[3], "kernel high-water mark (VmHWM), reset at the start of each measured interval")
    if c0.startswith("Dependent: processor utilization"):
        set_cell(r.cells[1], "Processor time consumed over the measured interval by every thread of the process and its "
                 "waited-for child processes, divided by wall time (can exceed 100% for threaded execution)")
        set_cell(r.cells[3], "kernel per-process CPU clock (CLOCK_PROCESS_CPUTIME_ID) plus getrusage for child processes")
t7 = TB[7]
for r in t7.rows[1:]:
    if r.cells[0].text.strip() == "psutil":
        set_cell(r.cells[2], "baseline resident memory; utilisation and peak memory are read from the kernel (Section 4.8)")

# Tables 4.4 and 4.5: an earlier revision wrote its cells at the default size;
# bring every run to the size the original rows use (8 pt)
for ti in (11, 12):
    for row in TB[ti].rows[1:]:
        for c in row.cells:
            for para in c.paragraphs:
                for r in para.runs:
                    if r.font.size is None:
                        r.font.size = 101600
# ================================================================= figures
IMG = {37: "fig-4-1.png", 38: "fig-4-2.png", 39: "fig-4-3.png", 40: "fig-4-4.png", 41: "fig-4-5.png",
       42: "fig-4-6.png", 43: "fig-4-7.png", 44: "fig-4-8.png"}
FIGDIR = "/root/work/cpu/figs/figs/"
import os
from PIL import Image as _PI
def swap_image(rid, path):
    if not os.path.exists(path):
        sys.exit("ABORT: missing image " + path)
    doc.part.related_parts[rid]._blob = open(path, "rb").read()
    w, h = _PI.open(path).size
    # keep the printed width, set the height from the new image's aspect ratio
    for blip in doc.element.body.iter(qn('a:blip')):
        if blip.get(qn('r:embed')) != rid:
            continue
        inline = blip
        while inline is not None and inline.tag not in (qn('wp:inline'), qn('wp:anchor')):
            inline = inline.getparent()
        ext = inline.find(qn('wp:extent'))
        cx = int(ext.get('cx')); cy = int(round(cx * h / w))
        ext.set('cy', str(cy))
        for aext in inline.iter(qn('a:ext')):
            if aext.get('cx') is not None:
                aext.set('cx', str(cx)); aext.set('cy', str(cy))
for rid_n, fn in IMG.items():
    swap_image(f"rId{rid_n}", FIGDIR + fn)
for rid_n, fn in {51: "fig-5-1.png", 52: "fig-5-2.png", 53: "fig-5-3.png", 47: "code-e3.png"}.items():
    swap_image(f"rId{rid_n}", "/root/work/cpu/figs/" + fn)

for i in (485, 498, 504, 511, 517, 572, 582, 588, 621, 625, 628, 824):
    for r in P[i].runs:
        hl(r)
doc.save(DST)
print("saved", DST, "paragraphs replaced:", len(NEW))
