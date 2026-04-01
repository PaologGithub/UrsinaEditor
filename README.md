# Ursina for Web
It doesn't work now

Just, before building, extract project/emscripten.zip to the folder `emscripten`, so that there are both these folders:
- `project/emscripten/embuilt`
- `project/emscripten/emscripten-libs`
Extract `ursina.tar.xz` too, so that you get these files:
- `src/ursina/audio/...`
- `src/ursina/editor/...`

## Production
For production games, I made a simple tool called `project/scripts/minify_html.py`. It converts the /built/index.html into a minified version of it,
so that you don't have to download a lot of data. For the base html, it gives ~41.1% of compression. (This is still in development)