# auto generated file

from stagehand.toolbox.config import Var, Group, Dict, List, Config

config = Config(desc='Easynews global search', schema=[

  Var(name='username', default=''),

  Var(name='password', default='', scramblekey='stagehand'),

  Var(name='url', desc='''
  The full URL that will be retrieved for search results.  The URL
  must contain 3 substrings that will be replaced: {subject}, {date},
  and {size}.
  
  Normally it should not be necessary to configure this as a sensible
  default is used if it\'s blank (global5 over HTTPS).
  ''', default=''),

  Var(name='retries', desc='''
  Number of times to retry if the server returns some non-fatal
  error before giving up.
  ''', default=5),

  ]
, module='stagehand.searchers.config')

