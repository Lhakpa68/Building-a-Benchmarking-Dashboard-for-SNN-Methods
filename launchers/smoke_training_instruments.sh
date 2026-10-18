#!/usr/bin/env bash
# Proves the 21 September training instrumentation before a multi-day campaign
# is committed to it. Tiny budget: hidden 100, 300 train, 100 test, 2 epochs.
#
# It checks four things a defect would break:
#   1. the processor clock still passes its own self-test;
#   2. every training-capable backend now reports utilisation and peak memory;
#   3. NEST's figures survive the subprocess boundary, and rise with threads;
#   4. Brian2's figures survive checkpoint/resume - the run is deliberately
#      chopped into 20-second chunks so the accumulators are saved and
#      restored many times, and the utilisation must still be plausible.
set -u
WIN_DIR="/mnt/d/MIT College/Last Edition/SNN Simulator Benchmark - Final"
OUT="$WIN_DIR/instrument_smoke_output"
PROJ="$HOME/snn_smoke_instruments"
PY="$HOME/projects/snn_benchmark_dashboard.backup_20260805_224202/.venv/bin/python3.11"
LOG="$OUT/smoke.log"

mkdir -p "$OUT" "$PROJ/results"
rm -f "$OUT/FINISHED.txt" "$OUT/FAILED.txt" "$OUT/RESULT.txt" 2>/dev/null
exec > >(tee "$LOG") 2>&1
fail() { echo "FAILED: $*"; echo "$*" > "$OUT/FAILED.txt"; sleep 20; exit 1; }

echo "=== training-instrument smoke test ==="
echo "started $(date -Is)"
[ -x "$PY" ] || fail "interpreter not found at $PY"
if pgrep -f "python[0-9.]* run\.py bench" >/dev/null 2>&1; then
  fail "another benchmark is running - stop it first"
fi

rm -rf "$PROJ/snnbench" "$PROJ/tools"
cp -f "$WIN_DIR/run.py" "$WIN_DIR/RUN_ME.py" "$PROJ/"
( cd "$WIN_DIR" && tar --exclude=__pycache__ -cf - snnbench tools ) | ( cd "$PROJ" && tar -xf - )
[ -f "$PROJ/results/mnist_784.npz" ] || cp -f "$WIN_DIR/results/mnist_784.npz" "$PROJ/results/"
cd "$PROJ" || fail "cannot enter $PROJ"
export SNN_RESULTS_DIR="$PROJ/results"
DB="$PROJ/results/benchmarks.db"
rm -f "$DB" "$PROJ/results/ckpt_"*.pkl 2>/dev/null

echo; echo "--- 1. processor-clock self-test ---"
"$PY" tools/cpu_instrument_check.py | tee "$OUT/instrument_check.txt"
grep -q "^SELFTEST PASS" "$OUT/instrument_check.txt" || fail "self-test did not pass"

S="--tasks training --preset smoke"
echo; echo "--- 2. the three fast simulators ---"
"$PY" run.py bench $S --only nengo        || fail "nengo training"
"$PY" run.py bench $S --only snntorch     || fail "snntorch training"
"$PY" run.py bench $S --only spikingjelly || fail "spikingjelly training"

echo; echo "--- 3. NEST, across the subprocess boundary, all thread counts ---"
for t in 1 2 4; do
  "$PY" run.py bench $S --only nest --backends threads$t || fail "nest threads$t training"
done

echo; echo "--- 4. Brian2, deliberately chopped into 20 s chunks ---"
for be in cython numpy cpp_standalone; do
  echo "  == brian2/$be"
  n=0
  while [ $n -lt 400 ]; do
    n=$((n+1))
    SNNBENCH_TRAIN_DEADLINE=$(( $(date +%s) + 20 )) \
      "$PY" run.py bench $S --only brian2 --backends $be
    got=$("$PY" - "$DB" "$be" <<'PYX'
import sqlite3, sys
try:
    c = sqlite3.connect(sys.argv[1])
    print(c.execute("SELECT COUNT(*) FROM conditions WHERE task='training' AND "
                    "framework='brian2' AND backend=?", (sys.argv[2],)).fetchone()[0])
except Exception:
    print(0)
PYX
)
    [ "${got:-0}" -gt 0 ] && { echo "     finished after $n chunk(s)"; break; }
  done
  [ "${got:-0}" -gt 0 ] || fail "brian2/$be never completed"
done

echo; echo "--- 5. what was recorded ---"
"$PY" - "$DB" <<'PYX' | tee "$OUT/RESULT.txt"
import sqlite3, sys, re
c = sqlite3.connect(sys.argv[1]); c.row_factory = sqlite3.Row
rows = c.execute("SELECT * FROM conditions WHERE task='training' "
                 "ORDER BY framework, backend").fetchall()
print(f"{'backend':<26}{'s/epoch':>10}{'CPU %':>9}{'peak MB':>10}{'energy J':>11}"
      f"{'acc %':>8}   cpu_s/wall_s")
bad = []
for r in rows:
    n = r['notes'] or ''
    cs = re.search(r'util_cpu_s=([\d.]+)', n)
    ws = re.search(r'util_wall_s=([\d.]+)', n)
    name = f"{r['framework']}/{r['backend']}"
    cpu = r['cpu_pct']; mem = r['peak_rss_mb']; en = r['energy_median_j']
    print(f"{name:<26}{r['runtime_median_s']:>10.2f}"
          f"{(f'{cpu:.1f}' if cpu is not None else 'MISSING'):>9}"
          f"{(f'{mem:.0f}' if mem is not None else 'MISSING'):>10}"
          f"{(f'{en:.3f}' if en is not None else 'MISSING'):>11}"
          f"{r['accuracy_pct']:>8.2f}   "
          f"{cs.group(1) if cs else '-'}/{ws.group(1) if ws else '-'}")
    if cpu is None: bad.append(f"{name}: no utilisation")
    if mem is None: bad.append(f"{name}: no peak memory")
    if en  is None: bad.append(f"{name}: no energy proxy")
    if cpu is not None and not (10.0 <= cpu <= 3300.0):
        bad.append(f"{name}: utilisation {cpu:.1f}% is outside 10-3300%")
    if mem is not None and mem < 20:
        bad.append(f"{name}: peak memory {mem:.0f} MB is implausibly small")

got = {f"{r['framework']}/{r['backend']}": r for r in rows}
need = ["nengo/reference", "snntorch/cpu", "spikingjelly/cpu",
        "nest/threads1", "nest/threads2", "nest/threads4",
        "brian2/cython", "brian2/numpy", "brian2/cpp_standalone"]
for k in need:
    if k not in got: bad.append(f"{k}: no training row at all")

# NEST should use more of the machine with more threads.
try:
    u1 = got["nest/threads1"]["cpu_pct"]; u4 = got["nest/threads4"]["cpu_pct"]
    if u1 and u4 and u4 <= u1 * 1.2:
        bad.append(f"NEST utilisation did not rise with threads: "
                   f"1 thread {u1:.0f}%, 4 threads {u4:.0f}%")
except Exception:
    pass

print()
if bad:
    print("PROBLEMS FOUND:")
    for b in bad: print("  -", b)
    sys.exit(1)
print("SMOKE TEST PASS: every training row carries utilisation, peak memory "
      "and an energy proxy, and the figures are plausible.")
PYX
rc=${PIPESTATUS[0]}
cp -f "$DB" "$OUT/smoke_benchmarks.db" 2>/dev/null
if [ "$rc" != 0 ]; then fail "the recorded values did not pass their checks (see RESULT.txt)"; fi
date -Is > "$OUT/FINISHED.txt"
echo; echo "finished $(date -Is)"
echo "DONE - you can close this window."
sleep 10
