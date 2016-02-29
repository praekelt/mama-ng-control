FROM praekeltfoundation/django-bootstrap
ENV DJANGO_SETTINGS_MODULE "mama_ng_control.settings"
# No collectstatic to do
CMD ["mama_ng_control.wsgi:application"]
