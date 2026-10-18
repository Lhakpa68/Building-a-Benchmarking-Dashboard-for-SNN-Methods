# De-duplication pass on the thesis

The thesis text (already rewritten into plainer sentences) is in /root/rw/full_rewritten.txt, one paragraph
per line as "[id] text", grouped under "##### <section heading>". The same data is in
/root/rw/full_rewritten.json (fields i, section, text). Section headings: /root/rw/headings.json.

The author's request: "Make sure none of the contents are repeated. If same explanation actions are to be made,
just mention section number under which that particular content has been explained in detail so that it will
minimize the repetition."

## What to do
1. Read the WHOLE thesis first. Build a map of topics that are explained more than once, and decide each
   topic's home: the one section where it is explained in full (usually the first full treatment, or the
   section whose title is about it). Typical candidates (check, do not assume):
   the single-machine/single-platform rationale; why Brian2's C++ standalone target is compile-dominated;
   the processor-utilisation defect and its fix; why EFLOP cannot discriminate between simulators at a fixed
   size; why accuracy is not comparable across learning rules / cost is the comparable quantity; the fixed vs
   full training budget; the missing homeostatic mechanisms of the STDP rules; the 25 ms presentation window;
   the statistical limits of five runs; run_group / provenance restrictions; why training energy was not
   measured; the between-session reproducibility result; what the dashboard does.
2. Everywhere else, cut the repeated EXPLANATION and replace it with a short pointer, e.g. "(Section 4.7)" or
   "for the reasons given in Section 4.8". Keep the paragraph's own point and flow intact; rewrite the
   surrounding sentence so it still reads naturally.
3. What may stay outside the home section: the result itself stated briefly (one clause, with the key
   number if the paragraph needs it), plus the pointer. This matters for the Abstract, Chapter 1's
   contributions, chapter overviews and summaries (3.16, 4.1, 4.13, 5.5), the RQ answers (4.11) and
   Chapter 6: these are expected to restate findings, but they must not re-explain mechanisms, reasons or
   method details. Shorten them to the finding plus a section reference.
4. Do not remove anything that appears ONLY in the paragraph you are editing. Every fact must survive
   somewhere. Keep citations: every ⟦Cn:[..]⟧ token in a paragraph must remain in that paragraph (you may move
   it within the paragraph). Keep all hedges and limitations at their home.
5. Chapter 2 (literature) and Chapter 3 (design) explain what will be done; Chapter 4 reports what happened.
   A design statement in Chapter 3 and its result in Chapter 4 are not duplicates. Only merge when the same
   explanation is given twice.
6. Keep the plain style: short sentences, no em dashes, simulator (not framework) for the five tools.
   Do not add new facts.

## Output
Write /root/rw/dedup/edits.json: a list of {"i": id, "text": "<new paragraph text>", "home": ["4.7", ...],
"note": "<what was cut and where it lives>"} for ONLY the paragraphs you change. "home" lists the section
number(s) the pointer refers to (use [] if you only trimmed internal repetition within the paragraph).
Then run `python3 /root/rw/dedup/check_dedup.py` and fix every error. The checker requires that any number
you remove from a paragraph is actually stated in the home section(s) you name; if it is not, either keep the
number or name the correct home. Iterate until it prints NO ERRORS.

Finally write /root/rw/dedup/topic_map.md: one line per repeated topic -> home section -> paragraphs trimmed.
Report back briefly: number of paragraphs edited, characters removed, and anything you were unsure about.
