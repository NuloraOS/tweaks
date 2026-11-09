"""Retain only current generated DEBs in GitHub Code, preserving prior files in git history."""
import pathlib
import subprocess
current = {str(file.relative_to('public')).replace('\\','/') for file in pathlib.Path('public/debs').glob('*.deb')}
tracked = subprocess.check_output(['git','ls-files','*.deb'],text=True).splitlines()
owned = ('com.theipos.camera_', 'com.theipos.o2camera_', 'com.theipos.dock_', 'com.theipos.motion_', 'com.theipos.glass_')
retired = [file for file in tracked if pathlib.PurePosixPath(file).name.startswith(owned) and file not in current]
if retired:
    subprocess.run(['git','rm','--cached','--',*retired],check=True)
subprocess.run(['git','add','--',*sorted(current),'Packages','Packages.gz','Packages.bz2','Release','CydiaIcon.png','.nojekyll'],check=True)
