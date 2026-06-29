# auto generated file

from stagehand.toolbox.config import Var, Group, Dict, List, Config

config = Config(desc='XBMC notifier', schema=[

  Var(name='hostname', default='localhost'),

  Var(name='http_port', default=8080),

  Var(name='tcp_port', default=9090),

  Var(name='notify', default=True),

  Var(name='individual', desc='''
  If True, update the media library for individual series
  directories.  If False, do a full library update.
  ''', default=True),

  Var(name='tvdir', desc='''
  The XBMC host\'s local path to the TV directory.  If defined,
  Stagehand will remap the path to the series directory when poking
  XBMC to update.  If not defined, no translation is done.
  
  This is useful if Stagehand\'s view of the filesystem is different
  than XBMC\'s.  Only relevant if individual is True.
  ''', default=''),

  ]
, module='stagehand.notifiers.config')

