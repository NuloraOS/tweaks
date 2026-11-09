import bz2
import gzip
import hashlib
import html
import pathlib
import re
import shutil
import urllib.request

BASE = 'https://koziavkamurz-wq.github.io/Nelora/'
out = pathlib.Path('public')
out.mkdir(exist_ok=True)
def fetch(name, limit=2*1024*1024):
    with urllib.request.urlopen(BASE + name, timeout=90) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Response too large')
    return data

index = fetch('Packages').decode('utf8')
records, cards = [], []
descriptions = {
    'camera': 'Камера с удержанием горизонта, записью видео и белым / жёлтым экранным светом.',
    'dock': 'Закруглённая панель с пятью местами для приложений. Радиус и прозрачность — в настройках.',
    'motion': 'Размытие движения в поддерживаемых анимациях UIKit. Сила эффекта — в настройках.',
    'glass': 'Стеклянное оформление совместимых панелей и фона строки времени и батареи.'
}
for block in index.split('\n\n'):
    p = dict(line.split(': ', 1) for line in block.splitlines() if ': ' in line and not line.startswith(' '))
    if not p.get('Package'):
        continue
    path = p['Filename'].removeprefix('./')
    if not re.fullmatch(r'[A-Za-z0-9_./+\-]+', path) or '..' in path.split('/') or path.startswith('/'):
        raise ValueError('Invalid package path')
    data = fetch(path, 64*1024*1024)
    if len(data) != int(p['Size']) or hashlib.sha256(data).hexdigest() != p['SHA256']:
        raise ValueError('DEB integrity mismatch')
    filename = pathlib.PurePosixPath(path).name
    (out / filename).write_bytes(data)
    # One flat folder on GitHub and one APT category in Sileo.
    shutil.copyfile(out / filename, filename)
    block = re.sub(r'^Filename: .+$', 'Filename: ./' + filename, block, flags=re.M)
    block = re.sub(r'^Section: .+$', 'Section: Tweaks', block, flags=re.M)
    if not re.search(r'^Section:', block, re.M):
        block += '\nSection: Tweaks'
    records.append(block.strip())
    kind = p['Package'].rsplit('.', 1)[-1]
    icon = 'icon-' + kind + '.png'
    (out / icon).write_bytes(fetch('Icons/nelora-' + kind + '.png'))
    name, version, description = html.escape(p['Name']), html.escape(p['Version']), html.escape(descriptions.get(kind, p.get('Description', '')))
    cards.append(f'<article><img src="{icon}" alt="" width="56" height="56"><div><h2>{name}</h2><small>{version} · iOS 12 / Chimera</small><p>{description}</p></div><a class="download" href="{html.escape(filename)}" download>Скачать DEB</a></article>')
if len(records) != 4:
    raise ValueError('Expected four published packages')
index = ('\n\n'.join(records) + '\n\n').encode('utf8')
(out / 'Packages').write_bytes(index)
(out / 'Packages.gz').write_bytes(gzip.compress(index, mtime=0))
(out / 'Packages.bz2').write_bytes(bz2.compress(index))
release = 'Origin: Nelora\nLabel: Nelora\nArchitectures: iphoneos-arm\nDescription: All tweaks in one source\nSHA256:\n'
for name in ['Packages', 'Packages.gz', 'Packages.bz2']:
    data = (out / name).read_bytes()
    release += f' {hashlib.sha256(data).hexdigest()} {len(data)} {name}\n'
(out / 'Release').write_text(release, encoding='utf8')
(out / 'CydiaIcon.png').write_bytes(fetch('CydiaIcon.png'))
(out / '.nojekyll').touch()
page = pathlib.Path('page.html').read_text(encoding='utf8').replace('__CARDS__', ''.join(cards))
(out / 'index.html').write_text(page, encoding='utf8')
for name in ['Packages', 'Packages.gz', 'Packages.bz2', 'Release', 'CydiaIcon.png', 'index.html', '.nojekyll']:
    shutil.copyfile(out / name, name)
print('PASS: four verified DEBs, one page, one APT category, flat file layout')
