from settings import *

DEBUG = False

TEMPLATE_DEBUG = False
TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates'),
)

ALLOWED_HOSTS = ['localhost']
ADMINS = (('David Brown', 'david.brown@pnnl.gov'))
MANAGERS = (('David Brown', 'david.brown@pnnl.gov'))
EMAIL_HOST = 'mailhost.emsl.pnl.gov'
SERVER_EMAIL = 'dmlb2000@we27430.emsl.pnl.gov'
