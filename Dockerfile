FROM praekeltfoundation/django-bootstrap
ENV DJANGO_SETTINGS_MODULE "mama_ng_control.settings"
CMD ["mama_ng_control.wsgi:application"]
