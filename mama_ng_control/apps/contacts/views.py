from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Contact
from .serializers import ContactSerializer


class ContactViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows contact models to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    filter_fields = ('details',)
