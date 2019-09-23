import socket

def parse_url(url):
    if url.startswith("http://"):
        url = url[len('http://'):]
    hostport, pathfragment = url.split("/", 1) if "/" in url else (url, "")
    host, port = hostport.rsplit(":", 1) if ":" in hostport else (hostport, "80")
    path, fragment = ("/" + pathfragment).rsplit("#", 1) if "#" in pathfragment else ("/" + pathfragment, None)
    return host, int(port), path, fragment

def request(method, host, port, path, body = None):
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    s.connect((host, port))
    s.send("{} {} HTTP/1.0\r\nHost: {}\r\n".format(method, path, host).encode("utf8"))
    if body:
        body = body.encode("utf8")
        s.send("Content-Length: {}\r\n\r\n".format(len(body)).encode("utf8"))
        s.send(body)
    else:
        s.send("\r\n".encode('utf8'))
    response = s.makefile("rb").read().decode("utf8")
    s.close()
    
    head, body = response.split("\r\n\r\n", 1)
    lines = head.split("\r\n")
    version, status, explanation = lines[0].split(" ", 2)
    assert status == "200", "Server error {}: {} ({}:{}/{})".format(status, explanation, host, port, path)
    headers = {}
    for line in lines[1:]:
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    return headers, body

