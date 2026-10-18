# Rewrite brief: master's thesis "Building a Benchmarking Dashboard for SNN Comparison"

Author: Lhakpa Tshering (Master of ICT Research, MIT). The thesis benchmarks five spiking-neural-network
simulators (Brian2, NEST, Nengo, snnTorch, SpikingJelly) plus a plain-NumPy control, and presents a dashboard.

## Your job
Rewrite every paragraph in your batch so it reads like a careful human academic wrote it. The author asked for:
"more of human tone. Limit complex sentences but make sure the flow, fluency, content quality and information
meaning shouldn't be affected. Try limit long complex sentences and try to make bit short."

So:
- Split long sentences. Aim for about 15-25 words per sentence; almost none above 35 words. Vary length naturally.
- Make each paragraph somewhat shorter (roughly 10-25% fewer words) by removing filler, repetition,
  throat-clearing and inflated phrasing. Never by dropping information.
- Keep EVERY fact, number, claim, qualification, limitation, comparison, cross-reference ("Section 4.8",
  "Table 4.1", "equation (3.8)") and citation. Keep the logical links between sentences (because, so, but).
  Hedges that carry meaning ("not measured", "within noise", "not significant") must stay.
- Do not add any fact, number, example, citation or claim that is not in the original.
- Keep academic register (this is a thesis, not a blog). Plain words over fancy ones. Prefer active voice.
  Keep first person only where the original already uses it.
- Avoid AI-sounding patterns: "serves as", "underscores", "highlights", "crucial", "pivotal", "key" (adjective),
  "landscape", "delve", "not X but Y" constructions, stacked "-ing" clauses, rhetorical punchlines, groups of
  three for effect, "It is worth noting", "In essence".
- Do NOT use em dashes (—). Use a full stop, comma, colon or parentheses instead. An en dash inside a numeric
  range (e.g. 81–85, 4.3-4.7) is fine; keep ranges exactly as written.
- Keep each paragraph as one paragraph (same id). Do not merge or split paragraphs.
- British/Australian vs US spelling: keep whatever the original paragraph uses.

## Terminology change (the author approved this)
Call Brian2, NEST, Nengo, snnTorch and SpikingJelly "simulators", not "frameworks": "the five simulators",
"simulator/backend pair", "simulator selection", "simulator-independent", "cross-simulator". Adjust grammar
(a/an) accordingly. KEEP the word "framework" only where it is not about these five tools:
proper names ("Neural Engineering Framework"), another author's named framework or reporting framework,
general ML frameworks such as PyTorch, or "conceptual framework". Research questions and objectives in
Chapter 1 also switch to "simulators".

## Hard constraints (checked automatically)
1. Citation tokens look like ⟦C3:[41]⟧. Copy each one EXACTLY, character for character, once each, placed
   where the citation belongs in your new sentence. Never invent, merge or drop one.
2. Every number written in digits must appear the same number of times in your version (e.g. "0.782",
   "4.8", "60,000", "10 000", "3.5", "2026"). Do not convert digits to words or words to digits, do not
   round, do not reformat ("10 000" stays "10 000"). Numbers written as words may stay as words.
3. No paragraph may end up longer than the original.

## Output
Write a JSON list to /root/rw/out/<batch>.json: [{"i": <same id>, "text": "<rewritten paragraph>"}, ...]
covering every paragraph in the batch, in the same order. Then run:
    python3 /root/rw/check.py <batch>
Fix everything it reports as an error (id mismatch, citation tokens, numbers, em dashes, length). For each
"framework kept" note, make sure the use is one of the allowed exceptions; otherwise change it. Re-run until
it prints NO HARD ERRORS (framework notes that are genuine exceptions are acceptable). Also re-read your text
once against the original to confirm no meaning changed.

Finish with a 2-3 line summary: batch name, the checker's final sentence-length line, and any paragraph you
were unsure about.
