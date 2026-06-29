# auto generated file

from stagehand.toolbox.config import Var, Group, Dict, List, Config

config = Config(desc='Email notifier', schema=[

  Var(name='hostname', desc='Hostname of the SMTP relay to use.', default='localhost'),

  Var(name='ssl', desc='''
  Normally STARTTLS is used if available.  If this option is
  true, then assume the remote is an SSL port and negotiate
  SSL immediately.
  ''', default=False),

  Var(name='port', default=587),

  Var(name='username', desc='If specified, authenticate to the SMTP server with this username.', default=''),

  Var(name='password', desc='If specified, authenticate to the SMTP server with this password.', default='', scramblekey='stagehand'),

  Var(name='sender', desc='Email address the notification email will be sent from.', default='stagehand@localhost'),

  Var(name='recipients', desc='''
  Comma-separated list of email addresses that will receive the
  notification.
  ''', default=''),

  ]
, module='stagehand.notifiers.config')

