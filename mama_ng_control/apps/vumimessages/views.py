from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Subscription
from .serializers import SubscriptionSerializer


class SubscriptionViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows Subscription models to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    filter_fields = ('contact', 'messageset_id', 'lang', 'active', 'completed',
                     'schedule', 'process_status', 'metadata',)
