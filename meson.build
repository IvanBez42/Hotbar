project(
    'hotbar',
    version: '0.1.0',
    meson_version: '>= 1.1.0',
    default_options: ['warning_level=2', 'werror=false'],
)

i18n = import('i18n')
gnome = import('gnome')
python = import('python').find_installation('python3')

blueprint_compiler = find_program('blueprint-compiler')
desktop_utils = find_program(
    'desktop-file-validate',
    required: false,
    disabler: true,
)
compile_schemas = find_program(
    'glib-compile-schemas',
    required: false,
    disabler: true,
)
appstreamcli = find_program('appstreamcli', required: false, disabler: true)

localedir = get_option('prefix') / get_option('localedir')
bindir = get_option('prefix') / get_option('bindir')
resourcedir = python.get_install_dir() / 'hotbar' / 'resources'

profile = get_option('profile')
if profile == 'development'
    app_id = 'io.github.IvanBez42.Hotbar.Devel'
    prefix = '/io/github/IvanBez42/Hotbar/Devel'
elif profile == 'release'
    app_id = 'io.github.IvanBez42.Hotbar'
    prefix = '/io/github/IvanBez42/Hotbar'
endif

conf = configuration_data(
    {
        'PYTHON': python.full_path(),
        'APP_ID': app_id,
        'PREFIX': prefix,
        'PROFILE': profile,
        'LOCALEDIR': localedir,
        'BINDIR': bindir,
    },
)

subdir('data')
subdir('hotbar')
subdir('po')

gnome.post_install(
    glib_compile_schemas: true,
    gtk_update_icon_cache: true,
    update_desktop_database: true,
)
