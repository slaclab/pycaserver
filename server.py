#!/usr/bin/python

import wsaccel, ujson
from bottle import route, run, request, abort, Bottle ,static_file
import numpy, epics
from gevent import monkey; monkey.patch_all()
from time import sleep
from geventwebsocket import WebSocketServer, WebSocketApplication, Resource

app = Bottle()

class PycaServerApplication(WebSocketApplication):
	pvs = {}
	def on_open(self):
		print("Connection opened.")
	
	def on_message(self, message):
		if message is None:
			return
			
		current_client = self.ws.handler.active_client
		current_client.pv = message
		
		if message in self.pvs:
			self.pvs[message].connections.add(current_client)
			print("Added a connection to %r.  Total connections: %r" % (message, len(self.pvs[message].connections)))
			#Manually send the latest value of the PV to a new connection.  Important for PVs that update very infrequently.
			self.monitor_update_callback(pvname=message, value=self.pvs[message].value, units=self.pvs[message].units, timestamp=self.pvs[message].timestamp, count=self.pvs[message].count)
		else:
			self.pvs[message] = epics.PV(message, callback=self.monitor_update_callback, connection_callback=self.monitor_connection_callback)
			self.pvs[message].connections = set()
			self.pvs[message].connections.add(current_client)
			print("New connection established to %r" % message)
		
	def monitor_update_callback(self, pvname=None, value=None, units=None, timestamp=None, **kw):
		response = {"msg_type": "monitor", "pvname": pvname, "value": value, "count": kw['count'], "timestamp": timestamp, "units": units }
		if units:
			response['units'] = units
		for subscriber in self.pvs[pvname].connections:
			subscriber.ws.send(ujson.dumps(response))
		
	def monitor_connection_callback(self, pvname=None, conn=None, **kw):
		response = { "msg_type": "connection", "pvname": pvname, "conn": conn }
		for subscriber in self.pvs[pvname].connections:
			subscriber.ws.send(ujson.dumps(response))
		
	def on_close(self, reason):
		current_client = self.ws.handler.active_client
		self.pvs[current_client.pv].connections.remove(current_client)
		print("Removed a connection to %r.  Total connections: %r" % (current_client.pv, len(self.pvs[current_client.pv].connections)))
		if len(self.pvs[current_client.pv].connections) < 1:
			self.pvs[current_client.pv].disconnect()
			del self.pvs[current_client.pv]
			print("PV disconnected.")
		print("Connection closed.")

@app.route('/<filename:path>')
def send_html(filename):
    return static_file(filename, root='./static')

host = "127.0.0.1"
port = 5000
server = WebSocketServer((host, port), Resource({'^/monitor': PycaServerApplication, '^.*': app})).serve_forever()