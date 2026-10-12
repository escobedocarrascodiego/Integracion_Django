"""How models become JSON: DRF's equivalent of the Flask version's Pydantic schemas."""

from rest_framework import serializers

from municipal.models import Complaint, ComplaintEvent, Procedure


class ProcedureSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Procedure
        # fee comes out as a string ("98.50"): money never goes through floats.
        fields = ["code", "name", "office", "fee", "processing_days", "available_online"]


class ProcedureDetailSerializer(ProcedureSummarySerializer):
    # The requirement texts, in order (Requirement.Meta.ordering).
    requirements = serializers.SlugRelatedField(many=True, read_only=True, slug_field="description")

    class Meta(ProcedureSummarySerializer.Meta):
        fields = [*ProcedureSummarySerializer.Meta.fields, "description", "requirements"]


class ComplaintEventSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ComplaintEvent
        fields = ["status", "status_label", "note", "created_at"]


class ComplaintSummarySerializer(serializers.ModelSerializer):
    # "in_review" for programs, "En evaluación" for people.
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Complaint
        # Datetimes come out in Lima time (settings.TIME_ZONE), e.g. 2026-09-02T08:15:00-05:00.
        fields = ["tracking_code", "category", "status", "status_label", "assigned_office", "created_at", "updated_at"]


class ComplaintDetailSerializer(ComplaintSummarySerializer):
    events = ComplaintEventSerializer(many=True, read_only=True)

    class Meta(ComplaintSummarySerializer.Meta):
        fields = [*ComplaintSummarySerializer.Meta.fields, "description", "events"]
