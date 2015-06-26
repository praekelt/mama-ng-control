from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist

from .models import Subscription
from .serializers import SubscriptionSerializer

from mama_ng_control.apps.vumimessages.models import Outbound


class SubscriptionViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows Subscription models to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    filter_fields = ('contact', 'messageset_id', 'lang', 'active', 'completed',
                     'schedule', 'process_status', 'metadata',)


class SubscriptionSend(APIView):

    """
    Triggers a send for the
    """
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        """
        Triggers celery tasks for user
        """
        # Look up subscriber
        subscription_id = kwargs["subscription_id"]
        try:
            subscription = Subscription.objects.get(id=subscription_id)
            expect = ["message-id", "send-counter", "schedule-id"]
            if set(expect).issubset(request.data.keys()):
                # Set the next sequence number
                subscription.next_sequence_number = request.data[
                    "send-counter"]
                subscription.save()
                # Create the message which will trigger send task
                new_message = Outbound()
                new_message.contact = subscription.contact
                new_message.metadata = {}
                new_message.metadata["scheduler_message_id"] = \
                    request.data["message-id"]
                new_message.metadata["scheduler_schedule_id"] = \
                    request.data["schedule-id"]
                new_message.save()
                # Return
                status = 201
                accepted = {"accepted": True}
            else:
                status = 400
                accepted = {"accepted": False,
                            "reason": "Missing expected body keys"}
        except ObjectDoesNotExist:
            status = 400
            accepted = {"accepted": False,
                        "reason": "Missing subscription in control"}
        return Response(accepted, status=status)
