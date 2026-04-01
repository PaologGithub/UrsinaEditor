from direct.dist import FreezeTool
import sys, os, shutil
import tomllib

if sys.version_info[:2] != (3, 13):
    sys.exit("Run this with Python 3.13, or edit this script")

content: dict = dict()
with open("project/settings.toml", "rb") as file:
    content = tomllib.load(file)

# [game] part
app_name_set: str      = content["game"]["name"]
app_icon: str          = content["game"]["icon"]
# [application] part
app_pyfile: str        = content["application"]["startfile"]

# Thirdparty libraries
THIRDPARTY_DIR = "./project/emscripten/emscripten-libs"

# Python built for target
PY_INCLUDE_DIR = THIRDPARTY_DIR + "/python/include/python3.13"
PY_LIB_DIR = THIRDPARTY_DIR + "/python/lib"
PY_LIBS = "libpython3.13.a", "libmpdec.a", "libexpat.a", "libHacl_Hash_SHA2.a"

# Python extension modules
PY_MODULE_DIR = PY_LIB_DIR + "/python/lib/python3.13/lib-dynload"
PY_STDLIB_DIR = PY_LIB_DIR + "/python/lib/python3.13"
PY_MODULES = []

# Panda modules / libraries
PANDA_BUILT_DIR = "./project/emscripten/embuilt"
PANDA_MODULES = ["core", "direct" ] #, "bullet"]
PANDA_LIBS = ["libpanda", "libpandaexpress", "libp3dtool", "libp3dtoolconfig", "libp3webgldisplay", "libp3direct", "libp3openal_audio"]
PANDA_STATIC = True # built with --static

# Ursina module
URSINA_SRC_DIR = "./src"

# Increase this when emscripten complains about running out of memory
INITIAL_HEAP = 83886080
STACK_SIZE = 1048576

# Increase this to get useful debugging info when crashes occur
ASSERTIONS = 0

# Files to preload into the virtual filesystem
# You don't need to preload these files anymore, Panda3D will happily read them
# from the web server instead, but preloading is considerably more efficient.
PRELOAD_FILES = []

for assets_root in ("assets/ursina_assets", "assets/game_assets"):
    for root, dirs, files in os.walk(assets_root):
        for fname in files:
            PRELOAD_FILES.append(os.path.join(root, fname))


class EmscriptenEnvironment:
    platform = 'emscripten'

    pythonInc = PY_INCLUDE_DIR
    pythonLib = ""
    for lib in PY_LIBS:
        lib_path = PY_LIB_DIR + "/" + lib
        if os.path.isfile(lib_path):
            pythonLib += lib_path + " "

    modStr = " ".join((os.path.join(PY_MODULE_DIR, a + ".cpython-313.o") for a in PY_MODULES))

    pandaFlags = ""
    for mod in PANDA_MODULES:
        if PANDA_STATIC:
            pandaFlags += f" {PANDA_BUILT_DIR}/lib/libpy.panda3d.{mod}.cpython-313-wasm32-emscripten.a"
        else:
            pandaFlags += f" {PANDA_BUILT_DIR}/panda3d/{mod}.cpython-313-wasm32-emscripten.o"

    for lib in PANDA_LIBS:
        pandaFlags += f" {PANDA_BUILT_DIR}/lib/{lib}.a"

    pandaFlags += f" -I{PANDA_BUILT_DIR}/include"
    pandaFlags += " -s USE_ZLIB=1 -s USE_VORBIS=1 -s USE_LIBPNG=1 -s USE_FREETYPE=1 -s USE_HARFBUZZ=1 -s USE_SQLITE3=1 -s USE_BZIP2=1 -s ERROR_ON_UNDEFINED_SYMBOLS=0 -s DISABLE_EXCEPTION_THROWING=0"

    pandaFlags += " -s 'EXPORTED_RUNTIME_METHODS=[\"cwrap\"]'"

    for file in PRELOAD_FILES:
        pandaFlags += " --preload-file " + file

    compileObj = f"emcc -O3 -fno-exceptions -fno-rtti -c -o %(basename)s.o %(filename)s -I{pythonInc}"
    linkExe = f"emcc --bind -O3 -s INITIAL_HEAP={INITIAL_HEAP} -s STACK_SIZE={STACK_SIZE} -s ASSERTIONS={ASSERTIONS} -s MAX_WEBGL_VERSION=2 -s NO_EXIT_RUNTIME=1 -fno-exceptions -fno-rtti -o %(basename)s.js %(basename)s.o {modStr} {pythonLib} {pandaFlags}"
    linkDll = f"emcc -O2 -shared -o %(basename)s.o %(basename)s.o {pythonLib}"

    # Paths to Python stuff.
    Python = None
    PythonIPath = pythonInc
    PythonVersion = "3.13"

    suffix64 = ''
    dllext = ''
    arch = ''

    def compileExe(self, filename, basename, extraLink=[]):
        compile = self.compileObj % {
            'python' : self.Python,
            'filename' : filename,
            'basename' : basename,
            }
        print(compile, file=sys.stderr)
        if os.system(compile) != 0:
            raise Exception('failed to compile %s.' % basename)

        link = self.linkExe % {
            'python' : self.Python,
            'filename' : filename,
            'basename' : basename,
            }
        link += ' ' + ' '.join(extraLink)
        print(link, file=sys.stderr)
        if os.system(link) != 0:
            raise Exception('failed to link %s.' % basename)

    def compileDll(self, filename, basename, extraLink=[]):
        compile = self.compileObj % {
            'python' : self.Python,
            'filename' : filename,
            'basename' : basename,
            }
        print(compile, file=sys.stderr)
        if os.system(compile) != 0:
            raise Exception('failed to compile %s.' % basename)

        link = self.linkDll % {
            'python' : self.Python,
            'filename' : filename,
            'basename' : basename,
            'dllext' : self.dllext,
            }
        link += ' ' + ' '.join(extraLink)
        print(link, file=sys.stderr)
        if os.system(link) != 0:
            raise Exception('failed to link %s.' % basename)


freezer = FreezeTool.Freezer()
freezer.frozenMainCode = """
#include "project/cpp/editor.cpp"
int Py_FrozenMain(int argc, char **argv)
{
    EM_ASM({
        Module.setStatus('Starting Python...');
        window.setTimeout(_loadPython, 0);
    });

    return 0;
}
"""

freezer.moduleSearchPath = [PANDA_BUILT_DIR, URSINA_SRC_DIR, PY_STDLIB_DIR, PY_MODULE_DIR]

# Set this to keep the intermediate .c and .o file
#freezer.keepTemporaryFiles = True

freezer.cenv = EmscriptenEnvironment()
freezer.excludeModule('doctest')
freezer.excludeModule('difflib')
freezer.excludeModule('panda3d')
freezer.addModule('__main__', filename=app_pyfile)

freezer.done(addStartupModules=True)
freezer.generateCode("editor", compileToExe=True)

built_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "built")
if not os.path.exists(built_path):
    os.mkdir(built_path)


shutil.move("editor.data", os.path.join(built_path, "editor.data"))
shutil.move("editor.js", os.path.join(built_path, "editor.js"))
shutil.move("editor.wasm", os.path.join(built_path, "editor.wasm"))
shutil.copy(app_icon, os.path.join(built_path, os.path.basename(app_icon)))

with open("assets/index.html", "r") as file:
    content = file.read()
    
    content = content.replace("{{TITLE}}", app_name_set)
    content = content.replace("{{LOGO}}", os.path.basename(app_icon))

    new_file = open(os.path.join(built_path, "index.html"), "w")
    new_file.write(content)