python.install_sources(
    files(
        '__init__.py',
        '__main__.py',
        'application.py',
        'cover.py',
        'gamepads.py',
        'games.py',
    ),
    subdir: 'hotbar',
)

install_subdir('sources', install_dir: python.get_install_dir() / 'hotbar')

configure_file(
    input: 'config.py.in',
    output: '@BASENAME@',
    configuration: conf,
    install_dir: python.get_install_dir(subdir: 'hotbar'),
)

subdir('ui')
