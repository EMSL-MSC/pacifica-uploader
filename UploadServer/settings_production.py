"""Production settings."""
import os

DEBUG = True

if not 'AMQP_PORT_5672_TCP_ADDR' in os.environ:
    os.environ['AMQP_PORT_5672_TCP_ADDR'] = 'localhost'
    os.environ['AMQP_PORT_5672_TCP_PORT'] = '5672'
BROKER_URL = 'amqp://guest:guest@'
BROKER_URL += os.environ['AMQP_PORT_5672_TCP_ADDR']+':'
BROKER_URL += os.environ['AMQP_PORT_5672_TCP_PORT']+'//'

TEMPLATE_DEBUG = False
TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates'),
)

ALLOWED_HOSTS = ['localhost', '*']
ADMINS = (('David Brown', 'david.brown@pnnl.gov'))
MANAGERS = (('David Brown', 'david.brown@pnnl.gov'))
EMAIL_HOST = 'emailgw01.pnnl.gov'
SERVER_EMAIL = 'dmlb2000@we27430.emsl.pnl.gov'
