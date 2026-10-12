from django.db import models
from django.db.models import Q
from django.utils import timezone


class Procedure(models.Model):
    """An administrative procedure ("trámite") from the municipal TUPA."""

    code = models.CharField("código", max_length=20, unique=True)
    name = models.CharField("nombre", max_length=200)
    description = models.TextField("descripción")
    office = models.CharField("oficina", max_length=120)
    fee = models.DecimalField("derecho de trámite (S/)", max_digits=10, decimal_places=2)
    processing_days = models.PositiveIntegerField("plazo (días hábiles)")
    available_online = models.BooleanField("disponible en línea", default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "trámite"
        verbose_name_plural = "trámites"

    def __str__(self):
        return f"{self.code} · {self.name}"


class Requirement(models.Model):
    """One requirement of a procedure, kept in the order citizens should read them."""

    procedure = models.ForeignKey(Procedure, on_delete=models.CASCADE, related_name="requirements")
    position = models.PositiveIntegerField("orden")
    description = models.TextField("descripción")

    class Meta:
        ordering = ["procedure", "position"]
        constraints = [
            models.UniqueConstraint(fields=["procedure", "position"], name="unique_requirement_position"),
        ]
        verbose_name = "requisito"
        verbose_name_plural = "requisitos"

    def __str__(self):
        return f"{self.position}. {self.description}"


class ComplaintStatus(models.TextChoices):
    # value stored in the database, label shown to people
    RECEIVED = "received", "Registrado"
    IN_REVIEW = "in_review", "En evaluación"
    FORWARDED = "forwarded", "Derivado a otra área"
    RESOLVED = "resolved", "Atendido"
    REJECTED = "rejected", "Improcedente"


def _valid_status(name):
    # choices only validate forms and the admin; this CHECK makes the database
    # itself refuse an unknown status, whoever writes it.
    return models.CheckConstraint(condition=Q(status__in=ComplaintStatus.values), name=name)


class Complaint(models.Model):
    """A citizen complaint or report ("reclamo") and its current status."""

    tracking_code = models.CharField("código de seguimiento", max_length=20, unique=True)
    citizen_dni = models.CharField("DNI del ciudadano", max_length=8, db_index=True)
    citizen_name = models.CharField("nombre del ciudadano", max_length=150)
    category = models.CharField("categoría", max_length=80)
    description = models.TextField("descripción")
    status = models.CharField("estado", max_length=20, choices=ComplaintStatus.choices, default=ComplaintStatus.RECEIVED)
    # Django convention: text fields use "" rather than NULL for "no value".
    assigned_office = models.CharField("oficina asignada", max_length=120, blank=True)
    # default=timezone.now rather than auto_now_add/auto_now, which would ignore the
    # historical dates the sample data sets.
    created_at = models.DateTimeField("registrado", default=timezone.now)
    updated_at = models.DateTimeField("última actualización", default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        constraints = [_valid_status("complaint_status_valid")]
        verbose_name = "reclamo"
        verbose_name_plural = "reclamos"

    def __str__(self):
        return self.tracking_code


class ComplaintEvent(models.Model):
    """One entry in a complaint's history: a status change plus a note for the citizen."""

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="events")
    status = models.CharField("estado", max_length=20, choices=ComplaintStatus.choices)
    note = models.TextField("nota")
    created_at = models.DateTimeField("fecha", default=timezone.now)

    class Meta:
        ordering = ["created_at"]
        constraints = [_valid_status("complaint_event_status_valid")]
        verbose_name = "evento del reclamo"
        verbose_name_plural = "historial del reclamo"

    def __str__(self):
        return f"{self.complaint} → {self.get_status_display()}"
