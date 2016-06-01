#!/usr/bin/python

import wsaccel, ujson
from bottle import route, run, request, abort, Bottle ,static_file
import numpy, epics
from gevent import monkey; monkey.patch_all()
from geventwebsocket import WebSocketServer, WebSocketApplication, Resource, WebSocketError
import logging
from collections import OrderedDict

logger = logging.getLogger("pycaserverLogger")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
filehandler = logging.FileHandler("pycaserver.log")
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
    
  def on_message(self, raw_message):
    if raw_message is None:
      return
    
    current_client = self.ws.handler.active_client
    try:
      message_data = ujson.loads(raw_message)
    except ValueError:
      #Fallback to old protocol, where we assume the raw message string is a PV to connect to.
      self.establish_pv_connection(raw_message, current_client)
      return
      
    if 'action' in message_data:  
      if message_data['action'] == "connect":
        self.establish_pv_connection(message_data["pv"], current_client)
      elif message_data['action'] == "disconnect":
        self.close_pv_connection(message_data["pv"], current_client)
  
  def on_close(self, reason):
    current_client = self.ws.handler.active_client
    for monitored_pv in current_client.monitors:
      self.close_pv_connection(monitored_pv, current_client)
    logger.debug("Connection to client closed.")
      
  def establish_pv_connection(self, pvname, client):
    client.monitors.add(pvname)
    if pvname in self.pvs:
      self.pvs[pvname].connections.add(client)
      logger.debug("Added a connection to {0} from {1}.  Total connections: {2}".format(pvname, client.address, len(self.pvs[pvname].connections)))
      #Manually send the connection established message, since the PV callback is long-since fired.
      self.monitor_connection_callback(pvname=pvname, conn=True)
      #Manually send the latest value of the PV to a new connection.  Important for PVs that update very infrequently.
      self.monitor_update_callback(pvname=pvname, value=self.pvs[pvname].value, units=self.pvs[pvname].units, timestamp=self.pvs[pvname].timestamp, count=self.pvs[pvname].count)
    else:
      self.pvs[pvname] = epics.PV(pvname, form='ctrl', callback=self.monitor_update_callback, connection_callback=self.monitor_connection_callback)
      self.pvs[pvname].connections = set()
      self.pvs[pvname].connections.add(client)
      logger.debug("New connection established to {0}".format(pvname))
  
  def close_pv_connection(self, pvname, client):
    if (pvname in self.pvs) and (client in self.pvs[pvname].connections):
      self.pvs[pvname].connections.remove(client)
      logger.debug("Removed a connection to {0}.  Total connections: {1}".format(pvname, len(self.pvs[pvname].connections)))
      if len(self.pvs[pvname].connections) < 1:
        self.pvs[pvname].disconnect()
        del self.pvs[pvname]
        logger.debug("PV {0} disconnected.".format(pvname))
    
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
    
@app.route('/<filename:path>')
def send_html(filename):
    return static_file(filename, root='./static')

#wsgi_app is the callable to use for WSGI servers.
wsgi_app = Resource(OrderedDict([('^/monitor$', PycaServerApplication), ('^/*', app)]))

#start() starts the development server.
def start():
  logger.info("Starting pycaserver.")
  host = "127.0.0.1"
  port = 8888
  server = WebSocketServer((host, port), wsgi_app)
  server.serve_forever()

if __name__ == '__main__':
  start()
