"""Genera index.html a partir de template.html + data.json.  Uso: python3 render.py data.json template.html index.html"""
import sys, json
data, tpl, out = sys.argv[1:4]
d = json.load(open(data))
html = open(tpl).read().replace('__DATA__', json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
open(out, 'w').write(html)
print('ok', out, len(html))
