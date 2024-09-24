from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

HOTETEC_CONFIG = getattr(settings, 'HOTETEC_CONFIG', {})

if not hasattr(settings, 'HOTETEC_CONFIG'):
    raise ImproperlyConfigured("You must define the HOTETEC_CONFIG variable in your settings.py")

if not HOTETEC_CONFIG.get('AGENCY_CODE'):
    raise ImproperlyConfigured("You must define the AGENCY_CODE attribute in your HOTETEC_CONFIG")

if not HOTETEC_CONFIG.get('USERNAME'):
    raise ImproperlyConfigured("You must define the USERNAME attribute in your HOTETEC_CONFIG")

if not HOTETEC_CONFIG.get('PASSWORD'):
    raise ImproperlyConfigured("You must define the PASSWORD attribute in your HOTETEC_CONFIG")
