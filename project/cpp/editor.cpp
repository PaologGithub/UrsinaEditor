#include "emscriptenmodule.c"
#include "browsermodule.c"

#include "Python.h"
#include <emscripten.h>

extern PyObject *PyInit_core();
extern PyObject *PyInit_direct();
//extern PyObject *PyInit_physics();

extern void init_libOpenALAudio();
extern void init_libpnmimagetypes();
extern void init_libwebgldisplay();

extern void task_manager_poll();

static void setup_ursina_emscripten(void)
{
    PyRun_SimpleString(
        "def _setup():\n"
        "    from ursina import application\n"
        "    from pathlib import Path\n"
        "    ursina_assets = Path('assets/ursina_assets')\n"
        "    game_assets   = Path('assets/game_assets')\n"
        "    application.package_folder = ursina_assets\n"
        "    application.asset_folder   = game_assets\n"
        "    application.scenes_folder  = game_assets / 'scenes/'\n"
        "    application.scripts_folder = game_assets / 'scripts/'\n"
        "    application.fonts_folder   = game_assets / 'fonts/'\n"
        "    application.internal_models_folder            = ursina_assets / 'models/'\n"
        "    application.internal_models_compressed_folder = ursina_assets / 'models_compressed/'\n"
        "    application.internal_scripts_folder           = ursina_assets / 'scripts/'\n"
        "    application.internal_textures_folder          = ursina_assets / 'textures/'\n"
        "    application.internal_fonts_folder             = ursina_assets / 'fonts/'\n"
        "    application.internal_audio_folder             = ursina_assets / 'audio/'\n"
        "_setup()\n"
        "del _setup\n"
    );
}

EMSCRIPTEN_KEEPALIVE void loadPython() {
    PyConfig config;
    PyConfig_InitIsolatedConfig(&config);
    config.pathconfig_warnings = 0;
    config.use_environment = 0;
    config.write_bytecode = 0;
    config.site_import = 0;
    config.user_site_directory = 0;
    config.buffered_stdio = 0;

    PyStatus status = Py_InitializeFromConfig(&config);
    if (!PyStatus_Exception(status)) {
        fprintf(stdout, "Python %s\\n", Py_GetVersion());

        EM_ASM({
            Module.setStatus('Importing Panda3D...');
            window.setTimeout(_loadPanda, 0);
        });
    }
    PyConfig_Clear(&config);
}

EMSCRIPTEN_KEEPALIVE void loadPanda() {
    PyObject *panda3d_module = PyImport_AddModule("panda3d");
    PyModule_AddStringConstant(panda3d_module, "__package__", "panda3d");
    PyModule_AddObject(panda3d_module, "__path__", PyList_New(0));

    PyObject *sys_modules = PySys_GetObject("modules");
    PyDict_SetItemString(sys_modules, "panda3d", panda3d_module);

    PyObject *panda3d_dict = PyModule_GetDict(panda3d_module);

    PyObject *core_module = PyInit_core();
    PyModule_AddStringConstant(core_module, "__name__", "panda3d.core");
    PyDict_SetItemString(panda3d_dict, "core", core_module);
    PyDict_SetItemString(sys_modules, "panda3d.core", core_module);

    PyObject *direct_module = PyInit_direct();
    PyModule_AddStringConstant(direct_module, "__name__", "panda3d.direct");
    PyDict_SetItemString(panda3d_dict, "direct", direct_module);
    PyDict_SetItemString(sys_modules, "panda3d.direct", direct_module);

    //PyObject *physics_module = PyInit_physics();
    //PyDict_SetItemString(panda3d_dict, "physics", physics_module);

    PyDict_SetItemString(sys_modules, "panda3d.core", core_module);
    PyDict_SetItemString(sys_modules, "panda3d.direct", direct_module);

    PyDict_SetItemString(sys_modules, "emscripten", PyInit_emscripten());
    PyDict_SetItemString(sys_modules, "browser", PyInit_browser());

    init_libOpenALAudio();
    init_libpnmimagetypes();
    init_libwebgldisplay();

    EM_ASM({
        Module.setStatus('Done!');
    });
}

EMSCRIPTEN_KEEPALIVE void stopPythonCode() {
    emscripten_cancel_main_loop();
    PyRun_SimpleString(
        "import gc\n"
        "try:\n"
        "    from panda3d.core import GraphicsEngine\n"
        "    engine = GraphicsEngine.get_global_ptr()\n"
        "    for win in engine.get_windows():\n"
        "        win.set_clear_color_active(True)\n"
        "        win.set_clear_color((0, 0, 0, 1))\n"
        "    engine.render_frame()\n"
        "    engine.render_frame()\n"
        "except Exception as e:\n"
        "    print('Failed to clear screen:', e)\n"
        "def free():\n"
        "    g = globals()\n"
        "    for name in list(g.keys()):\n"
        "        if not name.startswith('__') and name not in ('free',):\n"
        "            del g[name]\n"
        "free() \n"
        "gc.collect()\n"
    );

    Py_Finalize();
    loadPython();
}

EMSCRIPTEN_KEEPALIVE void runPythonCode(char *codeToExecute)
{
    // setup AFTER everything is ready
    setup_ursina_emscripten();

    if (PyRun_SimpleString(codeToExecute)) {
        stopPythonCode();
    } else {
        emscripten_set_main_loop(&task_manager_poll, 0, 0);
        EM_ASM({
            document.getElementById('stop-button').disabled = false;
        });
    }
}