import tkinter
import tkinter.font
from html import TextNode, ElementNode
from graphics import DrawText, DrawRect
from timing import Timer

METRIC_CACHE = dict()
GAP_CACHE = dict()

def px(something):
    #ROBUST
    try:
        return int(something[:-2])
    except:
        return 0

def is_inline(node):
    return isinstance(node, TextNode) and not node.text.isspace() or \
        node.style.get("display", "block") == "inline"

def is_checkbox(node):
    return node.tag == "input" and node.attributes.get("type", "") == "checkbox"

def is_checked(node):
    return is_checkbox(node) and "checked" in node.attributes.keys()

class BlockLayout:
    def __init__(self, parent, node):
        self.parent = parent
        self.mt = px(node.style.get("margin-top", "0px"))
        self.mb = px(node.style.get("margin-bottom", "0px"))
        self.x = parent.content_left()
        self.h = None
        self.node = node
        self.timer = Timer()
        
    # def layout1(self):
    #     y = 0
    #     self.y = y
    #     self.x += self.ml
    #     self.w -= self.ml + self.mr

    #     y = self.y + self.bt + self.pt
    #     if any(is_inline(child) for child in self.node.children):
    #         layout = InlineLayout(self, self.node)
    #         layout.layout()
    #         y += layout.height()
    #     else:
    #         for child in self.node.children:
    #             if isinstance(child, TextNode) and child.text.isspace(): continue
    #             layout = BlockLayout(self, child)
    #             y += layout.mt
    #             layout.layout(y)
    #             y += layout.height() + layout.mb
    #     y += self.pb + self.bb
    #     self.h = y - self.y

    def layout1(self):
        self.children = []
        self.parent.children.append(self)
        self.mt = px(self.node.style.get("margin-top", "0px"))
        self.mr = px(self.node.style.get("margin-right", "0px"))
        self.mb = px(self.node.style.get("margin-bottom", "0px"))
        self.ml = px(self.node.style.get("margin-left", "0px"))
        
        self.bt = px(self.node.style.get("border-top-width", "0px"))
        self.br = px(self.node.style.get("border-right-width", "0px"))
        self.bb = px(self.node.style.get("border-bottom-width", "0px"))
        self.bl = px(self.node.style.get("border-left-width", "0px"))
        
        self.pt = px(self.node.style.get("padding-top", "0px"))
        self.pr = px(self.node.style.get("padding-right", "0px"))
        self.pb = px(self.node.style.get("padding-bottom", "0px"))
        self.pl = px(self.node.style.get("padding-left", "0px"))
        self.w = self.parent.content_width()
        
        y = 0
        self.y = 0
        self.x += self.ml
        self.w -= self.ml + self.mr

        y = self.y + self.bt + self.pt
        if any(is_inline(child) for child in self.node.children):
            layout = InlineLayout(self, self.node)
            layout.layout1()
            y += layout.height()
        else:
            for child in self.node.children:
                if isinstance(child, TextNode) and child.text.isspace(): continue
                layout = BlockLayout(self, child)
                y += layout.mt
                layout.layout1()
                y += layout.height() + layout.mb
        y += self.pb + self.bb
        self.h = y - self.y
        
    def layout2(self,y):
        self.x = self.parent.content_left()
        self.y = y
        self.x += self.ml
        self.y += self.mt
        y = self.y
        for child in self.children:
            child.layout2(y)
            y += child.h + (child.mt + child.mb if isinstance(child, BlockLayout) else 0)

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
        parent.children.append(self)
        self.w = 0
        self.children = []

    def layout1(self):
        self.h = 0
        leading = 2
        for child in self.children:
            self.h = max(self.h, child.h + leading)

    def layout2(self, y):
        self.y = y
        self.x = self.parent.x

        x = self.x
        leading = 2
        y += leading / 2
        for child in self.children:
            child.layout2(x, y)
            x += child.w + child.space
        self.w = x - self.x

    def height(self):
        return self.h

    def display_list(self):
        dl = []
        for child in self.children:
            dl.extend(child.display_list())
        return dl
        
class TextLayout:
    def __init__(self, node, text):
        self.children = []
        self.node = node
        self.text = text
        self.space = 0
        self.bold = node.style["font-weight"] == "bold"
        self.italic = node.style["font-style"] == "italic"
        self.color = node.style["color"]
        self.font = tkinter.font.Font(
            family="Times", size=16,
            weight="bold" if self.bold else "normal",
            slant="italic" if self.italic else "roman"
        )
        key = (self.bold, self.italic, text)
        if key in METRIC_CACHE.keys():
            self.h, self.w = METRIC_CACHE[key]
        else:
            self.h = self.font.metrics('linespace')
            self.w = self.font.measure(text)
            METRIC_CACHE[key] = (self.h, self.w)


    def height(self):
        assert(len(self.children) == 0)
        return self.h
    
    def add_space(self):
        if (self.bold, self.italic) in GAP_CACHE.keys():
            gap = GAP_CACHE[(self.bold, self.italic)]
        else:
            gap = self.font.measure(" ")
            GAP_CACHE[(self.bold, self.italic)] = gap
        self.space = gap
        self.parent.w += gap
            
    def attach(self, parent):
        self.parent = parent
        parent.children.append(self)
        parent.w += self.w
        
    def layout1(self):
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

    def layout2(self, x, y):
        self.x = x
        self.y = y
        
    def display_list(self):
        return [DrawText(self.x, self.y, self.text, self.font, self.color, self.h)]
    
class InlineLayout:
    def __init__(self, block, node):
        self.parent = block
        self.parent.children.append(self)
        self.x = block.content_left()
        self.y = block.content_top()
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
        return self.h

    def recurse(self, node):
        # Input box lab x
        if isinstance(node, ElementNode) and node.tag in ("input", "textarea", "button"):
            self.input(node)
        elif isinstance(node, ElementNode):
            for child in node.children:
                self.recurse(child)
        else:
            self.text(node)
    # lab x
    def input(self, node):
        tl = InputLayout(node, node.tag == "textarea")
        line = self.children[-1]
        if line.w + tl.w > self.w:
            line = LineLayout(self)
        tl.attach(line)

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


    def layout1(self):
        self.children = []
        LineLayout(self)
        self.w = self.parent.content_width()
        self.recurse(self.node)
        h = 0
        for child in self.children:
            child.layout1()
            h += child.h
        self.h = h
        
    def layout2(self, y):
        self.x = self.parent.content_left()
        self.y = self.parent.content_top()
        y = self.y
        for child in self.children:
            child.layout2(y)
            y += child.h

    # def layout(self):
    #     self.x = self.parent.content_left()
    #     self.y = self.parent.content_top()
    #     self.w = self.parent.content_width()
    #     self.recurse(self.node)
    #     y = self.y
    #     for child in self.children:
    #         child.layout(y)
    #         y += child.h
    #     self.h = y - self.y

    def display_list(self):
        dl = []
        for child in self.children:
            assert(isinstance(child, LineLayout))
            dl.extend(child.display_list())
        return dl

    def content_left(self):
        return self.x + self.bl + self.pl

    def content_top(self):
        return self.y + self.bt + self.pt
    def content_width(self):
        return self.w - self.bl - self.br - self.pl - self.pr

class InputLayout:
    def __init__(self, node, multiline=False):
        self.children = []
        self.node = node
        self.space = 0
        self.multiline = multiline
        # EX 1

    def layout1(self):
        self.child_layout = []
        if is_checkbox(self.node):
            self.w = 20
        else:
            self.w = 200
        self.h = 60 if self.multiline else 20
        for child in self.node.children:
            layout = InlineLayout(self, child)
            self.child_layout.append(layout)
            layout.layout1()
            
    def layout2(self, x, y):
        self.x = x
        self.y = y
        for child in self.child_layout:
            child.layout2()

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
        if self.children:
            dl = []
            for child in self.children:
                dl.extend(child.display_list())
            dl.append(border)
            return dl
        elif (self.node.tag == "button" or 
              (self.node.tag == "input" and not is_checkbox(self.node))): # EX 1
            font = tkinter.font.Font(family="Times", size=16)
            text = DrawText(self.x + 1, self.y + 1, self.node.attributes.get("value", ""), font, 'black')
            return [border, text]
        else: # EX 1
            assert(is_checkbox(self.node))
            if is_checked(self.node):
                font = tkinter.font.Font(family="Times", size=16)
                tick = DrawText(self.x + 1, self.y + 1, "X", font, 'black')
                return [border, tick]
            else:
                return [border]

    def input(self, node):
        tl = InputLayout(node, node.tag == "textarea")
        line = self.children[-1]
        if line.w + tl.w > self.w:
            line = LineLayout(self)
        tl.attach(line)

    def height(self):
        return self.h

    def content_left(self):
        return self.x + 1

    def content_top(self):
        return self.y + 1

    def content_width(self):
        return self.w - 2
