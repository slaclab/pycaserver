#!/usr/bin/python

import wsaccel, ujson
from bottle import route, run, request, abort, Bottle ,static_file
import numpy, epics
from gevent import monkey; monkey.patch_all()
from time import sleep
from geventwebsocket import WebSocketServer, WebSocketApplication, Resource, WebSocketError

app = Bottle()

class PycaServerApplication(WebSocketApplication):
	pvs = {}
	def on_open(self):
		current_client = self.ws.handler.active_client
		print("Connection opened.");
		current_client.monitors = set()
		
	def on_message(self, message):
		if message is None:
			return
			
		current_client = self.ws.handler.active_client
		#if not hasattr(current_client, 'monitors'):
		#	current_client.monitors = set()
		current_client.monitors.add(message)
		
		if message in self.pvs:
			self.pvs[message].connections.add(current_client)
			print("Added a connection to %r from %r.  Total connections: %r" % (message, current_client.address, len(self.pvs[message].connections)))
			#Manually send the latest value of the PV to a new connection.  Important for PVs that update very infrequently.
			self.monitor_update_callback(pvname=message, value=self.pvs[message].value, units=self.pvs[message].units, timestamp=self.pvs[message].timestamp, count=self.pvs[message].count)
		else:
			self.pvs[message] = epics.PV(message, form='ctrl', callback=self.monitor_update_callback, connection_callback=self.monitor_connection_callback)
			self.pvs[message].connections = set()
			self.pvs[message].connections.add(current_client)
			print("New connection established to %r" % message)
		
	def monitor_update_callback(self, pvname=None, value=None, units=None, timestamp=None, **kw):
		response = { "msg_type": "monitor", "pvname": pvname, "value": value, "count": kw['count'], "timestamp": timestamp }
		if units:
			response['units'] = units
		for subscriber in self.pvs[pvname].connections:
			try:
				subscriber.ws.send(ujson.dumps(response))
			except WebSocketError:
				print("Tried to send message to disconnected socket.")
		
	def monitor_connection_callback(self, pvname=None, conn=None, **kw):
		response = { "msg_type": "connection", "pvname": pvname, "conn": conn }
		for subscriber in self.pvs[pvname].connections:
			try:
				subscriber.ws.send(ujson.dumps(response))
			except WebSocketError:
				print("Tried to send message to disconnected socket.")
		
	def on_close(self, reason):
		current_client = self.ws.handler.active_client
		for monitored_pv in current_client.monitors:
			self.pvs[monitored_pv].connections.remove(current_client)
			print("Removed a connection to %r.  Total connections: %r" % (monitored_pv, len(self.pvs[monitored_pv].connections)))
			if len(self.pvs[monitored_pv].connections) < 1:
				self.pvs[monitored_pv].disconnect()
				del self.pvs[monitored_pv]
				print("PV disconnected.")
		print("Connection closed.")
		

@app.route('/<filename:path>')
def send_html(filename):
    return static_file(filename, root='./static')

host = "127.0.0.1"
port = 5000
server = WebSocketServer((host, port), Resource({'^/monitor': PycaServerApplication, '^.*': app})).serve_forever()