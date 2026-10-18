"""python3 /root/rw/dedup/check_dedup.py  -- validates /root/rw/dedup/edits.json"""
import json, re, collections
full = json.load(open('/root/rw/full_rewritten.json'))
cur = {x['i']: x for x in full}
heads = json.load(open('/root/rw/headings.json'))
secnums = {h.split()[0] for h in heads if re.match(r'^\d+\.\d+', h)}
edits = json.load(open('/root/rw/dedup/edits.json'))
NUM = re.compile(r'\d+(?:[.,]\d+)*'); CIT = re.compile(r'⟦C\d+:[^⟧]*⟧')
def sec_text(ref):
    return ' '.join(x['text'] for x in full if x['section'] and x['section'].split()[0] == ref)
errs = []; seen = set(); removed_chars = 0
for e in edits:
    i = e['i']
    if i in seen: errs.append(f'[{i}] edited twice'); continue
    seen.add(i)
    if i not in cur: errs.append(f'[{i}] unknown paragraph id'); continue
    a, b = cur[i]['text'], e['text']
    removed_chars += len(a) - len(b)
    if collections.Counter(CIT.findall(a)) != collections.Counter(CIT.findall(b)):
        errs.append(f'[{i}] citation tokens changed')
    if '—' in b: errs.append(f'[{i}] em dash')
    if len(b) > len(a): errs.append(f'[{i}] longer than before')
    for ref in re.findall(r'Sections? (\d+\.\d+)', b):
        if ref not in secnums: errs.append(f'[{i}] refers to Section {ref}, which does not exist')
    homes = e.get('home', [])
    homes = [homes] if isinstance(homes, str) else homes
    for h in homes:
        if h not in secnums: errs.append(f'[{i}] home "{h}" is not a section number')
        elif cur[i]['section'] and cur[i]['section'].split()[0] == h:
            errs.append(f'[{i}] home {h} is the paragraph\'s own section')
    na = collections.Counter(NUM.findall(CIT.sub('', a))); nb = collections.Counter(NUM.findall(CIT.sub('', b)))
    extra = nb - na
    for n in extra.elements():
        if not re.fullmatch(r'\d+\.\d+', n) or n not in secnums:
            errs.append(f'[{i}] new number "{n}" (only section numbers may be added)')
    hometext = ' '.join(sec_text(h) for h in homes if h in secnums)
    for n in (na - nb).elements():
        if n not in hometext:
            errs.append(f'[{i}] removed number "{n}" is not stated in home section(s) {homes}')
print(f'{len(edits)} paragraphs edited, {removed_chars} characters removed')
print('\n'.join(errs) if errs else 'NO ERRORS')
