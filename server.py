#!/usr/bin/python

import wsaccel, ujson
from bottle import route, run, request, abort, Bottle ,static_file
import numpy, epics
from gevent import monkey; monkey.patch_all()
from time import sleep
from gevent.pywsgi import WSGIServer
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler

app = Bottle()

@app.route('/monitor')
def handle_monitor():
	wsock = request.environ.get('wsgi.websocket')
	if not wsock:
		abort(400, 'Expected WebSocket request.')
	def monitor_update_callback(pvname=None, value=None, units=None, timestamp=None, **kw):
		response = {"msg_type": "monitor", "pvname": pvname, "value": value, "count": kw['count'], "timestamp": timestamp }
		if units:
			response['units'] = units
		try:
			wsock.send(ujson.dumps(response))
		except WebSocketError, ex:
			print("Oh my goodness an error while sending.")
			print("{0}: {1}".format(ex.__class__.__name__, ex))
			print("Closing dead connection.")
			wsock.close()
	
	def monitor_connection_callback(pvname=None, conn=None, **kw):
		response = { "msg_type": "connection", "pvname": pvname, "conn": conn }
		try:
			wsock.send(ujson.dumps(response))
		except WebSocketError, ex:
			print("Oh my goodness an error while (dis)connecting.")
			print("{0}: {1}".format(ex.__class__.__name__, ex))
		
	try:
		while True:
				message = wsock.receive()
				pv = epics.PV(message, callback=monitor_update_callback, connection_callback=monitor_connection_callback)
		wsock.close()
	except WebSocketError, ex:
		print("Oh my goodness an error.")
		print("{0}: {1}".format(ex.__class__.__name__, ex))
		wsock.close()

@app.route('/<filename:path>')
def send_html(filename):
    return static_file(filename, root='./static', mimetype='text/html')

host = "127.0.0.1"
port = 5000

server = WSGIServer((host, port), app,
                    handler_class=WebSocketHandler)
print "access @ http://%s:%s/websocket.html" % (host,port)
server.serve_forever()