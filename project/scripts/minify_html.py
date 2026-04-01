import shutil
from html.parser import HTMLParser

from html.parser import HTMLParser
import requests
import json

def minify(url, code) -> str:
    try:
        resp = requests.post(
            url,
            data={"input": code},
            timeout=5
        )
        if resp.ok:
            return resp.text
    except Exception as e:
        print("Minify failed:", e)
    return code  # fallback

class HTMLMinifier(HTMLParser):
    js_config = {
        "jsc": {
            "minify": {
                "mangle": True,
                "compress": True
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.result = []
        self.current_tag = None
        self.buffer = []

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attrs_str = "".join(f' {k}="{v}"' for k, v in attrs)
        self.result.append(f"<{tag}{attrs_str}>")

    def handle_endtag(self, tag):
        if self.current_tag in ("script", "style"):
            # Minify the content buffer
            code = "".join(self.buffer)
            if self.current_tag == "script":
                minified = self.minify_js(code)
            else:
                minified = self.minify_css(code)
            self.result.append(minified)
            self.buffer = []

        self.result.append(f"</{tag}>")
        self.current_tag = None

    def handle_data(self, data):
        if self.current_tag in ("script", "style"):
            self.buffer.append(data)
        else:
            self.result.append(data)

    def get_html(self):
        return "".join(self.result)

    def minify_js(self, code):
        return minify("https://www.toptal.com/developers/javascript-minifier/api/raw", code)

    def minify_css(self, code: str) -> str:
        return minify("https://www.toptal.com/developers/cssminifier/api/raw", code)

minifier = HTMLMinifier()
with open("built/index.html", "r") as file:
    content = file.read()
    minifier.feed(content)

shutil.move("built/index.html", "built/index.html.max")
with open("built/index.html", "w") as file:
    file.write(minifier.get_html())

js = ""
with open("built/game.js", "r") as file:
    content = file.read()
    js = minify("https://www.toptal.com/developers/javascript-minifier/api/raw", content)

shutil.move("built/game.js", "built/game.js.max")
with open("built/game.js", "w") as file:
    file.write(js)