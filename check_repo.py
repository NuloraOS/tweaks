"""Check the published file contract used by Sileo RepoManager, not HTTP status alone."""
import bz2
import gzip
import hashlib
import pathlib

root = pathlib.Path('public')
raw = (root / 'Release').read_bytes()
assert not raw.startswith(b'\xef\xbb\xbf') and b'\r' not in raw, 'Release must be UTF-8 without BOM and LF terminated'
text = raw.decode('utf8')
fields, key = {}, None
for line in text.splitlines():
    if line.startswith((' ', '\t')):
        assert key is not None
        fields[key] += '\n' + line.strip()
    else:
        key, value = line.split(':', 1)
        key = key.lower()
        fields[key] = value.strip()

def sileo_contract(values):
    # RepoManager rejects a successfully downloaded Release if components is absent.
    assert 'components' in values and values['components'], 'Sileo: Could not parse release file (Components missing)'
    assert 'iphoneos-arm' in values['architectures'].split(), 'Wrong architecture for rootful Chimera'

sileo_contract(fields)
old = dict(fields)
del old['components']
try:
    sileo_contract(old)
except AssertionError:
    pass
else:
    raise AssertionError('Regression check failed to reject the old broken Release')
plain = (root / 'Packages').read_bytes()
assert gzip.decompress((root / 'Packages.gz').read_bytes()) == plain
assert bz2.decompress((root / 'Packages.bz2').read_bytes()) == plain
for field, algorithm in [('md5sum', 'md5'), ('sha1', 'sha1'), ('sha256', 'sha256'), ('sha512', 'sha512')]:
    for row in fields[field].splitlines():
        if not row:
            continue
        checksum, size, filename = row.split()
        data = (root / filename).read_bytes()
        assert len(data) == int(size) and hashlib.new(algorithm, data).hexdigest() == checksum
packages = plain.decode('utf8').strip().split('\n\n')
assert len(packages) == 3
for block in packages:
    values = dict(line.split(': ', 1) for line in block.splitlines() if ': ' in line and not line.startswith(' '))
    assert values['Section'] == 'Tweaks'
    assert values['Filename'].startswith('./debs/')
    assert values['Package'] in {'com.theipos.camera','com.theipos.o2camera','com.theipos.dock'}
    data = (root / values['Filename'].removeprefix('./')).read_bytes()
    assert hashlib.sha256(data).hexdigest() == values['SHA256']
print('PASS Sileo Release fields + missing-Components regression + all index hashes + two cameras and Dock + one category')
assert not (root / 'index.html').exists(), 'No website requested'
