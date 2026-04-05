import sys
import os
import site

site.addsitedir(os.path.expanduser('~/.local/lib/python3.12/site-packages'))

sys.path.insert(0, os.path.dirname(__file__))

from app import app as application

