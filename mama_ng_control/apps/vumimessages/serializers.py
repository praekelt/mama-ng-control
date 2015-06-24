from .models import Outbound, Inbound
from rest_framework import serializers


class OutboundSerializer(serializers.HyperlinkedModelSerializer):
    metadata = serializers.DictField(child=serializers.CharField())

    class Meta:
        model = Outbound
        fields = (
            'url', 'id', 'version', 'contact', 'vumi_message_id',
            'delivered', 'attempts', 'metadata', 'created_at', 'updated_at')


class InboundSerializer(serializers.HyperlinkedModelSerializer):
    metadata = serializers.DictField(child=serializers.CharField())

    class Meta:
        model = Inbound
        fields = (
            'url', 'id', 'message_id', 'in_reply_to', 'to_addr',
            'from_addr', 'content', 'transport_name', 'transport_type',
            'helper_metadata', 'created_at', 'updated_at')
