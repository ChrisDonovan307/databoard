import sys
import os
import site

base_dir = '/users/c/d/cdonov12/www-root/databoard'
venv_dir = os.path.join(base_dir, 'backend', '.venv')
site_packages = os.path.join(
    venv_dir, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages'
)

site.addsitedir(site_packages)
sys.path.insert(0, base_dir)

from backend.api import app

application = app
