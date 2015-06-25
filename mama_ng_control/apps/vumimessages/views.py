from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Outbound, Inbound
from .serializers import OutboundSerializer, InboundSerializer


class OutboundViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows Outbound models to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = Outbound.objects.all()
    serializer_class = OutboundSerializer
    filter_fields = ('version', 'contact', 'vumi_message_id', 'delivered',
                     'attempts', 'metadata', 'created_at', 'updated_at',)


class InboundViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows Inbound models to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = Inbound.objects.all()
    serializer_class = InboundSerializer
    filter_fields = ('message_id', 'in_reply_to', 'to_addr', 'from_addr',
                     'content', 'transport_name', 'transport_type',
                     'helper_metadata', 'created_at', 'updated_at',)
