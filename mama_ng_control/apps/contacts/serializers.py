from .models import Contact
from rest_framework import serializers


class ContactSerializer(serializers.HyperlinkedModelSerializer):
    details = serializers.DictField(child=serializers.CharField())

    class Meta:
        model = Contact
        fields = (
            'url', 'id', 'version', 'details', 'created_at', 'updated_at')
