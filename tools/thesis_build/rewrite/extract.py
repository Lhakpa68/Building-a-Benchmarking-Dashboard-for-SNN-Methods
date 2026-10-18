import docx, json, re
from docx.oxml.ns import qn
d=docx.Document('src.docx'); P=d.paragraphs
rng=list(range(79,87))+list(range(217,673))+list(range(773,834))
CAP=re.compile(r'^(Figure|Table)\s+[A-Z0-9]+\.\d+')
SKIP_MIXED={86,408,415,418,420}
items=[]; chap=None; capt=[]
for i in rng:
    p=P[i]
    if p.style.name.startswith('Heading 1'):
        if p.text.strip(): chap=p.text.strip()
        continue
    if i<217: chap='ABSTRACT'
    if not p.text.strip() or p.style.name.startswith('Heading'): continue
    if p._p.findall('.//'+qn('w:drawing')): continue
    if CAP.match(p.text.strip()) or re.match(r'^E\.\d', p.text.strip()) or i in SKIP_MIXED:
        capt.append(i); continue
    segs=[]; k=0
    for ch in p._p:
        tag=ch.tag.split('}')[1]
        if tag=='r':
            segs.append(''.join(t.text or '' for t in ch.iter(qn('w:t'))))
        elif tag=='hyperlink':
            k+=1; txt=''.join(t.text or '' for t in ch.iter(qn('w:t')))
            segs.append(f'⟦C{k}:{txt}⟧')
    text=''.join(segs)
    items.append(dict(i=i, chapter=chap, text=text))
json.dump(items,open('items.json','w'),ensure_ascii=False,indent=0)
json.dump(capt,open('captions.json','w'))
import collections
c=collections.Counter(x['chapter'] for x in items); print(c, len(items), 'captions/skip', len(capt))
print(sum(len(x['text']) for x in items), 'chars')
print(items[5]['text'][:400])
