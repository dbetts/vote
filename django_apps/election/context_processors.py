from django.conf import settings
from django_apps.election.models import Asset, Election

def default_phone(request):
    try:
        election = Election.objects.select_related().get(pk=request.session.get('election_id'))
        asset = Asset.objects.get(election=election)
        default_phone = asset.default_phone
    except Election.DoesNotExist:
        default_phone = settings.SUPPORT_PHONE

    return {
        'default_phone' : default_phone,
    }


def default_email(request):
    try:
        election = Election.objects.select_related().get(pk=request.session.get('election_id'))
        asset = Asset.objects.get(election=election)
        default_email = asset.default_email
    except Election.DoesNotExist:
        default_email = settings.SUPPORT_EMAIL

    return {
        'default_email' : default_email,
    }