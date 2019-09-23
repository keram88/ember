import socket
import sys

ENTRIES = ["A nice message", "Another nice message"]
FORUM = {'Cars' : [("Can't find the flux capacitor.", "Marty", False)],
         'Cooking': [("Trying to fry spinach.", "Spencer", True)]}

def make_links(source):
    out = ""
    for f in sorted(list(FORUM.keys())):
        out += "<p><a href='{}'>{}</a></p>\n".format("/" if f == source else "" + f, f)
    out += "<p><a href='/'>Guest book</a></p>\n"
    return out

def forum_posts(forum, extend=True):
    out = ""
    for f in FORUM[forum]:
        out += "<pre>" + f[0] + "</pre>\n"
        out += "<p> - <i>" + f[1] + "</i>" + ("<b>(Verified)</b>" if f[2] else "") + "</p>\n"
    out += """<form action={}add method=get>
<p><textarea name=comment>Comment...</textarea></p>
<p><input name=user></p>
<p><input name=robot type=checkbox>I'm not a robot.</p>
<p><button>Submit</button></p>
</form>\n""".format("/{}/add".format(forum))
    #format(forum + "/" if extend else "")
    return out

def to_params(text):
    params = {}
    for field in text.split("&"):
        name, value = field.split("=", 1)
        params[name] = value.replace("%20", " ")
    return params

def handle_request(method, url, headers, body):
    surl = url.split('/')
    if method == 'POST':
        params = to_params(body)
        if 'guest' in params:
            ENTRIES.append(params['guest'])
    if method == 'GET' and '?' in url:
        assert(len(surl) > 2)
        forum = surl[1]
        print(surl[2])
        _, data = surl[2].split('?')
        params = to_params(data)
        comment = params.get('comment', 'Nothing to say...')
        user = params.get('user', "Anonymous")
        verified = 'robot' in params
        FORUM[forum].append((comment, user, verified))

    out = "<!doctype html><body>"
    out += make_links(surl[1])
    if len(surl) >= 2 and surl[1] in FORUM.keys():
        out += forum_posts(surl[1], len(surl)<3)
    else:
        out += "<form action=add method=post><p><input name=guest></p><p><button>Sign the book!</button></p></form>"
        for entry in ENTRIES:
            out += "<p>" + entry + "</p>"
            
    out += "</body>"
    return out

def handle_connection(conx):
    req = conx.makefile("rb")
    method, url, version = req.readline().decode("utf8").split(" ", 2)
    method = method.upper()
    print(method, url, version)
    assert(method in ("GET", "POST"))
    headers={}
    for line in req:
        line = line.decode('utf8')
        print(line)
        if line == '\r\n': break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    if 'content-length' in headers:
        length = int(headers['content-length'])
        body = req.read(length).decode('utf8')
    else:
        body = None
    response = handle_request(method, url, headers, body)
    response = response.encode("utf8")
    conx.send('HTTP/1.0 200 OK\r\n'.encode('utf8'))
    conx.send('Content-Length: {}\r\n\r\n'.format(len(response)).encode('utf8'))
    conx.send(response)
    conx.close()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8000
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    s.bind(("", port))

    # I'm listening...
    s.listen()
    while True:
        conx, addr = s.accept()
        handle_connection(conx)
