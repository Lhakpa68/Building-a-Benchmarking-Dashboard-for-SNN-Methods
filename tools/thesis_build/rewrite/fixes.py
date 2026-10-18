import json
full = {x['i']: x for x in json.load(open('/root/rw/full_rewritten.json'))}
ed = {e['i']: e for e in json.load(open('/root/rw/dedup/edits.json'))}
cur = {i: (ed[i]['text'] if i in ed else x['text']) for i, x in full.items()}
FIX = [
 (235, "across ten execution backends", "across eleven execution backends"),
 (235, "all ten executable backends", "all eleven executable backends"),
 (443, "ten execution backends need", "eleven execution backends need"),
 (645, "five simulators and ten executable backends", "five simulators and eleven executable backends"),
 (555, "The harness isolates each NEST training attempt in a disposable subprocess, for the reason given in Section 3.9, and caps the number of attempts.",
       "The harness runs each NEST training attempt in a disposable subprocess, because NEST 3.10.0 crashed the whole process after a small number of kernel resets on this machine. It also caps the number of attempts."),
 (409, "F(10, 17.29) = 2541.69 across k = 11 backends gives eta-squared = 0.9995",
       "F(10, 17.22) = 1898.78 across k = 11 backends gives eta-squared = 0.9986"),
 (385, "The backend yields a slightly negative exponent with a high coefficient of determination: an apparently well-fitted result saying the workload gets cheaper as it grows, which no simulator does (Section 4.7).",
       "The backend yields an exponent indistinguishable from zero: its runtime does not respond to a hundredfold change in network size, which no simulator's workload does (Section 4.7)."),
 (331, "We also perform every measurement in a single continuous campaign on one machine, so no comparison crosses a hardware or software change.",
       "We also take every comparison from one measurement session on one machine, so no comparison crosses a hardware or software change."),
 (453, "and the whole campaign runs in one continuous session on one machine (Section 3.3).",
       "and every comparison is drawn from one measurement session on one machine (Section 4.2)."),
 (660, "The statistical limits stated in Section 3.10 apply: repeats within a condition are not independent draws, five retained runs is a small sample, and one of eleven backends fails the Shapiro-Wilk test. This limits how much weight the Holm-corrected pairwise Welch tests in Section 4.3 can bear for that backend specifically.",
       "The statistical limits set out in Sections 3.10 and 4.12 apply. They bear most on the Holm-corrected pairwise Welch tests in Section 4.3 for the one backend that fails the Shapiro-Wilk test."),
 (660, "Variability between sessions was measured directly on four sessions (Section 4.4). It is larger than the within-session range for absolute times, especially for multi-threaded configurations, and small for orderings.",
       "Variability between sessions is reported in Section 4.4."),
 (651, "Section 6.4 states the work to remove it, and Section 6.5 records the bound.",
       "Section 6.4 records the limits they leave, and Section 6.5 the work that would remove them."),
 (649, "the equivalence check confirms that the simulators produce statistically indistinguishable spiking output on the same specification before any timing is compared",
       "the equivalence check confirms that the simulators produce matching firing rates on the same specification before any timing is compared (Section 6.4)"),
 (667, "ten times the data moved the plasticity rules by about one percentage point without reaching chance",
       "ten times the data moved the plasticity rules by 0.82 to 2.21 percentage points, and none exceeded chance (Section 4.6)"),
 (666, "is adding two further adapters to the harness to test whether the pattern found here generalizes to GeNN, Lava and BindsNET.",
       "is adding adapters for GeNN, Lava and BindsNET to the harness, to test whether the pattern found here generalizes to them."),
 (276, "Two recent papers change the standards", "Three recent papers change the standards"),
 (633, "All six experiment pages and the overview were exercised against the full backend set during verification. The simulator selector was confirmed to change every chart, table and result line on the page it touches, with zero console errors across all eight routes.",
       "All six experiment pages, the overview, the ranked all-simulators page and the about page were exercised against the full backend set during verification. The simulator selector was confirmed to change every chart, table and result line on the page it touches, with zero console errors across all nine routes."),
 (634, "Its usefulness depends on the question asked of it. For verifying this thesis's own results, it is.",
       "Its usefulness depends on the question asked of it. For verifying this thesis's own results, it is useful."),
 (783, "instead of being re-specified four times", "instead of being re-specified five times"),
]
for i, a, b in FIX:
    assert cur[i].count(a) == 1, (i, a[:50], cur[i].count(a))
    cur[i] = cur[i].replace(a, b)
json.dump({str(k): v for k, v in cur.items()}, open('/root/rw/final_text.json', 'w'), ensure_ascii=False)
print("fixes applied", len(FIX))
