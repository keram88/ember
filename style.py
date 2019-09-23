from html import ElementNode

class TagSelector:
    def __init__(self, tag):
        self.tag = tag

    def matches(self, node):
        return self.tag == node.tag
    
    def score(self):
        return 1

    def __str__(self):
        return "Tag: " + self.tag

class ClassSelector:
    def __init__(self, cls):
        self.cls = cls

    def matches(self, node):
        return self.cls == node.attributes.get("class", "").split()
    
    def score(self):
        return 16

    def __str__(self):
        return "class: " + self.cls

class IdSelector:
    def __init__(self, id):
        self.id = id

    def matches(self, node):
        return self.id == node.id

    def score(self):
        return 256

    def __str__(self):
        return "id: " + self.id

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

