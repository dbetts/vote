#!/usr/bin/python3

import os
import sys

sys.path.append('/home/merriman/merrimanriver.com')
sys.path.append('/home/merriman/django_apps')

os.environ['DJANGO_SETTINGS_MODULE'] = 'source.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
