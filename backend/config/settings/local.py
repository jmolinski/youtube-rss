import socket

from .base import *  # noqa

# DEBUG
# ------------------------------------------------------------------------------
DEBUG = env.bool("DJANGO_DEBUG", default=True)
TEMPLATES[0]["OPTIONS"]["debug"] = DEBUG
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", default=["localhost", "0.0.0.0", "*"])

# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = env("DJANGO_SECRET_KEY")


# EMAIL
# ------------------------------------------------------------------------------

EMAIL_PORT = 1025
EMAIL_HOST = "localhost"
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)


# CACHING
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    }
}


# DJANGO DEBUG TOOLBAR
# ------------------------------------------------------------------------------
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
INSTALLED_APPS += ["debug_toolbar"]

INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]

# tricks to have debug toolbar when developing with docker
ip = socket.gethostbyname(socket.gethostname())
INTERNAL_IPS += [ip[:-1] + "1"]


DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": ["debug_toolbar.panels.redirects.RedirectsPanel"],
    "SHOW_TEMPLATE_CONTEXT": True,
}


# DJANGO EXTENSIONS
# ------------------------------------------------------------------------------
INSTALLED_APPS += ["django_extensions"]

# TESTING
# ------------------------------------------------------------------------------
# TEST_RUNNER = 'django.test.runner.DiscoverRunner'
TEST_RUNNER = "config.runner.PytestTestRunner"
AUTHENTICATION_BACKENDS += ["django_webtest.backends.WebtestUserBackend"]


MIDDLEWARE += ["django_webtest.middleware.WebtestUserMiddleware"]

# CORS

CORS_ORIGIN_ALLOW_ALL = True

# Your local stuff: Below this line define 3rd party library settings
# ------------------------------------------------------------------------------

KEEP_LAST_N = env.int("KEEP_LAST_N", 5)
REMOVE_THRESHOLD_N = env.int("REMOVE_THRESHOLD_N", 5)
NR_FEED_DOMAIN = "https://nocneradio.xyz/"
CONCURRENT_DOWNLOADS = env.int("CONCURRENT_DOWNLOADS", 1)
