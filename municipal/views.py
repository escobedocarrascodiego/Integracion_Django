from django.db import connection
from django.http import Http404
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from municipal import services
from municipal.serializers import (
    ComplaintDetailSerializer,
    ComplaintSummarySerializer,
    ProcedureDetailSerializer,
    ProcedureSummarySerializer,
)


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return Response({"status": "ok"})


# Procedures are public information: these views opt out of the default
# "logged-in users only" permission.


class ProcedureListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProcedureSummarySerializer

    def get_queryset(self):
        return services.search_procedures(self.request.query_params.get("q", ""))


class ProcedureDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProcedureDetailSerializer

    def get_object(self):
        procedure = services.get_procedure(self.kwargs["code"])
        if procedure is None:
            raise Http404("Trámite no encontrado.")
        return procedure


# Complaints are personal: these keep the default permission, and the DNI
# always comes from the logged-in user.


class MyComplaintListView(generics.ListAPIView):
    serializer_class = ComplaintSummarySerializer

    def get_queryset(self):
        return services.list_complaints(self.request.user.dni)


class MyComplaintDetailView(generics.RetrieveAPIView):
    serializer_class = ComplaintDetailSerializer

    def get_object(self):
        complaint = services.get_complaint(self.kwargs["tracking_code"], self.request.user.dni)
        if complaint is None:
            # Same answer whether it doesn't exist or belongs to someone else.
            raise Http404("Reclamo no encontrado.")
        return complaint
