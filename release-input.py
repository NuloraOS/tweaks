"""Stage our verified build directly, without depending on another Pages deployment."""
import hashlib, json, os, pathlib, subprocess, urllib.request

root = pathlib.Path('.verified-release')
root.mkdir(exist_ok=True)
api = 'https://api.github.com/repos/NuloraOS/TheIpOS/'
def request(url, limit, authenticated=False):
    headers = {'User-Agent': 'Nelora APT publisher'}
    if authenticated and os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=90) as response:
        data = response.read(limit + 1)
    assert len(data) <= limit, 'Response too large'
    return data

jobs = json.loads(request(api + 'actions/runs/42793848639/jobs?filter=latest', 1024*1024, True))['jobs']
for name in ('packages', 'interface'):
    assert any(j['name'] == name and j['conclusion'] == 'success' for j in jobs), name
release = json.loads(request(api + 'releases/tags/v0.4.4', 1024*1024, True))
expected = {'com.theipos.camera': '0.4.4', 'com.theipos.o2camera': '0.4.4', 'com.theipos.dock': '0.4.3'}
blocks = []
for package, version in expected.items():
    name = package + '_' + version + '_iphoneos-arm.deb'
    assets = [a for a in release['assets'] if a['name'] == name]
    assert len(assets) == 1, name
    asset = assets[0]
    data = request(asset['browser_download_url'], 64*1024*1024)
    checksum = hashlib.sha256(data).hexdigest()
    assert len(data) == asset['size'] and data.startswith(b'!<arch>\n')
    if asset.get('digest'):
        assert asset['digest'] == 'sha256:' + checksum, 'Release asset digest mismatch'
    target = root / name
    target.write_bytes(data)
    block = subprocess.check_output(['dpkg-deb', '--field', str(target)], text=True).strip()
    fields = dict(line.split(': ', 1) for line in block.splitlines() if ': ' in line and not line.startswith(' '))
    assert fields['Package'] == package and fields['Version'] == version and fields['Architecture'] == 'iphoneos-arm'
    block = '\n'.join(line for line in block.splitlines() if not line.startswith(('Filename:', 'Size:', 'SHA256:', 'Icon:')))
    block += f'\nFilename: ./{name}\nSize: {len(data)}\nSHA256: {checksum}\nIcon: https://nuloraos.github.io/tweaks/icon-{package.rsplit(".",1)[-1]}.png'
    blocks.append(block)
(root / 'Packages').write_text('\n\n'.join(blocks) + '\n\n', encoding='utf8')
print('PASS: verified camera 0.4.4, O2 camera 0.4.4 and Dock 0.4.3 release inputs')
