# yourapp/management/commands/create_initial_users.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ...models import ManagerProfile

class Command(BaseCommand):
    help = "Create initial admin and five manager users (for development)."

    def handle(self, *args, **options):
        # Admin
        admin_username = "admin"
        admin_password = "adminpass123"  # CHANGE after creation
        if not User.objects.filter(username=admin_username).exists():
            admin = User.objects.create_superuser(username=admin_username, email="", password=admin_password)
            self.stdout.write(self.style.SUCCESS(f"Created superuser '{admin_username}' / password '{admin_password}'"))
        else:
            self.stdout.write(self.style.NOTICE(f"User '{admin_username}' already exists"))

        # Managers and their locations
        managers = [
            ("manager_dulari", "Dulari"),
            ("manager_pours", "Pours and Plates"),
            ("manager_rachels", "Rachels"),
            ("manager_rachels1", "Rachels1"),
            ("manager_rachels2", "Rachels2"),
        ]
        default_password = "managerpass123"  # CHANGE these after creation
        for uname, loc in managers:
            if User.objects.filter(username=uname).exists():
                self.stdout.write(self.style.NOTICE(f"User '{uname}' already exists"))
                user = User.objects.get(username=uname)
            else:
                user = User.objects.create_user(username=uname, password=default_password)
                self.stdout.write(self.style.SUCCESS(f"Created user '{uname}' / password '{default_password}'"))
            # ensure ManagerProfile exists and is set
            profile, created = ManagerProfile.objects.get_or_create(user=user)
            profile.location = loc
            profile.save()
            self.stdout.write(self.style.SUCCESS(f"Assigned location '{loc}' to '{uname}'"))

        self.stdout.write(self.style.SUCCESS("Initial accounts created. Please change the passwords promptly."))
