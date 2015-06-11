from django.conf.urls import include, url
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('mama_ng_control.apps.web.urls')),
    url(r'^subscriptions/', include('mama_ng_control.apps.subscriptions.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
