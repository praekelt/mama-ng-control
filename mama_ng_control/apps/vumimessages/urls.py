from django.conf.urls import url, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'outbound', views.OutboundViewSet)
router.register(r'inbound', views.InboundViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browseable API.
urlpatterns = [
    url('^events$',
        views.EventListener.as_view()),
    url(r'^', include(router.urls)),
]
