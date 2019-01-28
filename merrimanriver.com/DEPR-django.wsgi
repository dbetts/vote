import os
import sys
sys.path.append('/home/merriman/merrimanriver.com')
sys.path.append('/home/merriman/django_apps')

os.environ['DJANGO_SETTINGS_MODULE'] = 'source.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()