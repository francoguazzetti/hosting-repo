"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os, sys
path = '/home/francoguazzetti/hosting-repo'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DEBUG'] = '0'
os.environ['SECRET_KEY'] = '0^q*n-&jjslxh(iu64y705spyj$01&@g#oowdxuseu--by+1u1'
os.environ['ALLOWED_HOSTS'] = 'francoguazzetti.pythonanywhere.com'
os.environ['CSRF_TRUSTED_ORIGINS'] = 'https://francoguazzetti.pythonanywhere.com'
os.environ['DATABASE_URL'] = 'sqlite:////home/francoguazzetti/hosting-repo/db.sqlite3'

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
