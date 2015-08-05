from rest_framework import viewsets, generics
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


class ContactSearchList(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ContactSerializer

    def get_queryset(self):
        """
        This view should return a list of all the contacts
        for the supplied msisdn
        """
        contains = {
            "addresses": "msisdn:%s" % self.request.query_params["msisdn"]
        }
        data = Contact.objects.filter(
            details__contains=contains)
        return data
