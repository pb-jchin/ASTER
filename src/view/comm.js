var curReadID = "";


function evalJSFromHtml(html) {
  var newElement = document.createElement('div');
  newElement.innerHTML = html;

  var scripts = newElement.getElementsByTagName("script");
  for (var i = 0; i < scripts.length; ++i) {
    var script = scripts[i];
    eval(script.innerHTML);
  }
}

//<!-- All of the Node.js APIs are available in this renderer process. -->
// You can also require other files to run in this process
//require('./renderer.js')
var ws = new WebSocket("ws://localhost:6502/plotsocket/");
ws.onopen = function() {
  //ws.send("Hello, world");
};

ws.onmessage = function(evt) {
  var js = JSON.parse(evt.data);
  if (js["msg"] == "dot_plot") {
    var script = js["script"];
    div = js["div"];
    plot_area = document.getElementById("dotplotarea");
    plot_area.innerHTML = div;
    evalJSFromHtml(script);
    read_info = js["read_info"];
    read_name = read_info["name"];
    read_len = read_info["len"];
    read_map = read_info["map"];
    curReadID = read_name;
    document.getElementById("read-detail").innerHTML =
      "name: " + read_name + "<br>" +
      "len: " + read_len + "<br>" +
      "mapped location: " + read_map;

  } else if (js["msg"] == "asm_graph_plot") {
    plot_area = document.getElementById("dotplotarea");
    div = js["div"];
    plot_area.innerHTML = div;
  }
  $("[href='#dotplot']").tab("show")
};

var showLocalGraph = function(node_name) {
  var data = {
    "v": node_name + ":E",
    "layers": 60,
    "max_nodes": 3600
  };
  $("[href='#asmgraph']").tab("show")
  $.post("http://localhost:6502/ShowLocalSG/", data,
    function(g) {
      renderAsmGraph(g);
    });
}
