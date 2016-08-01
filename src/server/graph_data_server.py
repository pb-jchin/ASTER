
import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.log import enable_pretty_logging
import logging

import networkx as nx
import json
from falcon_kit.fc_asm_graph import AsmGraph

def reverse_end( node_id ):
    node_id, end = node_id.split(":")
    new_end = "B" if end == "E" else "E"
    return node_id + ":" + new_end

def load_graph():
    G_asm = AsmGraph("sg_edges_list", "utg_data", "ctg_paths")
    return G_asm

def get_full_asm_G(G_asm):
    full_asm_G = nx.DiGraph()
    for v, w in G_asm.sg_edges:
        edge_data = G_asm.sg_edges[(v, w)]
        if edge_data[-1] == "G":
            full_asm_G.add_edge(v, w)
    return full_asm_G

class GraphDataServer(object):
    _G_asm = None
    _full_asm_G = None

    def __init__(self):
        if GraphDataServer._G_asm == None:
            GraphDataServer._G_asm = load_graph()
        self.G_asm = GraphDataServer._G_asm

        if GraphDataServer._full_asm_G == None:
            GraphDataServer._full_asm_G = get_full_asm_G(self.G_asm)
        self.full_asm_G = GraphDataServer._full_asm_G

    def get_sg_edge( self, v, w ):
        return self.G_asm.sg_edges[ (v, w) ]

    def get_utg_data( self, s, t, v):
        return self.G_asm.utg_data[ (s, t, v) ]

    def get_ctg_path( self, ctg ):
        return self.G_asm.ctg_data[ctg]

GraphDataServer() #load data


class GraphData(tornado.web.RequestHandler):
    def post(self):
        req = self.get_argument("req", "NA")
        gds = GraphDataServer()
        if req == "sg_edge":
            v = self.get_argument("v")
            w = self.get_argument("w")
            self.write( json.dumps( gds.get_sg_edge(v,w) ) )

        elif req == "utg_data":
            s = self.get_argument("s")
            t = self.get_argument("t")
            v = self.get_argument("v")
            self.write( json.dumps( gds.get_utg_data(s,t,v) ) )

        elif req == "ctg_path":
            ctg = self.get_argument("ctg")
            self.write( json.dumps( gds.get_ctg_path(ctg) ) )

        elif req == "utgs":
            ulist = json.loads(self.get_argument("ulist"))
            utg_data= gds.G_asm.utg_data
            udata = []
            for s, v, t in ulist:
                udata.append( ((s, v, t), utg_data[ (s, t, v) ]) )
            self.write( json.dumps( udata ) )

        elif req == "sg_edges":
            elist = json.loads(self.get_argument("elist"))
            sg_edges = gds.G_asm.sg_edges
            sg_data = []
            for v, w in elist:
                sg_data.append( ( (v, w), sg_edges[ (v, w) ] ) )
            self.write( json.dumps( sg_data ) )

        elif req == "node_to_ctgs":
            nlist = json.loads(self.get_argument("nlist"))
            node_to_ctg = gds.G_asm.node_to_ctg
            data = []
            for v in nlist:
                if v in node_to_ctg:
                    data.append( (v, tuple(node_to_ctg[v]) ) )
                else:
                    data.append( (v, "X" ) )
            self.write( json.dumps( data ) )

        elif req == "node_to_utgs":
            nlist = json.loads(self.get_argument("nlist"))
            node_to_utg = gds.G_asm.node_to_utg
            data = []
            for n in nlist:
                utg_list = []
                if n in node_to_utg:
                    for s, t, v in list(node_to_utg[n]):
                        utg_list.append( (s, v, t) )
                    data.append( (n, utg_list) )
                else:
                    data.append( (n, "X") )
            self.write( json.dumps( data ) )

        elif req == "contig_sg":
            ctg = self.get_argument("ctg")
            nodes = set() 
            edges = []
            s_utg_nodes = set() 
            s_utg_edges = []
            utgs = []
            path = gds.get_ctg_path(ctg)[-1] 
            for s, v, t in path:
                type_, length, score, path_or_edges =  gds.G_asm.utg_data[ (s, t, v) ]
                utgs.append( (type_, path_or_edges) )
            for t, utg in utgs:
                if t == "simple":
                    one_path = utg.split("~")
                    start, end = one_path[0], one_path[-1]
                    s_utg_nodes.add(start)
                    s_utg_nodes.add(end)
                    s_utg_edges.append(  (start, end) )
                    v = one_path[0]
                    nodes.add(v)
                    for w in one_path[1:]:
                        nodes.add(v)
                        edges.append( (v, w) )
                        v = w
                elif t == "compound":
                    for svt in utg.split("|"):
                        s, v, t = svt.split("~")
                        type_, length, score, one_path =  gds.G_asm.utg_data[ (s, t, v) ]
                        one_path = one_path.split("~")
                        start, end = one_path[0], one_path[-1]
                        s_utg_nodes.add(start)
                        s_utg_nodes.add(end)
                        s_utg_edges.append(  (start, end) )
                        v = one_path[0]
                        nodes.add(v)
                        for w in one_path[1:]:
                            nodes.add(v)
                            edges.append( (v, w) )
                            v = w
            rtn = {"nodes": tuple(nodes), "edges": edges, "s_utg_nodes": tuple(s_utg_nodes), "s_utg_edges": s_utg_edges}
            self.write( json.dumps( rtn ) )

        elif req == "local_sg": 
            v = self.get_argument("v")
            layers = self.get_argument("layers")
            layers = int(layers)
            max_nodes = self.get_argument("max_nodes")
            max_nodes = int(max_nodes)
            
            nodes = set()
            edges = []
            
            vB = v.split(":")[0] + ":B"
            vE = v.split(":")[0] + ":E"
            all_neighbor_nodes = set()
            all_neighbor_nodes.add(vB)
            all_neighbor_nodes.add(vE)
            l = 0
            while l < layers and len(all_neighbor_nodes) < max_nodes:
                new_nodes = set()
                for n in list(all_neighbor_nodes):
                    for v, w in gds.full_asm_G.out_edges(n):
                        new_nodes.add(w)
                    for v, w in gds.full_asm_G.in_edges(n):
                        new_nodes.add(v)
                all_neighbor_nodes.update( new_nodes )
                l += 1
             
            for n in list(all_neighbor_nodes):
                for v, w in gds.full_asm_G.out_edges(n):
                    edges.append( (v, w) )
                    nodes.add(v)
                    nodes.add(w)

            rtn = {"nodes": tuple(nodes), "edges": edges}
            self.write( json.dumps( rtn ) )




class MainHandler(tornado.web.RequestHandler):
	def get(self):
		self.write("Hello, world")

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/GraphData/", GraphData ),],
    autoreload=False, debug=True)

if __name__ == "__main__":
    from tornado.options import options
    options.logging = "DEBUG"
    logging.debug("starting torando web server")
    application.listen(6503)
    tornado.ioloop.IOLoop.current().start()
