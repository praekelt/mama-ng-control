from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from .models import Outbound, Inbound
from .serializers import OutboundSerializer, InboundSerializer
from .tasks import send_message


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


class EventListener(APIView):

    """
    Triggers updates to outbound messages based on event data from Vumi
    """
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        """
        Checks for expect event types before continuing
        """

        try:
            expect = ["message_type", "event_type", "user_message_id",
                      "event_id", "timestamp"]
            if set(expect).issubset(request.data.keys()):
                # Load message
                message = Outbound.objects.get(
                    vumi_message_id=request.data["user_message_id"])
                # only expecting `event` on this endpoint
                if request.data["message_type"] == "event":
                    event = request.data["event_type"]
                    # expecting ack, nack, delivery_report
                    if event == "ack":
                        message.delivered = True
                        message.metadata["ack_timestamp"] = \
                            request.data["timestamp"]
                    elif event == "delivery_report":
                        message.delivered = True
                        message.metadata["delivery_timestamp"] = \
                            request.data["timestamp"]
                    elif event == "nack":
                        if "nack_reason" in request.data:
                            message.metadata["nack_reason"] = \
                                request.data["nack_reason"]
                        send_message.delay(str(message.id))
                    message.save()
                    # Return
                    status = 200
                    accepted = {"accepted": True}
                else:
                    status = 400
                    accepted = {"accepted": False,
                                "reason": "Unexpected message_type"}
            else:
                status = 400
                accepted = {"accepted": False,
                            "reason": "Missing expected body keys"}
        except ObjectDoesNotExist:
            status = 400
            accepted = {"accepted": False,
                        "reason": "Missing message in control"}
        return Response(accepted, status=status)
