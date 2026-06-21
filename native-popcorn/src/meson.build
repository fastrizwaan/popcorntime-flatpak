pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'native_popcorn')

install_data(
    'native_popcorn/__init__.py',
    'native_popcorn/api.py',
    'native_popcorn/database.py',
    'native_popcorn/main.py',
    'native_popcorn/player.py',
    'native_popcorn/window.py',
    install_dir: moduledir
)

conf = configuration_data()
conf.set('pkgdatadir', pkgdatadir)
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))

configure_file(
    input: 'native-popcorn.in',
    output: 'native-popcorn',
    configuration: conf,
    install: true,
    install_dir: get_option('bindir'),
    install_mode: 'rwxr-xr-x'
)
