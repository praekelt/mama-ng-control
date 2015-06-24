from django.conf.urls import include, url
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('mama_ng_control.apps.web.urls')),
    url(r'^api/v1/', include('mama_ng_control.apps.subscriptions.urls')),
    url(r'^api/v1/', include('mama_ng_control.apps.contacts.urls')),
    url(r'^api/v1/messages/', include('mama_ng_control.apps.vumimessages.urls')),
    url(r'^api-auth/',
        include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api-token-auth/',
        'rest_framework.authtoken.views.obtain_auth_token'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
