from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from Rachels.models import ManagerProfile
from django.db import transaction


class Command(BaseCommand):
    help = "Remove all manager users and their profiles (keeps admin users)."

    def handle(self, *args, **options):
        with transaction.atomic():
            profiles = ManagerProfile.objects.select_related("user")

            if not profiles.exists():
                self.stdout.write(self.style.WARNING("No manager profiles found."))
                return

            for profile in profiles:
                user = profile.user
                username = user.username

                # Safety check: never delete superusers
                if user.is_superuser:
                    self.stdout.write(
                        self.style.WARNING(f"Skipping superuser '{username}'")
                    )
                    continue

                profile.delete()
                user.delete()

                self.stdout.write(
                    self.style.SUCCESS(f"Deleted manager '{username}'")
                )

        self.stdout.write(self.style.SUCCESS("All manager users removed successfully."))
