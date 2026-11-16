"""Build atlas-tree/data.js from GGG's atlastree-export.

Usage: python -I build_data.py <export_dir> <out_dir>
Copies the sprite sheets it needs into <out_dir>/assets and writes
<out_dir>/data.js (window.ATLAS = {normal:{...}, ruthless:{...}}).
Each node gets a content category ("cat") so the viewer can hide content types.
"""
import json, math, os, re, shutil, sys, collections

SRC, OUT = sys.argv[1], sys.argv[2]
ZOOM = '0.5'

A16 = [0,30,45,60,90,120,135,150,180,210,225,240,270,300,315,330]
A40 = [0,10,20,30,40,45,50,60,70,80,90,100,110,120,130,135,140,150,160,170,180,
       190,200,210,220,225,230,240,250,260,270,280,290,300,310,315,320,330,340,350]

# (category, regex over name+stats). First match wins, so order = most specific first.
KEYWORDS = [
    ('Threads',              r'\bThreads?\b'),
    ('The Maven',            r'\bMaven\b'),
    ('Essence',              r'\bEssences?\b'),
    ('Abyss',                r'\bAbyss|Abysses'),
    ('Incursion',            r'Incursion|\bAlva\b|Temple|Architect'),
    ('Rogue Exiles',         r'Rogue Exile'),
    ('Atlas Anomalies',      r'Anomal'),
    ('Viridian Wildwood',    r'Wildwood|Wisp|Azmeri'),
    ('Bestiary',             r'\bBeasts?\b|Einhar|Bestiary'),
    ('Beyond',               r'\bBeyond\b'),
    ('Blight',               r'Blight|\bOils?\b'),
    ('Breach',               r'Breach'),
    ('The Searing Exarch',   r'Searing Exarch'),
    ('The Eater of Worlds',  r'Eater of Worlds'),
    ('Conquerors',           r'Conqueror|Sirus|Citadel'),
    ('Delirium',             r'Delirium|Simulacr'),
    ('Divination Cards',     r'Divination|Stacked Deck|Scrying'),
    ('Shrines',              r'Shrine'),
    ('The Shaper and Elder', r'Shaper|\bElder\b|Guardians?\b'),
    ('Expedition',           r'Expedition|Logbook|Explosive|Excavat'),
    ('Mercenaries',          r'Mercenar'),
    ('Gold',                 r'\bGold'),
    ('Sacred Flora',         r'Harvest|Sacred Grove|Lifeforce|\bCrops?\b|Sacred Flora'),
    ('Betrayal',             r'Syndicate|Betrayal|Veiled|\bJun\b'),
    ('Labyrinth',            r'Labyrinth|Ascendan'),
    ('Legion',               r'Legion|Timeless'),
    ('Atlas Memories',       r'Memor'),
    ('Mirage',               r'Mirage'),
    ('Ritual',               r'Ritual|Tribute'),
    ('Sentinels',            r'Sentinel'),
    ('Settlers of Kalguur',  r'Kalguur|\bOre\b'),
    ('Strongboxes',          r'Strongbox'),
    ('Synthesis',            r'Synthes'),
    ('Torment',              r'Tormented|Possess'),
    ('Ultimatum',            r'Ultimatum|Trialmaster|\bRuin\b'),
    ('Unique Monsters',      r'Unique Monster'),
    ('Magic Monsters',       r'Magic Monster'),
    ('Rare Monsters',        r'Rare Monster|Mirrored'),
]
# icon-file prefix -> category, used when no keyword matched
ICONS = [
    ('Alva','Incursion'),('Anarchy','Rogue Exiles'),('AtlasAnomalies','Atlas Anomalies'),
    ('EagonKeystone','Atlas Anomalies'),('AtlasDivination','Divination Cards'),('ScryingOrb','Divination Cards'),
    ('AtlasGold','Gold'),('AtlasHarvest','Sacred Flora'),('AtlasMagicmonsters','Magic Monsters'),
    ('AtlasMemories','Atlas Memories'),('AtlasUniquemonsters','Unique Monsters'),('AzmeriForest','Viridian Wildwood'),
    ('Bestiary','Bestiary'),('Beyond','Beyond'),('Blight','Blight'),('CassiasPride','Blight'),
    ('Conqueror','Conquerors'),('Delirium','Delirium'),('ElderShaper','The Shaper and Elder'),
    ('Essence','Essence'),('Expedition','Expedition'),('ExtremeArchaeology','Expedition'),
    ('Harvest','Sacred Flora'),('Jun','Betrayal'),('Kalguur','Settlers of Kalguur'),('Legion','Legion'),
    ('RuptureMeter','Legion'),('Mapn','Maps'),('Merc','Mercenaries'),('Mirage','Mirage'),('NewBreach','Breach'),
    ('RareMonsters','Rare Monsters'),('Ritual','Ritual'),('ArbitraryTenets','Ritual'),('Sentinel','Sentinels'),
    ('Shrines','Shrines'),('GreedShrine','Shrines'),('Strongbox','Strongboxes'),('Synthesis','Synthesis'),
    ('TheCleansingFire','The Searing Exarch'),('WrathOfTheCosmos','The Searing Exarch'),
    ('TheTangle','The Eater of Worlds'),('EldritchGaze','The Eater of Worlds'),('Torment','Torment'),
    ('SpeakeroftheDead','Torment'),('Ultimatum','Ultimatum'),('RuinousWager','Ultimatum'),
    ('GruelingGauntlet','Ultimatum'),('Abyss','Abyss'),('Ascendancy','Labyrinth'),('TheMaven','The Maven'),
    ('AtlasThreads','Threads'),('ThreadNode','Threads'),('Wheelof','Threads'),
]
# mastery icon suffix -> category (masteries are labels for a cluster)
MASTERY = {'Abyss':'Abyss','Alva':'Incursion','Anarchy':'Rogue Exiles','Anomalies':'Atlas Anomalies',
    'AzmeriForest':'Viridian Wildwood','Bestiary':'Bestiary','Beyond':'Beyond','Blight':'Blight','Breach':'Breach',
    'CleansingFire':'The Searing Exarch','Conqueror':'Conquerors','Delirium':'Delirium','Divination':'Divination Cards',
    'Domination':'Shrines','ElderShaper':'The Shaper and Elder','Essence':'Essence','Expedition':'Expedition',
    'Gold':'Gold','Harvest':'Sacred Flora','Jun':'Betrayal','Labyrinth':'Labyrinth','Legion':'Legion',
    'MagicMonsters':'Magic Monsters','Map':'Maps','Memories':'Atlas Memories','Mercenaries':'Mercenaries',
    'Mirage':'Mirage','RareMonsters':'Rare Monsters','Ritual':'Ritual','Sentinek':'Sentinels',
    'Settlers':'Settlers of Kalguur','Strongbox':'Strongboxes','Synthesis':'Synthesis','Tangle':'The Eater of Worlds',
    'Thread':'Threads','Torment':'Torment','Ultimatum':'Ultimatum','UniqueMonsters':'Unique Monsters'}

KW = [(c, re.compile(r)) for c, r in KEYWORDS]
# extra hints only used for the options of "Select a type of content" nodes
VARIANT_KW = [('Beyond', re.compile(r'Demonic Evocator')), ('Essence', re.compile(r'Imprisoned Monster'))]

def clean(s):  # "[Thread|Threads]" -> "Threads", "[Thread]" -> "Thread"
    return re.sub(r'\[([^\]|]*)\|?([^\]]*)\]', lambda m: m.group(2) or m.group(1), s)

def categorise(n):
    if n.get('isWormhole'):
        return 'Gateways'
    icon = n['icon'].split('/')[-1][:-4]
    if n.get('isMastery'):
        return MASTERY.get(icon.replace('AtlasPassiveMastery', ''), 'General')
    icat = next((c for p, c in ICONS if icon.startswith(p)), None)
    name = clean(n.get('name', ''))
    stats = clean(' '.join(n.get('stats', [])))
    if re.search(r'Select a type of content', stats):
        return 'General'
    # 1) name keyword, 2) stats keywords (icon breaks ties), 3) icon, 4) variants all agreeing
    for c, rx in KW:
        if rx.search(name):
            return c
    hits = [c for c, rx in KW if rx.search(stats)]
    if hits:
        return icat if icat in hits else hits[0]
    if icat:
        return icat
    vc = {next((c for c, rx in KW if rx.search(clean(' '.join(e['stats'])))), None)
          for e in n.get('variantEffects', [])}
    if len(vc) == 1 and None not in vc:
        return vc.pop()
    return 'General'

def build(path):
    d = json.load(open(path, encoding='utf-8'))
    C = d['constants']; R = C['orbitRadii']; K = C['skillsPerOrbit']
    G = d['groups']
    nodes, root_out = {}, []
    for nid, n in d['nodes'].items():
        if nid == 'root':
            root_out = n['out']; continue
        g = G[str(n['group'])]
        o, i, k = n['orbit'], n['orbitIndex'], K[n['orbit']]
        a = math.radians(A16[i] if k == 16 else A40[i] if k == 40 else 360 * i / k)
        x, y = g['x'] + R[o] * math.sin(a), g['y'] - R[o] * math.cos(a)
        t = ('mastery' if n.get('isMastery') else 'wormhole' if n.get('isWormhole') else
             'keystone' if n.get('isKeystone') else 'notable' if n.get('isNotable') else
             'start' if not n['name'] else 'normal')
        e = {'id': nid, 'n': n['name'], 't': t, 'x': round(x, 1), 'y': round(y, 1), 'a': round(a, 5),
             'g': n['group'], 'o': o, 'ic': n['icon'], 'cat': categorise(n) if t != 'start' else 'Start',
             's': [clean(s) for s in n.get('stats', [])], 'out': n['out'], 'in': n['in']}
        if t in ('normal', 'notable', 'keystone'):
            txt = clean(' '.join([n['name']] + n.get('stats', []) + [s for v in n.get('variantEffects', []) for s in v['stats']]))
            also = [c for c, rx in KW if rx.search(txt) and c != e['cat']]
            if also and 'Select a type of content' not in txt: e['also'] = also
        if n.get('reminderText'): e['r'] = [clean(s) for s in n['reminderText']]
        if n.get('flavourText'): e['f'] = n['flavourText']
        if n.get('variantEffects'): e['v'] = [[clean(s) for s in v['stats']] for v in n['variantEffects']]
        if n.get('variantEffects'):
            base = e['s']
            select = any('Select a type of content' in b for b in base)
            def full(opt):
                # "...Shrines to be of type" + "Covetous Shrine" -> one sentence; full-sentence options stand alone
                if select or not base: return opt
                if len(' '.join(opt).split()) > 5: return base + opt
                o = ' '.join(opt)
                return [b + (': ' if re.search(r'certain \w+$', b) else ' ') + o for b in '\n'.join(base).split('\n')]
            e['vt'] = [full(v) for v in e['v']]
            # content-choice nodes file each option under its own content type; other choices stay with the node
            e['vc'] = [next((c for c, rx in VARIANT_KW + KW if rx.search(' '.join(v))), e['cat']) if select else e['cat']
                       for v in e['v']]
        if n.get('connections'): e['arc'] = {c['to']: [c['orbit'], c.get('orbitX'), c.get('orbitY')] for c in n['connections']}
        nodes[nid] = e
    groups = {k: {'x': g['x'], 'y': g['y'], 'bg': g.get('background')} for k, g in G.items()}
    sprites = {}
    for name, levels in d['sprites'].items():
        z = levels.get(ZOOM) or levels.get('1')
        scale = float(ZOOM) if ZOOM in levels else 1.0
        sprites[name] = {'file': z['filename'].split('/')[-1].split('?')[0], 'scale': scale, 'w': z['w'], 'h': z['h'], 'coords': z['coords']}
    return {'nodes': nodes, 'groups': groups, 'root': root_out, 'radii': R, 'sprites': sprites,
            'points': d['points'], 'bounds': [d['min_x'], d['min_y'], d['max_x'], d['max_y']]}

out = {'normal': build(os.path.join(SRC, 'data.json')), 'ruthless': build(os.path.join(SRC, 'ruthless.json'))}

os.makedirs(os.path.join(OUT, 'assets'), exist_ok=True)
files = {s['file'] for t in out.values() for s in t['sprites'].values()}
for f in files:
    shutil.copy(os.path.join(SRC, 'assets', f), os.path.join(OUT, 'assets', f))
with open(os.path.join(OUT, 'data.js'), 'w', encoding='utf-8') as fh:
    fh.write('window.ATLAS=' + json.dumps(out, separators=(',', ':'), ensure_ascii=False) + ';\n')

# report
cnt = collections.Counter(n['cat'] for n in out['normal']['nodes'].values())
print(sorted(cnt.items()))
print('files', sorted(files))
if len(sys.argv) > 3:
    for n in out['normal']['nodes'].values():
        if n['t'] in ('notable', 'keystone') or n['cat'] == 'General':
            print(f"{n['cat']:22} {n['t']:8} {n['n'][:28]:28} :: {' | '.join(n['s'] or (n.get('v') or [['']])[0])[:90]}")
