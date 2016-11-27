/*global Viva*/
var graph = Viva.Graph.graph();
var graphics = Viva.Graph.View.svgGraphics();
var renderer;

var renderAsmGraph = function(graph_data) {
  if (typeof renderer != "undefined") {
    renderer.dispose();
  }

  graph.clear();

  var graph_data = $.parseJSON(graph_data);

  g_links = graph_data["links"];
  g_node_to_ctg = graph_data["node_to_ctg"];
  node_size = graph_data["node_size"];
  var center_node = graph_data["center_node"];
  var center_read = center_node.split(":")[0];
  var c_node_B = center_read + ":B";
  var c_node_E = center_read + ":E";
  


  for (i = 0; i < g_links.length; i++) {

    //if (g_links[i][4] == 'r') continue;  // remove read end pairing in the graph

    graph.addNode(g_links[i][0], {
      ctg: g_node_to_ctg[g_links[i][0]]
    })
    graph.addNode(g_links[i][2], {
      ctg: g_node_to_ctg[g_links[i][2]]
    })
    graph.addLink(g_links[i][0], g_links[i][2], {
      color: g_links[i][3],
      ctg: g_links[i][4]
    });
  }

  var layout = Viva.Graph.Layout.forceDirected(graph, {
    springLength: 10,
    springCoeff: 0.0001,
    dragCoeff: 0.001,
    gravity: -20,
    theta: 1
  });

  var nodeSize = 12;

  var createMarker = function(id) {
      return Viva.Graph.svg('marker')
        .attr('id', id)
        .attr('viewBox', "0 0 12 12")
        .attr('refX', "12")
        .attr('refY', "6")
        .attr('markerUnits', "strokeWidth")
        .attr('markerWidth', "12")
        .attr('markerHeight', "6")
        .attr('orient', "auto");
    },
    marker = createMarker('Triangle');

  marker.append('path').attr('d', 'M 0 0 L 12 6 L 0 12 z ')
    .attr("fill", "context-stroke");

  var defs = graphics.getSvgRoot().append('defs');
  defs.append(marker);
  var geom = Viva.Graph.geom();

  graphics.node(function(node) {
    var nsize = nodeSize;
    var fill_color;
    if (node.id.split(":")[1] == "B") {
      fill_color = "#0F0";
    } else {
      fill_color = "#00F";
    }

    if (node.id == c_node_B) {
      nsize = nsize * 8;
      fill_color = "#0F0";
    }

    if (node.id == c_node_E) {
      nsize = nsize * 8;
      fill_color = "#00F";
    }

    nsize = node_size[ node.id ];

    var ui = Viva.Graph.svg("circle")
      .attr("cx", 0)
      .attr("cy", 0)
      .attr("r", nsize)
      .attr("fill", fill_color);
    ui.addEventListener("click", function() {
      document.getElementById("ctgname").innerHTML = " clicked node: " + node.id + "<br> ctg of the node: " + node.data["ctg"];
    });
    return ui;
  }).placeNode(placeNodeWithTransform);


  function placeNodeWithTransform(nodeUI, pos) {
    // Shift image to let links go to the center:
    nodeUI.attr('transform', 'translate(' + pos.x + ',' + pos.y + ')');
  }

  graphics.link(function(link) {
    var ui = Viva.Graph.svg('path')
      .attr('stroke', link.data["color"])
      .attr('stroke-width', '8pt')
    if (link.data.ctg != "r") {
      ui.attr('marker-end', 'url(#Triangle)');
    } else {
      ui.attr('stroke', link.data["color"]);
    }
    ui.addEventListener("click", function() {
      document.getElementById("ctgname").innerHTML = link.fromId + " => " + link.toId;
    });
    return ui;
  }).placeLink(function(linkUI, fromPos, toPos) {

    var toNodeSize = nodeSize,
      fromNodeSize = nodeSize;

    var from = geom.intersectRect(
      // rectangle:
      fromPos.x - fromNodeSize / 2, // left
      fromPos.y - fromNodeSize / 2, // top
      fromPos.x + fromNodeSize / 2, // right
      fromPos.y + fromNodeSize / 2, // bottom
      // segment:
      fromPos.x, fromPos.y, toPos.x, toPos.y) || fromPos; // if no intersection found - return center of the node
    var to = geom.intersectRect(
      // rectangle:
      toPos.x - toNodeSize / 2, // left
      toPos.y - toNodeSize / 2, // top
      toPos.x + toNodeSize / 2, // right
      toPos.y + toNodeSize / 2, // bottom
      // segment:
      toPos.x, toPos.y, fromPos.x, fromPos.y) || toPos; // if no intersection found - return center of the node

    // linkUI - is the object returend from link() callback above.
    var data = 'M' + from.x + ',' + from.y +
      'L' + to.x + ',' + to.y;
    // 'Path data' (http://www.w3.org/TR/SVG/paths.html#DAttribute )
    // is a common way of rendering paths in SVG:
    linkUI.attr("d", data);
  });

  renderer = Viva.Graph.View.renderer(graph, {
    graphics: graphics,
    layout: layout,
    container: document.getElementById('asmgrapharea')
  });

  for (i = 0; i < 2000; i++) {
    layout.step();
  }
  renderer.run();

  var graphRect = layout.getGraphRect();
  var graphSize = Math.min(graphRect.x2 - graphRect.x1, graphRect.y2 - graphRect.y1);
  //var screenSize = Math.min(document.body.clientWidth, document.body.clientHeight);
  var screenSize = 400;

  function zoomOut(desiredScale, currentScale) {
    // zoom API in vivagraph 0.5.x is silly. There is no way to pass transform
    // directly. Maybe it will be fixed in future, for now this is the best I could do:
    if (desiredScale < currentScale) {
      currentScale = renderer.zoomOut();
      setTimeout(function() {
        zoomOut(desiredScale, currentScale);
      }, 16);
    }
  }

  var desiredScale = screenSize / graphSize;
  zoomOut(desiredScale, 1);
  renderer.pause()


  document.getElementById("ctglist").innerHTML = "";
  var ctg_div = "";
  for (i = 0; i < graph_data["ctg_list"].length; i++) {
    var ctg = graph_data["ctg_list"][i];
    ctg_div += '<li> <a id="' + ctg + '" onclick=highlightCtg("' + ctg + '")>' + ctg + '</a></li> ';
  }
  document.getElementById("ctglist").innerHTML = ctg_div;
}


var highlightCtg = function(ctg) {
  graph.forEachLink(function(link) {
    if (link.data.ctg == ctg) {
      graphics.getLinkUI(link.id).attr('stroke-width', '16pt');
    } else {
      graphics.getLinkUI(link.id).attr('stroke-width', '8pt');
    }
  })
};
