release: python manage.py check --deploy --fail-level WARNING && python manage.py migrate --noinput
web: gunicorn config.wsgi:application --access-logfile -
