from django.contrib.auth.signals import user_logged_in
from django.contrib.sessions.models import Session
from django.dispatch import receiver
from django.utils import timezone


def invalidate_other_user_sessions(user, keep_session_key=None):
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) != str(user.pk):
            continue
        if keep_session_key and session.session_key == keep_session_key:
            continue
        session.delete()


@receiver(user_logged_in)
def rehash_and_rotate_user_sessions(sender, request, user, **kwargs):
    # Django rehashes legacy password hashes on successful login when a stronger
    # preferred hasher is configured. Keep the current session, drop older ones.
    invalidate_other_user_sessions(user, keep_session_key=request.session.session_key)
