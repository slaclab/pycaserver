#!/usr/bin/python

import wsaccel, ujson
from bottle import route, run, request, abort, Bottle ,static_file
import numpy, epics
from gevent import monkey; monkey.patch_all()
from geventwebsocket import WebSocketServer, WebSocketApplication, Resource, WebSocketError
import logging

logger = logging.getLogger("pycaserverLogger")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
filehandler = logging.FileHandler("/var/log/pycaserver/pycaserver.log")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
filehandler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(filehandler)
logger.setLevel(logging.DEBUG)

app = Bottle()

class PycaServerApplication(WebSocketApplication):
	pvs = {}
	units = {}
	def on_open(self):
		current_client = self.ws.handler.active_client
		logger.debug("Client connection opened.");
		current_client.monitors = set()
		
	def on_message(self, message):
		if message is None:
			return
			
		current_client = self.ws.handler.active_client
		current_client.monitors.add(message)
		
		if message in self.pvs:
			self.pvs[message].connections.add(current_client)
			logger.debug("Added a connection to %r from %r.  Total connections: %r" % (message, current_client.address, len(self.pvs[message].connections)))
			#Manually send the latest value of the PV to a new connection.  Important for PVs that update very infrequently.
			self.monitor_update_callback(pvname=message, value=self.pvs[message].value, units=self.pvs[message].units, timestamp=self.pvs[message].timestamp, count=self.pvs[message].count)
		else:
			self.pvs[message] = epics.PV(message, form='ctrl', callback=self.monitor_update_callback, connection_callback=self.monitor_connection_callback)
			self.pvs[message].connections = set()
			self.pvs[message].connections.add(current_client)
			logger.debug("New connection established to %r" % message)
		
	def monitor_update_callback(self, pvname=None, value=None, units=None, timestamp=None, **kw):
		response = { "msg_type": "monitor", "pvname": pvname, "value": value, "count": kw['count'], "timestamp": timestamp }
		if units:
			response['units'] = units
			self.units[pvname] = units
		else:
			if pvname in self.units:
				response['units'] = self.units[pvname]
		for subscriber in self.pvs[pvname].connections:
			try:
				subscriber.ws.send(ujson.dumps(response))
			except WebSocketError:
				logger.error("Tried to send message to disconnected socket.")
		
	def monitor_connection_callback(self, pvname=None, conn=None, **kw):
		response = { "msg_type": "connection", "pvname": pvname, "conn": conn }
		for subscriber in self.pvs[pvname].connections:
			try:
				subscriber.ws.send(ujson.dumps(response))
			except WebSocketError:
				logger.error("Tried to send message to disconnected socket.")
		
	def on_close(self, reason):
		current_client = self.ws.handler.active_client
		for monitored_pv in current_client.monitors:
			self.pvs[monitored_pv].connections.remove(current_client)
			logger.debug("Removed a connection to %r.  Total connections: %r" % (monitored_pv, len(self.pvs[monitored_pv].connections)))
			if len(self.pvs[monitored_pv].connections) < 1:
				self.pvs[monitored_pv].disconnect()
				del self.pvs[monitored_pv]
				logger.debug("PV disconnected.")
		logger.debug("Connection closed.")
		
@app.route('/<filename:path>')
def send_html(filename):
    return static_file(filename, root='./static')

#wsgi_app is the callable to use for WSGI servers.
wsgi_app = Resource({'^/monitor$': PycaServerApplication, '^/*': app})

#start() starts the development server.
def start():
	logger.info("Starting pycaserver.")
	host = "127.0.0.1"
	port = 8888
	server = WebSocketServer((host, port), wsgi_app)
	server.serve_forever()

if __name__ == '__main__':
	start()