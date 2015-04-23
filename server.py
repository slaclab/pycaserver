#!/usr/bin/python

import json
from bottle import route, run, request, abort, Bottle ,static_file
import numpy, epics
from gevent import monkey; monkey.patch_all()
from time import sleep

app = Bottle()

@app.route('/websocket')
def handle_websocket():
    wsock = request.environ.get('wsgi.websocket')
    if not wsock:
        abort(400, 'Expected WebSocket request.')
    while True:
        try:
            message = wsock.receive()
            wsock.send("Your message was: %r" % message)
            sleep(3)
            wsock.send("Your message was: %r" % message)
        except WebSocketError:
            break

@app.route('/<filename:path>')
def send_html(filename):
    return static_file(filename, root='./static', mimetype='text/html')


from gevent.pywsgi import WSGIServer
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler

host = "127.0.0.1"
port = 5000

server = WSGIServer((host, port), app,
                    handler_class=WebSocketHandler)
print "access @ http://%s:%s/websocket.html" % (host,port)
server.serve_forever()