project('native-popcorn',
          version: '0.1.0',
          license: 'GPL-3.0-or-later',
    meson_version: '>= 0.62.0',
  default_options: [ 'warning_level=2', 'werror=false', ],
)

dependency('glib-2.0', version: '>= 2.66')
dependency('gio-2.0', version: '>= 2.66')
dependency('gtk4', version: '>= 4.0.0')
dependency('libadwaita-1', version: '>= 1.0.0')

python = import('python')
py_installation = python.find_installation('python3')

if not py_installation.found()
    error('No valid python3 found!')
endif

subdir('src')
subdir('data')
