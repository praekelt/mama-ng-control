from django.contrib import admin

from .models import Outbound, Inbound
# Register your models here.
admin.site.register(Outbound)
admin.site.register(Inbound)
