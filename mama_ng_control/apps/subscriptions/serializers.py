from .models import Subscription
from rest_framework import serializers


class SubscriptionSerializer(serializers.HyperlinkedModelSerializer):
    metadata = serializers.DictField(child=serializers.CharField())

    class Meta:
        model = Subscription
        fields = (
            'url', 'id', 'version', 'contact', 'messageset_id',
            'next_sequence_number', 'lang', 'active', 'completed', 'schedule',
            'process_status', 'metadata', 'created_at', 'updated_at')
