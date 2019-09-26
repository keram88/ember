import tkinter
import tkinter.font
import dukpy
from network import parse_url, request
from html import lex, parse
from style import style, parse_css
from layout import BlockLayout, is_checkbox, is_checked
from html import ElementNode
from timing import Timer

with open('default.css', 'r') as f:
    DEFAULT_STYLE = f.read()

with open('runtime.js', 'r') as f:
    DEFAULT_JS = f.read()

class Page:
    def __init__(self):
        self.x = 13
        self.y = 13
        self.w = 774
        self.children = []

    def content_left(self):
        return self.x
    def content_top(self):
        return self.y
    def content_width(self):
        return self.w

def find_element(x, y, layout):
    if hasattr(layout, "children"):
        for child in layout.children:
            result = find_element(x, y, child)
            if result: return result
    if hasattr(layout, "node") and layout.x <= x < layout.x + layout.w and \
       layout.y <= y < layout.y + layout.height():
        return layout.node

def is_layout(c):
    return (isinstance(c, TextLayout) or
            isinstance(c, LineLayout) or
            isinstance(c, BlockLayout) or
            isinstance(c, InlineLayout) or
            isinstance(c, InputLayout))

def edit_input(elt):
    new_text = input("Enter new text: ")
    if elt.tag == "input":
        elt.attributes["value"] = new_text
    else:
        elt.children = [TextNode(elt, new_text)]

def find_inputs(elt, out):
    if not isinstance(elt, ElementNode): return
    if (elt.tag == 'input' or elt.tag == 'textarea') and 'name' in elt.attributes:
        out.append(elt)
    for child in elt.children:
        find_inputs(child, out)
    return out

def find_selected(node, sel, out):
    if not isinstance(node, ElementNode): return
    if sel.matches(node):
        out.append(node)
    for child in node.children:
        find_selected(child, sel, out)
    return out

def relative_url(url, current):
    url = url.replace('"', '').replace("'", '')

    if url.startswith("http://"):
        return url    
    current = current.replace('http://', '')
    if url == '/':
        return 'http://' + current.split('/')[0] + url
    elif url.startswith("/"):
        return 'http://' + "/".join(current.split("/")) + url
    else:
        return 'http://' + current.rsplit("/", 1)[0] + "/" + url

def find_scripts(node, out):
    if not isinstance(node, ElementNode): return
    if node.tag == "script" and \
       "src" in node.attributes:
        out.append(node.attributes["src"])
    for child in node.children:
        find_scripts(child, out)
    return out

SCROLL_STEP = 100

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=800, height=600)
        self.canvas.pack()
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Button-3>", self.go_back)
        self.history = []
        self.scrolly = 0
        self.maxh = 0
        self.timer=Timer()

    def go_back(self, e):
        if len(self.history) < 2:
            return
        current, s_type1, post = self.history.pop()
        # browse puts this back
        last, s_type2, post2 = self.history.pop()
        if s_type1 is not None:
            if s_type1 == 'post':
                result = input("Resending POST data. Confirm: ")
                if result.lower() != "yes":
                    self.history.append((last, s_type2, post2))
                    self.history.append((current, s_type1, post))
                    return
                else:
                    print("OK!!!")
                    self.send_post(current, post)
                    return
            else:
                self.browse(current, 'get', post)
        self.browse(last, s_type2, post2)

    def browse(self, url, s_type=None, post=None):
        try:
            host, port, path, fragment = parse_url(url)
            self.timer.start("Downloading")
            headers, body = request('GET', host, port, path)
            self.timer.stop()
        except AssertionError:
            return
        self.headers = headers
        self.body = body
        self.url = url
        self.history.append((url, s_type, post))

        self.parse()

    def parse(self):
        self.timer.start("HTML")
        self.text = lex(self.body)
        self.timer.stop()
        self.nodes = parse(self.text)
        self.timer.start("Parse CSS")
        self.rules = parse_css(DEFAULT_STYLE)
        self.timer.stop()
        self.rules.sort(key=lambda x: x[0].score())
        self.timer.start("JS")
        self.js = dukpy.JSInterpreter()
        self.js_handles = dict()
        
        # Registration
        self.js.export_function("log", print)
        self.js.export_function("querySelectorAll", self.js_querySelectorAll)

        # Run runtime
        self.js.evaljs(DEFAULT_JS)
        
        for script in find_scripts(self.nodes, []):
            lhost, lport, lpath, lfragment = parse_url(relative_url(script, self.history[-1]))
            header, body = request('GET', lhost, lport, lpath)
            self.js.evaljs(body)
        self.timer.stop()
        self.relayout()

    def js_querySelectorAll(self,sel):
        selector, _ = css_selector(sel + "{", 0)
        elts = find_selected(self.nodes, selector, [])
        out = []
        for elt in elts:
            if not elt.handle:
                handle = len(self.js_handles) + 1
                elt.handle = handle
                self.js_handles[handle] = elt
            out.append(handle)
        return out

    def js_getAttribute(self, handle, attr):
        elt = self.js_handles[handle]
        return elt.attributes.get(attr, None)
    
    def relayout(self):
        self.timer.start("Style")
        style(self.nodes, self.rules)
        self.timer.stop()

        self.page = Page()
        self.layout = BlockLayout(self.page, self.nodes)
        self.timer.start("Layout1")
        self.layout.layout1()
        self.timer.stop()
        self.timer.start("Layout2")
        self.layout.layout2(0)
        self.timer.stop()
        self.maxh = self.layout.height()
        self.timer.start("Display list")
        self.display_list = self.layout.display_list()
        self.timer.stop()
        self.render()

    def render(self):
        self.timer.start("Render")
        self.canvas.delete("all")
        for cmd in self.display_list:
            if cmd.y2 - self.scrolly < 0: continue
            if cmd.y2 - self.scrolly > 600: continue
            cmd.draw(self.scrolly, self.canvas)
        self.timer.stop()

    def scrolldown(self, e):
        self.scrolly = min(self.scrolly + SCROLL_STEP, 13 + self.maxh - 600)
        self.render()

    def scrollup(self, e):
        self.scrolly = max(self.scrolly - SCROLL_STEP, 0)
        self.render()
    
    def handle_click(self, e):
        x, y = e.x, e.y + self.scrolly
        elt = find_element(x, y, self.layout)
        while elt and not \
              (isinstance(elt, ElementNode) and ((elt.tag == "a" and "href" in elt.attributes)
                                                 or elt.tag in ("input", "textarea", "button"))):
            elt = elt.parent
        if not elt:
            pass
        elif elt.tag == 'a':
            # Follow link!
            url = relative_url(elt.attributes["href"], self.history[-1][0])
            self.browse(url)
        # lab x
        elif elt.tag in ("input", "textarea"):
            if is_checkbox(elt): # EX 1
                if is_checked(elt):
                    del elt.attributes["checked"]
                else:
                    elt.attributes["checked"] = ""
            else:
                edit_input(elt)
            self.relayout()
        elif elt.tag == 'button':
            self.submit_form(elt)
        else:
            pass

    def submit_form(self, elt):
        while elt and elt.tag != 'form':
            elt = elt.parent
        if not elt: return

        # EX 2
        method = elt.attributes.get('method', 'get').lower()
        if method not in ('get', 'post'):
            # "Sane" default
            method = 'get'

        inputs = []
        find_inputs(elt, inputs)
        params = dict()
        for input in inputs:
            # EX 1
            if input.tag == 'input':
                if is_checkbox(input):
                    if is_checked(input):
                        params[input.attributes['name']] = ''
                else:
                    params[input.attributes['name']] = input.attributes.get('value', '')
            else:
                params[input.attributes['name']] = input.children[0].text if input.children else ""
        url = relative_url(elt.attributes['action'], self.history[-1][0])
        # EX 2
        if method == 'get':
            host, port, path, fragment = parse_url(url)
            get = self.format_post(params)
            nurl = "http://" + host + ":" + str(port) + path + "?" + get + (fragment if fragment is not None else "")
            self.browse(nurl, 'get')
            
        else:
            body = self.format_post(params)
            self.send_post(url, body)

    def format_post(self, params):
        body = ""
        for param, value in params.items():
            body += "&" + param + "="
            body += value.replace(" ", "%20")
        body = body[1:]
        return body

    def send_post(self, url, body):
        host, port, path, fragment = parse_url(url)
        self.headers, self.body = request('POST', host, port, path, body)
        self.history.append((url, 'post', body))
        self.parse()

if __name__ == "__main__":
    import sys
    browser = Browser()
    if len(sys.argv) > 1:
        browser.browse(sys.argv[1])
    else:
        #browser.browse("http://pavpanchekha.com/blog/emberfox/chrome.html")
        browser.browse("http://kepler.cs.utah.edu:9000")
    tkinter.mainloop()
