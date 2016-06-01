# pycaserver
A Python-based Channel Access WebSockets Server

This is a tiny web server for getting channel access data via a WebSockets connection.  Useful if you want to make a website that displays a real-time updating value of some PVs.  Built with Bottle, PyEpics, and Geventwebsockets.

### How to use
First, establish a WebSockets connection to the server's '/monitor' URL.
```javascript
var ws = new WebSocket("ws://localhost:8888/monitor");
```

Send messages to the server to connect to PVs:

```javascript
socket.send({"action":"connect", "pv":"myPVName"});
```

Sit back and wait for messages to roll in.  The messages are JSON dictionaries with this format:
```javascript
{ "msg_type": "monitor", "pvname": pvname, "value": value, "count": count, "timestamp": timestamp }
```

If you want to stop listening to a PV, send the server a disconnect message:
```javascript
socket.send({"action":"disconnect", "pv":"myPVName"});
```

That is pretty much it.  For more details, see the [wiki](https://github.com/slaclab/pycaserver/wiki).  Have fun!
