"""Usage: python3 /root/rw/check.py <batch_k>
Validates out/<batch>.json against batches/<batch>.json."""
import json, re, sys, collections
k=sys.argv[1]
src={x['i']:x['text'] for x in json.load(open(f'/root/rw/batches/{k}.json'))}
out={x['i']:x['text'] for x in json.load(open(f'/root/rw/out/{k}.json'))}
NUM=re.compile(r'\d+(?:[.,]\d+)*')
CIT=re.compile(r'⟦C\d+:[^⟧]*⟧')
errs=[]
if set(src)!=set(out): errs.append(f'paragraph ids differ: missing {sorted(set(src)-set(out))} extra {sorted(set(out)-set(src))}')
for i in src:
    if i not in out: continue
    a,b=src[i],out[i]
    ca,cb=collections.Counter(CIT.findall(a)),collections.Counter(CIT.findall(b))
    if ca!=cb: errs.append(f'[{i}] citation tokens changed: missing {list((ca-cb).elements())} extra {list((cb-ca).elements())}')
    na=collections.Counter(NUM.findall(CIT.sub('',a))); nb=collections.Counter(NUM.findall(CIT.sub('',b)))
    if na!=nb: errs.append(f'[{i}] numbers changed: missing {list((na-nb).elements())} extra {list((nb-na).elements())}')
    if '—' in b: errs.append(f'[{i}] contains an em dash')
    if re.search(r'\bframeworks?\b', b, re.I):
        for m in re.finditer(r'.{0,40}\bframeworks?\b.{0,40}', b, re.I):
            errs.append(f'[{i}] note, "framework" kept (fine only for proper names / other authors\' or ML frameworks): ...{m.group(0)}...')
    if len(b) > 1.05*len(a): errs.append(f'[{i}] longer than the original ({len(b)} vs {len(a)} chars)')
sent=lambda t:[s for s in re.split(r'(?<=[.!?])\s+(?=[A-Z(])', CIT.sub('C',t)) if s.strip()]
la=[len(s.split()) for t in src.values() for s in sent(t)]; lb=[len(s.split()) for i in out for s in sent(out[i])]
print(f'avg sentence words: original {sum(la)/len(la):.1f} -> new {sum(lb)/max(1,len(lb)):.1f}; sentences over 35 words: {sum(x>35 for x in la)} -> {sum(x>35 for x in lb)}')
print(f'total chars {sum(map(len,src.values()))} -> {sum(len(out[i]) for i in out)}')
print('\n'.join(errs) if errs else 'NO HARD ERRORS')
