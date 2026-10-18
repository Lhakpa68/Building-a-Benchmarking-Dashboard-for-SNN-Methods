"""Swap fig-5-1..3 into the thesis, keeping display width and fixing the height to the new aspect."""
import sys
from docx import Document
from docx.oxml.ns import qn
from PIL import Image

SRC, DST = sys.argv[1], sys.argv[2]
NEW = {'rId51': '/root/work/cpu/figs/fig-5-1.png',
       'rId52': '/root/work/cpu/figs/fig-5-2.png',
       'rId53': '/root/work/cpu/figs/fig-5-3.png'}
d = Document(SRC)
part = d.part
for rid, path in NEW.items():
    img = part.rels[rid].target_part
    data = open(path, 'rb').read()
    img._blob = data
    img.blob  # noqa
    # python-docx ImagePart stores the blob on _blob
    w, h = Image.open(path).size
    for p in d.paragraphs:
        for blip in p._p.findall('.//' + qn('a:blip')):
            if blip.get(qn('r:embed')) != rid:
                continue
            drawing = blip.getparent()
            while drawing is not None and drawing.tag != qn('w:drawing'):
                drawing = drawing.getparent()
            ext = drawing.find('.//' + qn('wp:extent'))
            cx = int(ext.get('cx'))
            cy = int(round(cx * h / w))
            ext.set('cy', str(cy))
            aext = drawing.find('.//' + qn('a:ext'))
            if aext is not None:
                aext.set('cx', str(cx)); aext.set('cy', str(cy))
            print(rid, path.split('/')[-1], f'{w}x{h}', 'cx', cx, 'cy', cy)
d.save(DST)
print('saved', DST)
