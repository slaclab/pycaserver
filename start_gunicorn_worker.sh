#!/bin/bash

gunicorn --daemon -w 1 -b 127.0.0.1:8888 -k "geventwebsocket.gunicorn.workers.GeventWebSocketWorker" server:wsgi_app
