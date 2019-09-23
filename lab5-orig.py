import socket
import tkinter
import tkinter.font

DEFAULT_STYLE = """
p { margin-bottom: 16px; }
ul { margin-top: 16px; margin-bottom: 16px; padding-left: 20px; }
html {font-style: normal; }
body {font-style: normal; }
i { display: inline; font-style: italic; }
b { display: inline; font-weight: bold; }
a { color:blue; }

h1 {display: block;
margin-top: 5px;
margin-bottom: 16px;
margin-left: 0;
margin-right: 0;
font-weight: bold;
}
h2 { display: block;
font-size: 1.5em;
margin-top: 0.83em;
margin-bottom: 0.83em;
margin-left: 0;
margin-right: 0;
font-weight: bold;
}
"""

def parse_url(url):
    assert url.startswith("http://")
    url = url[len("http://"):]
    hostport, pathfragment = url.split("/", 1) if "/" in url else (url, "")
    host, port = hostport.rsplit(":", 1) if ":" in hostport else (hostport, "80")
    path, fragment = ("/" + pathfragment).rsplit("#", 1) if "#" in pathfragment else ("/" + pathfragment, None)
    return host, int(port), path, fragment

def request(host, port, path):
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    s.connect((host, port))
    s.send("GET {} HTTP/1.0\r\nHost: {}\r\n\r\n".format(path, host).encode("utf8"))
    response = s.makefile("rb").read().decode("utf8")
    s.close()

    head, body = response.split("\r\n\r\n", 1)
    lines = head.split("\r\n")
    version, status, explanation = lines[0].split(" ", 2)
    assert status == "200", "Server error {}: {}".format(status, explanation)
    headers = {}
    for line in lines[1:]:
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    return headers, body

class TagSelector:
    def __init__(self, tag):
        self.tag = tag

    def matches(self, node):
        return self.tag == node.tag
    
    def score(self):
        return 1

class ClassSelector:
    def __init__(self, cls):
        self.cls = cls

    def matches(self, node):
        return self.cls == node.attributes.get("class", "").split()
    
    def score(self):
        return 16

class IdSelector:
    def __init__(self, id):
        self.id = id

    def matches(self, node):
        return self.id == node.id

    def score(self):
        return 256

def css_value(s, i):
    j = i
    while s[j].isalnum() or s[j] == "-" or s[j] == '#':
        j += 1
    return s[i:j], j

def css_whitespace(s, i):
    while i < len(s) and s[i] in " \t\n\f\r\v":
        i += 1
    return None, i

def css_pair(s, i):
    prop, i = css_value(s, i)
    _, i = css_whitespace(s, i)
    assert s[i] == ":"
    i += 1
    _, i = css_whitespace(s, i)
    val, i = css_value(s, i)

    return (prop, val), i

def css_body(s, i):
    pairs = dict()
    assert s[i] == "{"
    _, i = css_whitespace(s, i+1)
    while True:
        if s[i] == "}": break

        try:
            (prop, val), i = css_pair(s, i)
            pairs[prop] = val
            _, i = css_whitespace(s, i)
            assert s[i] == ";"
            _, i = css_whitespace(s, i+1)
        except AssertionError:
            while s[i] not in [";", "}"]:
                i += 1
            if s[i] == ";":
                _, i = css_whitespace(s,i + 1)
    assert s[i] == "}"
    return pairs, i+1

def css_selector(s, i):
    if s[i] == "#":
        name, i = css_value(s, i+1)
        return IdSelector(name), i
    elif s[i] == ".":
        name, i = css_value(s, i+1)
        return ClassSelector(name), i
    else:
        name, i = css_value(s, i)
        return TagSelector(name), i

def parse_css(s):
    i = 0
    styles = []
    _, i = css_whitespace(s,i)
    while i < len(s):
        # Eat whitespace
       
        selector, i = css_selector(s,i)
        _, i = css_whitespace(s,i)
        try: 
            body, i = css_body(s,i)
            styles.append((selector,body))
        except AssertionError:
            _, i = css_whitespace(s,i)
            while s[i] != "}":
                i += 1
            i += 1
        _, i = css_whitespace(s,i)
    return styles

class Text:
    def __init__(self, text):
        self.text = text

class Tag:
    def __init__(self, tag):
        self.tag = tag

def lex(source):
    out = []
    text = ""
    in_angle = False
    for c in source:
        if c == "<":
            in_angle = True
            if text: out.append(Text(text))
            text = ""
        elif c == ">":
            in_angle = False
            out.append(Tag(text))
            text = ""
        else:
            text += c
    return out

# Lab X
class InputLayout:
    def __init__(self, node, multiline=False):
        self.children = []
        self.node = node
        self.space = 0
        self.multiline = multiline
        self.w = 200
        self.h = 60 if self.multiline else 20

    def layout(self, x, y):
        self.x = x
        self.y = y

    def attach(self, parent):
	    self.parent = parent
	    parent.children.append(self)
	    parent.w += self.w

    def add_space(self):
	    if self.space == 0:
	        gap = 5
	        self.space = gap
	        self.parent.w += gap

    def display_list(self):
        border = DrawRect(self.x, self.y, self.x + self.w, self.y + self.h)
        return [border]

    def input(self, node):
        tl = InputLayout(node, node.tag == "textarea")
        line = self.children[-1]
        if line.w + tl.w > self.w:
            line = LineLayout(self)
        tl.attach(line)
# End Lab X

INHERITED_PROPERTIES = [ ("font-style", "normal"),
                         ("font-weight", "normal"),
                         ("color", "black") ]
def style(node, rules):
    if not isinstance(node, ElementNode): return
    rules.sort(key=lambda x: x[0].score())
    for selector, pairs in rules:
        if selector.matches(node):
            for property in pairs:
                node.style[property] = pairs[property]
    for property, value in node.compute_style().items():
        node.style[property] = value
    for (prop, defautl) in INHERITED_PROPERTIES:
        if prop not in node.style:
            if node.parent is None:
                node.style[prop] = default
            else:
                node.style[prop] = node.parent.style[prop]
    for child in node.children:
        style(child, rules)

class ElementNode:
    def __init__(self, parent, tagname):
        self.tag, *attrs = tagname.split(" ")
        self.children = []
        self.attributes = {}
        self.parent = parent

        for attr in attrs:
            out = attr.split("=", 1)
            name = out[0]
            val = out[1].strip("\"") if len(out) > 1 else ""
            self.attributes[name.lower()] = val
        self.style = self.compute_style()
        self.style["font-weight"] = "normal"
        self.style["font-style"] = "normal"
        self.style["color"] = "black"

    
    def compute_style(self):
        style = {}
        if self.tag == "p":
            style["margin-bottom"] = "16px"
        if self.tag == "ul":
            style["margin-top"] = style["margin-bottom"] = "16px"
            style["padding-left"] = "20px"
        if self.tag == "li":
            style["margin-bottom"] = "8px"
        if self.tag == "pre":
            style["margin-left"] = style["margin-right"] = "8px"
            style["border-top-width"] = style["border-bottom-width"] = style["border-left-width"] = style["border-right-width"] = "1px"
            style["padding-top"] = style["padding-bottom"] = style["padding-right"] = style["padding-left"] = "8px"

        style_value = self.attributes.get("style", "")
        for line in style_value.split(";"):
            split = line.split(':')
            prop, val = split if len(split) == 2 else (split[0], None)
            style[prop.lower().strip()] = val.strip() if val is not None else None
        return style

    def __str__(self, level = 0):
        result = " "*level+"{}, {}, {{self.style}}".format(self.tag, self.attributes)
        for c in self.children:
            result += "\n" + c.__str__(level+1)
        return result

def parse(tokens):
    current = None
    for tok in tokens:
        if isinstance(tok, Tag):
            if tok.tag.startswith("/"): # Close tag
                tag = tok.tag[1:]
                node = current
                while node is not None and node.tag != tag:
                    node = node.parent
                if not node and current.parent is not None:
                    current = current.parent
                elif node.parent is not None:
                    current = node.parent
            else: # Open tag
                new = ElementNode(current, tok.tag)
                if current is not None: current.children.append(new)
                if new.tag not in ["br", "link", "meta"]:
                    current = new
        else: # Text token
            new = TextNode(current, tok.text)
            current.children.append(new)
    return current

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

def is_inline(node):
    return isinstance(node, TextNode) and not node.text.isspace() or \
        node.style.get("display", "block") == "inline"

def px(something):
    #ROBUST
    try:
        return int(something[:-2])
    except:
        return 0

class BlockLayout:
    def __init__(self, parent, node):
        self.parent = parent
        self.children = []
        parent.children.append(self)

        self.mt = px(node.style.get("margin-top", "0px"))
        self.mr = px(node.style.get("margin-right", "0px"))
        self.mb = px(node.style.get("margin-bottom", "0px"))
        self.ml = px(node.style.get("margin-left", "0px"))

        self.bt = px(node.style.get("border-top-width", "0px"))
        self.br = px(node.style.get("border-right-width", "0px"))
        self.bb = px(node.style.get("border-bottom-width", "0px"))
        self.bl = px(node.style.get("border-left-width", "0px"))

        self.pt = px(node.style.get("padding-top", "0px"))
        self.pr = px(node.style.get("padding-right", "0px"))
        self.pb = px(node.style.get("padding-bottom", "0px"))
        self.pl = px(node.style.get("padding-left", "0px"))

        self.x = parent.content_left()
        self.w = parent.content_width()
        self.h = None
        self.node = node

    def layout(self, y):
        self.y = y
        self.x += self.ml
        self.w -= self.ml + self.mr

        y = self.y + self.bt + self.pt
        if any(is_inline(child) for child in self.node.children):
            layout = InlineLayout(self, self.node)
            layout.layout()
            y += layout.height()
        else:
            for child in self.node.children:
                if isinstance(child, TextNode) and child.text.isspace(): continue
                layout = BlockLayout(self, child)
                y += layout.mt
                layout.layout(y)
                y += layout.height() + layout.mb
        y += self.pb + self.bb
        self.h = y - self.y

    def height(self):
        return self.h

    def display_list(self):
        dl = []
        for child in self.children:
            dl.extend(child.display_list())
        if self.bl > 0: dl.append(DrawRect(self.x, self.y, self.x + self.bl, self.y + self.h))
        if self.br > 0: dl.append(DrawRect(self.x + self.w - self.br, self.y, self.x + self.w, self.y + self.h))
        if self.bt > 0: dl.append(DrawRect(self.x, self.y, self.x + self.w, self.y + self.bt))
        if self.bb > 0: dl.append(DrawRect(self.x, self.y + self.h - self.bb, self.x + self.w, self.y + self.h))
        return dl

    def content_left(self):
        return self.x + self.bl + self.pl
    def content_top(self):
        return self.y + self.bt + self.pt
    def content_width(self):
        return self.w - self.bl - self.br - self.pl - self.pr

class LineLayout:
    def __init__(self, parent):
        self.parent = parent
        self.children = []
        parent.children.append(self)
        self.w = 0

    def layout(self, y):
        self.y = y
        self.x = self.parent.x
        self.h = 0

        x = self.x
        leading = 2
        y += leading / 2
        for child in self.children:
            child.layout(x, y)
            x += child.w + child.space
            self.h = max(self.h, child.h + leading)
        self.w = x - self.x

    def height(self):
        return self.h

    def display_list(self):
        dl = []
        for child in self.children:
            dl.extend(child.display_list())
        return dl
        
class TextNode:
    def __init__(self, parent, text):
        self.text = text
        self.parent = parent
        self.style = self.parent.style

    def __str__(self, level = 0):
        return " "*level + self.text

class TextLayout:
    def __init__(self, node, text):
        self.children = []
        self.node = node
        self.text = text
        bold = node.style["font-weight"] == "bold"
        italic = node.style["font-style"] == "italic"
        self.color = node.style["color"]
        self.font = tkinter.font.Font(
            family="Times", size=16,
            weight="bold" if bold else "normal",
            slant="italic" if italic else "roman"
        )
        self.w = self.font.measure(text)
        self.h = self.font.metrics('linespace')
        self.space = 0

    def height(self):
        return self.h
    
    def add_space(self):
        if self.space == 0:
            gap = self.font.measure(" ")
            self.space = gap
            self.parent.w += gap
            
    def attach(self, parent):
        self.parent = parent
        parent.children.append(self)
        parent.w += self.w
        
    def layout(self, x, y):
        self.x = x
        self.y = y
        
    def display_list(self):
        return [DrawText(self.x, self.y, self.text, self.font, self.color)]
    
class InlineLayout:
    def __init__(self, block, node):
        self.parent = block
        self.parent.children.append(self)
        self.x = block.content_left()
        self.y = block.content_top()
        self.italic = False
        self.terminal_space = True
        self.dl = []
        self.children = []
        LineLayout(self)
        self.w = self.parent.content_width()
        self.node = node

    def font(self):
        return tkinter.font.Font(
            family="Times", size=16,
            weight=self.parent.node.style["font-weight"],
            slant="roman" if self.parent.node.style["font-style"] == "normal" else "italic"
        )

    def height(self):
        font = self.font()
        return (self.y + font.metrics('linespace') * 1.2) - self.parent.y

    def display_list(self):
        return self.dl

    def recurse(self, node):
        if isinstance(node, ElementNode):
            for child in node.children:
                self.recurse(child)
        else:
            self.text(node)

    def text(self, node):
        words = node.text.split()
        if node.text[0].isspace() and len(self.children[-1].children) > 0:
            self.children[-1].children[-1].add_space()

        for i, word in enumerate(words):
            tl  = TextLayout(node, word)
            line = self.children[-1]
            if line.w + tl.w > self.w:
                line = LineLayout(self)
            tl.attach(line)
            if i != len(words) - 1 or node.text[-1].isspace():
                tl.add_space()

    def layout(self):
        self.x = self.parent.content_left()
        self.y = self.parent.content_top()
        self.w = self.parent.content_width()
        self.recurse(self.node)
        y = self.y
        for child in self.children:
            child.layout(y)
            y += child.h
        self.h = y - self.y

    def display_list(self):
        dl = []
        for child in self.children:
            dl.extend(child.display_list())
        return dl

    def content_left(self):
        return self.x + self.bl + self.pl
    def content_top(self):
        return self.y + self.bt + self.pt
    def content_width(self):
        return self.w - self.bl - self.br - self.pl - self.pr
    
class DrawText:
    def __init__(self, x, y, text, font, color):
        self.x = x
        self.y = y
        self.text = text
        self.font = font
        self.color = color
        
    def draw(self, scrolly, canvas):
        canvas.create_text(self.x, self.y - scrolly, text=self.text, font=self.font, anchor='nw', fill = self.color)

class DrawRect:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def draw(self, scrolly, canvas):
        canvas.create_rectangle(self.x1, self.y1 - scrolly, self.x2, self.y2 - scrolly)


def find_element(x, y, layout):
    for child in layout.children:
        result = find_element(x, y, child)
        if result: return result
    if layout.x <= x < layout.x + layout.w and \
       layout.y <= y < layout.y + layout.height():
        return layout.node


def show(nodes):
    window = tkinter.Tk()
    canvas = tkinter.Canvas(window, width=800, height=600)
    canvas.pack()

    # Get styles


    SCROLL_STEP = 100
    scrolly = 0
    styles = parse_css(DEFAULT_STYLE)
    style(nodes, styles)
    page = Page()
    mode = BlockLayout(page, nodes)
    mode.layout(0)
    maxh = mode.height()
    display_list = mode.display_list()
 
    def render():
        canvas.delete("all")
        for cmd in display_list:
            cmd.draw(scrolly, canvas)

    def scrolldown(e):
        nonlocal scrolly
        scrolly = min(scrolly + SCROLL_STEP, 13 + maxh - 600)
        render()

    def scrollup(e):
        nonlocal scrolly
        scrolly = max(scrolly - SCROLL_STEP, 0)
        render()
    
    def handle_click(e):
        x, y = e.x, e.y + scrolly
        elt = find_element(x, y, nodes)
        while elt and not \
              (isinstance(elt, ElementNode) and elt.tag == "a" and "href" in elt.attributes):
            elt = elt.parent
        if elt:
            print(elt.attributes["href"])
        
    window.bind("<Down>", scrolldown)
    window.bind("<Up>", scrollup)
    window.bind("<Button-1>", handle_click)
    render()

    tkinter.mainloop()

def run(url):
    host, port, path, fragment = parse_url(url)
    headers, body = request(host, port, path)
    text = lex(body)
    nodes = parse(text)
    show(nodes)
"""
"""
def test_css():
        print(parse_css("""
html { margin: 0; padding: 0; background: #f6f6f6; color: #2e3436; }

body {
    padding: 0 10px 5em; max-width: 35em; margin: 0 auto; line-height: 1.5;
    font-weight: 200; font-size: 22px; font-family: "Merriweather", serif;
    text-rendering: optimizeLegibility;
    }
    #table-of-contents ul { margin: 0; }
.drawer { padding: 20px; margin: 1em 0; background-color: #5c3566; color: #eeeeec; }
#table-of-contents h2 { font-size: 100%; font-variant: small-caps; }
#table-of-contents li { margin: .25em; font-size: 90%; }
"""))

if __name__ == "__main__":
    import sys
    run("http://pavpanchekha.com/blog/emberfox/chrome.html")
