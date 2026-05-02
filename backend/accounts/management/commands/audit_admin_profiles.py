from django.core.management.base import BaseCommand

from accounts.models import UserProfile
from core.constants import ROLE_ADMIN


class Command(BaseCommand):
    help = "Flag ROLE_ADMIN profiles whose linked Django user is not staff."

    def add_arguments(self, parser):
        parser.add_argument("--deactivate", action="store_true", help="Deactivate flagged profiles.")

    def handle(self, *args, **options):
        qs = UserProfile.objects.select_related("user").filter(role=ROLE_ADMIN, user__is_staff=False)
        count = qs.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No non-staff ROLE_ADMIN profiles found."))
            return

        for profile in qs:
            self.stdout.write(
                self.style.WARNING(
                    f"FLAG username={profile.user.username} email={profile.user.email} "
                    f"profile_id={profile.id} active={profile.is_active}"
                )
            )
            if options["deactivate"]:
                profile.is_active = False
                profile.save(update_fields=["is_active", "updated_at"])

        if options["deactivate"]:
            self.stdout.write(self.style.SUCCESS(f"Deactivated {count} flagged profile(s)."))
        else:
            self.stdout.write(self.style.WARNING(f"Found {count} flagged profile(s). Re-run with --deactivate to disable them."))
