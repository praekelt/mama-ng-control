from django.conf.urls import url, include
from rest_framework import routers
# import views

router = routers.DefaultRouter()
# router.register(r'url', views.ModelNameViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browseable API.
urlpatterns = [
    url(r'^', include(router.urls)),
]
