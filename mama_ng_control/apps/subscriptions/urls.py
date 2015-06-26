from django.conf.urls import url, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'subscriptions', views.SubscriptionViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browseable API.
urlpatterns = [
    url(r'^', include(router.urls)),
    url('^subscriptions/(?P<subscription_id>.+)/send$',
        views.SubscriptionSend.as_view()),
]
