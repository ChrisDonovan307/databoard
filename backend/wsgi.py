import sys
import os
import site

# Paths
base_dir = '/users/c/d/cdonov12/www-root/databoard'
venv_dir = os.path.join(base_dir, 'venv')
site_packages = os.path.join(
    venv_dir, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages'
)

# Add the virtual environment's site-packages
site.addsitedir(site_packages)

# Add the app directory
sys.path.insert(0, base_dir)

# Import the Dash app
from app import app as dash_app

# Expose Flask server
application = dash_app.server
