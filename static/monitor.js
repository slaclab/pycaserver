$(window).load(function() {
  $(".monitor").each(function(){
    var elem = this
    var pv = $(this).data("pv");
    var ws = new WebSocket("ws://localhost:5000/monitor");
    ws.onopen = function() {
      ws.send(pv);
    };
    ws.onmessage = function(evt) {
      var data = JSON.parse(evt.data);
      if (data.msg_type === "monitor") {
        $(elem).text(data.value);
      } else if (data.msg_type === "connection") {
        if (data.conn) {
          $(elem).css("color", "black");
        } else {
          $(elem).css("color", "red");
        }
      }
    };
  });
});