
project('spam', 'c',
  version: '0.1.0',
  default_options: ['warning_level=2'],
)

py = import('python').find_installation(pure: false)

py.extension_module('spam',
  'spam.c',
  install: true,
)