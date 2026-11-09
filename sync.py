import bz2
import gzip
import hashlib
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
records = []
descriptions = {
    'camera': 'Камера с удержанием горизонта, записью видео и белым / жёлтым экранным светом.',
    'o2camera': 'Отдельная камера для ролика: оранжевые элементы, круговой зум, ручные параметры. Реальная основная запись 1080p/30; надписи 4K/60 — демонстрационные.',
    'dock': 'Закруглённая панель с пятью местами для приложений. Радиус и прозрачность — в настройках.',
    'motion': 'Размытие движения в поддерживаемых анимациях UIKit. Сила эффекта — в настройках.',
    'glass': 'Стеклянное оформление совместимых панелей и фона строки времени и батареи.'
}
for block in index.split('\n\n'):
    p = dict(line.split(': ', 1) for line in block.splitlines() if ': ' in line and not line.startswith(' '))
    if not p.get('Package'):
        continue
    if p['Package'] not in {'com.theipos.camera','com.theipos.o2camera','com.theipos.dock'}:
        continue
    path = p['Filename'].removeprefix('./')
    if not re.fullmatch(r'[A-Za-z0-9_./+\-]+', path) or '..' in path.split('/') or path.startswith('/'):
        raise ValueError('Invalid package path')
    data = fetch(path, 64*1024*1024)
    if len(data) != int(p['Size']) or hashlib.sha256(data).hexdigest() != p['SHA256']:
        raise ValueError('DEB integrity mismatch')
    filename = pathlib.PurePosixPath(path).name
    (out / 'debs').mkdir(exist_ok=True)
    (pathlib.Path('debs')).mkdir(exist_ok=True)
    (out / 'debs' / filename).write_bytes(data)
    shutil.copyfile(out / 'debs' / filename, pathlib.Path('debs') / filename)
    block = re.sub(r'^Filename: .+$', 'Filename: ./debs/' + filename, block, flags=re.M)
    block = re.sub(r'^Section: .+$', 'Section: Tweaks', block, flags=re.M)
    if not re.search(r'^Section:', block, re.M):
        block += '\nSection: Tweaks'
    records.append(block.strip())
    kind = p['Package'].rsplit('.', 1)[-1]
    icon = 'icon-' + kind + '.png'
    (out / icon).write_bytes(fetch('Icons/nelora-' + kind + '.png'))
if len(records) != 3:
    raise ValueError('Expected two cameras and Dock; keep the previous source if builds are incomplete')
index = ('\n\n'.join(records) + '\n\n').encode('utf8')
(out / 'Packages').write_bytes(index)
(out / 'Packages.gz').write_bytes(gzip.compress(index, mtime=0))
(out / 'Packages.bz2').write_bytes(bz2.compress(index))
release = 'Origin: Nelora\nLabel: Nelora\nSuite: stable\nVersion: 1.0\nCodename: nelora\nArchitectures: iphoneos-arm\nComponents: main\nDescription: All tweaks in one source\n'
for field, algorithm in [('MD5Sum', 'md5'), ('SHA1', 'sha1'), ('SHA256', 'sha256'), ('SHA512', 'sha512')]:
    release += field + ':\n'
    for name in ['Packages', 'Packages.gz', 'Packages.bz2']:
        data = (out / name).read_bytes()
        release += f' {hashlib.new(algorithm, data).hexdigest()} {len(data)} {name}\n'
(out / 'Release').write_text(release, encoding='utf8')
(out / 'CydiaIcon.png').write_bytes(fetch('CydiaIcon.png'))
(out / '.nojekyll').touch()
for name in ['Packages', 'Packages.gz', 'Packages.bz2', 'Release', 'CydiaIcon.png', '.nojekyll']:
    shutil.copyfile(out / name, name)
print('PASS: two cameras and Dock in debs/, valid APT metadata, no website')
