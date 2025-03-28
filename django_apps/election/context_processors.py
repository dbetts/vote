from django.conf import settings
from django_apps.election.models import Asset, Election

def default_phone(request):
    try:
        election = Election.objects.select_related().get(pk=request.session.get('election_id'))
        asset = Asset.objects.get(election=election)
        phone = asset.default_phone
    except Election.DoesNotExist:
        phone = settings.SUPPORT_PHONE

    return {
        'default_phone' : phone,
    }


def default_email(request):
    try:
        election = Election.objects.select_related().get(pk=request.session.get('election_id'))
        asset = Asset.objects.get(election=election)
        email = asset.default_email
    except Election.DoesNotExist:
        email = settings.SUPPORT_EMAIL

    return {
        'default_email' : email,
    }