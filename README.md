# pycaserver
A Python-based Channel Access WebSockets Server

This is a tiny web server for getting channel access data via a WebSockets connection.  Useful if you want to make a website that displays a real-time updating value of some PVs.  Built with Bottle, PyEpics, and Geventwebsockets.

### How to use
Establish a WebSockets connection to the server's '/monitor' URL.  Send a message containing a PV name.  Sit back and wait for messages to roll in.  The messages are JSON dictionaries with this format: { "msg_type": "monitor", "pvname": pvname, "value": value, "count": count, "timestamp": timestamp }
