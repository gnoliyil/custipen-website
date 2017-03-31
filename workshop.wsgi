import sys
import os
sys.path.insert(0,"/var/www/custipen-website")

# Activate your virtual env
activate_env=os.path.expanduser("/var/www/custipen-website/venv/bin/activate_this.py")
execfile(activate_env, dict(__file__=activate_env))

from workshop import app as application



