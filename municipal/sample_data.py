"""Fictional sample data: procedures, complaints with their history, and demo users.

Loaded with `python manage.py seed`, and by the tests.
"""

from datetime import datetime
from decimal import Decimal
from functools import cache
from zoneinfo import ZoneInfo

from django.contrib.auth.hashers import make_password
from django.db import transaction

from accounts.models import User
from municipal.models import Complaint, ComplaintEvent, ComplaintStatus, Procedure, Requirement

LIMA = ZoneInfo("America/Lima")

REGISTERED_NOTE = "Reclamo registrado en la plataforma de atención ciudadana."

# Demo accounts for local development only. Every demo user shares this password.
DEMO_PASSWORD = "vecino-demo-2026"

DEMO_USERS = [
    {"email": "maria.quispe@example.com", "first_name": "María", "last_name": "Quispe Huamán", "dni": "70000001"},
    {"email": "jose.mamani@example.com", "first_name": "José", "last_name": "Mamani Condori", "dni": "70000002"},
    {"email": "rosa.flores@example.com", "first_name": "Rosa", "last_name": "Flores Vargas", "dni": "70000003"},
]


def _at(day: str, time: str) -> datetime:
    return datetime.fromisoformat(f"{day}T{time}").replace(tzinfo=LIMA)


PROCEDURES = [
    {
        "code": "LF-01",
        "name": "Licencia de funcionamiento para establecimientos de riesgo bajo o medio",
        "description": (
            "Autoriza el desarrollo de actividades económicas en un establecimiento "
            "determinado. Aplica a establecimientos de hasta 500 m² clasificados con "
            "nivel de riesgo bajo o medio."
        ),
        "office": "Subgerencia de Licencias y Comercialización",
        "fee": Decimal("98.50"),
        "processing_days": 4,
        "available_online": True,
        "requirements": [
            "Solicitud de licencia de funcionamiento con carácter de declaración jurada "
            "(formato gratuito), indicando el número de RUC y DNI del solicitante o "
            "representante legal.",
            "En caso de personas jurídicas, vigencia de poder del representante legal.",
            "Declaración jurada de cumplimiento de las condiciones de seguridad en la edificación.",
            "Pago del derecho de trámite.",
        ],
    },
    {
        "code": "CN-01",
        "name": "Certificado de numeración de inmueble",
        "description": "Asigna o certifica la numeración oficial de un inmueble ubicado en el distrito.",
        "office": "Subgerencia de Obras Privadas y Catastro",
        "fee": Decimal("42.00"),
        "processing_days": 5,
        "available_online": False,
        "requirements": [
            "Solicitud dirigida al alcalde con los datos del solicitante y la ubicación del inmueble.",
            "Copia del documento que acredite la propiedad del inmueble.",
            "Plano o croquis de ubicación del inmueble.",
            "Pago del derecho de trámite.",
        ],
    },
    {
        "code": "PU-01",
        "name": "Certificado de parámetros urbanísticos y edificatorios",
        "description": (
            "Informa las condiciones técnicas de diseño (zonificación, alturas, retiros "
            "y usos permitidos) que debe respetar un proyecto de edificación en un predio."
        ),
        "office": "Subgerencia de Obras Privadas y Catastro",
        "fee": Decimal("86.30"),
        "processing_days": 5,
        "available_online": True,
        "requirements": [
            "Solicitud indicando la ubicación del predio (dirección, manzana y lote).",
            "Plano de ubicación del predio.",
            "Pago del derecho de trámite.",
        ],
    },
    {
        "code": "AP-01",
        "name": "Autorización de anuncio publicitario adosado a fachada",
        "description": (
            "Autoriza la instalación de un anuncio o letrero adosado a la fachada de un "
            "establecimiento que cuenta con licencia de funcionamiento."
        ),
        "office": "Subgerencia de Licencias y Comercialización",
        "fee": Decimal("55.00"),
        "processing_days": 5,
        "available_online": True,
        "requirements": [
            "Solicitud con carácter de declaración jurada (formato gratuito).",
            "Número de la licencia de funcionamiento del establecimiento.",
            "Arte o fotomontaje del anuncio indicando sus dimensiones.",
            "Fotografía de la fachada donde se instalará el anuncio.",
            "Pago del derecho de trámite.",
        ],
    },
    {
        "code": "MC-01",
        "name": "Matrimonio civil en el local municipal",
        "description": "Celebración del matrimonio civil en el local municipal, en la fecha y hora programadas.",
        "office": "Oficina de Registro Civil",
        "fee": Decimal("160.00"),
        "processing_days": 8,
        "available_online": False,
        "requirements": [
            "Solicitud firmada por ambos contrayentes.",
            "Copia certificada de la partida de nacimiento de cada contrayente, con "
            "antigüedad no mayor a tres meses.",
            "Copia del DNI de los contrayentes y de dos testigos mayores de edad.",
            "Certificado médico prenupcial de cada contrayente.",
            "Declaración jurada de domicilio y de estado civil.",
            "Pago del derecho de trámite.",
        ],
    },
    {
        "code": "RC-02",
        "name": "Copia certificada de partida de nacimiento",
        "description": (
            "Emisión de copias certificadas de partidas de nacimiento inscritas en el "
            "registro civil de la municipalidad."
        ),
        "office": "Oficina de Registro Civil",
        "fee": Decimal("12.00"),
        "processing_days": 1,
        "available_online": True,
        "requirements": [
            "Nombres y apellidos de la persona inscrita y, de ser posible, el año de inscripción.",
            "Pago del derecho de trámite.",
        ],
    },
]

# Each complaint's current status, created_at and updated_at are derived from its events.
COMPLAINTS = [
    {
        "tracking_code": "REC-2026-0001",
        "citizen_dni": "70000001",
        "citizen_name": "María Quispe Huamán",
        "category": "Limpieza pública",
        "description": (
            "El camión recolector no pasa por la calle Los Geranios, cuadra 3, desde hace "
            "una semana. Hay acumulación de basura en la esquina."
        ),
        "assigned_office": "Subgerencia de Gestión Ambiental",
        "events": [
            (ComplaintStatus.RECEIVED, _at("2026-09-02", "08:15"), REGISTERED_NOTE),
            (ComplaintStatus.FORWARDED, _at("2026-09-03", "10:40"), "Derivado a la Subgerencia de Gestión Ambiental."),
            (
                ComplaintStatus.RESOLVED,
                _at("2026-09-06", "16:05"),
                "Se reprogramó la ruta de recolección y se limpió el punto crítico. "
                "El servicio está normalizado.",
            ),
        ],
    },
    {
        "tracking_code": "REC-2026-0002",
        "citizen_dni": "70000001",
        "citizen_name": "María Quispe Huamán",
        "category": "Alumbrado público",
        "description": (
            "El poste de alumbrado frente al parque Los Pinos está apagado desde hace dos "
            "semanas y la zona queda muy oscura de noche."
        ),
        "assigned_office": "Subgerencia de Obras Públicas",
        "events": [
            (ComplaintStatus.RECEIVED, _at("2026-09-28", "19:30"), REGISTERED_NOTE),
            (
                ComplaintStatus.IN_REVIEW,
                _at("2026-09-30", "11:00"),
                "Se programó una inspección técnica y se notificó a la empresa "
                "concesionaria de electricidad.",
            ),
        ],
    },
    {
        "tracking_code": "REC-2026-0003",
        "citizen_dni": "70000002",
        "citizen_name": "José Mamani Condori",
        "category": "Ruidos molestos",
        "description": (
            "Un local de la calle Las Magnolias tiene música a alto volumen después de "
            "medianoche los viernes y sábados."
        ),
        "assigned_office": "Subgerencia de Fiscalización Administrativa",
        "events": [
            (ComplaintStatus.RECEIVED, _at("2026-09-15", "09:10"), REGISTERED_NOTE),
            (
                ComplaintStatus.FORWARDED,
                _at("2026-09-16", "15:20"),
                "Derivado a la Subgerencia de Fiscalización Administrativa para verificar el local.",
            ),
            (
                ComplaintStatus.IN_REVIEW,
                _at("2026-09-21", "10:00"),
                "Se realizó un operativo nocturno de verificación. El caso está en "
                "evaluación para iniciar el procedimiento sancionador.",
            ),
        ],
    },
    {
        "tracking_code": "REC-2026-0004",
        "citizen_dni": "70000002",
        "citizen_name": "José Mamani Condori",
        "category": "Pistas y veredas",
        "description": (
            "Hay un bache profundo en la avenida Principal, a la altura de la cuadra 8, "
            "que ya causó accidentes de motos."
        ),
        "assigned_office": "",
        "events": [
            (ComplaintStatus.RECEIVED, _at("2026-10-10", "18:45"), REGISTERED_NOTE),
        ],
    },
    {
        "tracking_code": "REC-2026-0005",
        "citizen_dni": "70000003",
        "citizen_name": "Rosa Flores Vargas",
        "category": "Parques y jardines",
        "description": "Las áreas verdes del pasaje Santa Rosa no se riegan desde hace un mes.",
        "assigned_office": "Subgerencia de Gestión Ambiental",
        "events": [
            (ComplaintStatus.RECEIVED, _at("2026-08-20", "12:00"), REGISTERED_NOTE),
            (ComplaintStatus.IN_REVIEW, _at("2026-08-22", "09:30"), "Se inspeccionó la zona reportada."),
            (
                ComplaintStatus.REJECTED,
                _at("2026-08-25", "14:10"),
                "El área reportada es de propiedad privada (condominio), por lo que su "
                "mantenimiento corresponde a la junta de propietarios. Se brindó "
                "orientación a la persona reclamante.",
            ),
        ],
    },
    {
        "tracking_code": "REC-2026-0006",
        "citizen_dni": "70000003",
        "citizen_name": "Rosa Flores Vargas",
        "category": "Seguridad ciudadana",
        "description": (
            "Solicito mayor patrullaje de serenazgo en el parque San Martín por las noches; "
            "los vecinos reportan robos frecuentes."
        ),
        "assigned_office": "Gerencia de Seguridad Ciudadana",
        "events": [
            (ComplaintStatus.RECEIVED, _at("2026-10-05", "21:05"), REGISTERED_NOTE),
            (ComplaintStatus.FORWARDED, _at("2026-10-06", "08:30"), "Derivado a la Gerencia de Seguridad Ciudadana."),
        ],
    },
]


@cache
def _demo_password_hash() -> str:
    # Hashing is deliberately slow; do it once, not per user or per test.
    return make_password(DEMO_PASSWORD)


@transaction.atomic
def load_sample_data() -> None:
    """Replace the sample procedures, complaints and demo users.

    Other users, such as the superuser you create for the admin, are left alone.
    """
    Procedure.objects.all().delete()  # cascades to requirements
    Complaint.objects.all().delete()  # cascades to events
    User.objects.filter(email__in=[u["email"] for u in DEMO_USERS]).delete()

    User.objects.bulk_create(User(**data, password=_demo_password_hash()) for data in DEMO_USERS)

    for data in PROCEDURES:
        fields = {k: v for k, v in data.items() if k != "requirements"}
        procedure = Procedure.objects.create(**fields)
        Requirement.objects.bulk_create(
            Requirement(procedure=procedure, position=position, description=text)
            for position, text in enumerate(data["requirements"], start=1)
        )

    for data in COMPLAINTS:
        fields = {k: v for k, v in data.items() if k != "events"}
        events = data["events"]
        complaint = Complaint.objects.create(
            **fields, status=events[-1][0], created_at=events[0][1], updated_at=events[-1][1]
        )
        ComplaintEvent.objects.bulk_create(
            ComplaintEvent(complaint=complaint, status=status, created_at=created_at, note=note)
            for status, created_at, note in events
        )
