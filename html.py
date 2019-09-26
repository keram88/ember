class Tag:
    def __init__(self, tag):
        self.tag = tag

class Text:
    def __init__(self, text):
        self.text = text

class ElementNode:
    def __init__(self, parent, tagname):
        self.handle=None
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

class TextNode:
    def __init__(self, parent, text):
        self.text = text
        self.parent = parent
        self.style = self.parent.style

    def __str__(self, level = 0):
        return " "*level + self.text

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
                if new.tag not in ["br", "link", "meta", "input"]: # lab x
                    current = new
        else: # Text token
            new = TextNode(current, tok.text)
            current.children.append(new)
    return current
