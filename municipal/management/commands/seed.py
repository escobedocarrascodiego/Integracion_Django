from django.core.management.base import BaseCommand

from municipal.sample_data import COMPLAINTS, DEMO_USERS, PROCEDURES, load_sample_data


class Command(BaseCommand):
    help = "Replace the sample procedures, complaints and demo users (other users are kept)."

    def handle(self, *args, **options):
        load_sample_data()
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(DEMO_USERS)} demo users, {len(PROCEDURES)} procedures "
            f"and {len(COMPLAINTS)} complaints."
        ))
