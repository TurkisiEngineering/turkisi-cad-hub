import json,sys
d=json.load(open(sys.argv[1]))
print(d['result'], d.get('error'))
for c in d['checks']: print(('OK ' if c['ok'] else 'XX '), c['label'], '' if c['ok'] else str(c['value'])[:400])
for n in d['notes']: print('note', n[:400])
