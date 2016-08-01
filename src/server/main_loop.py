import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.httpclient
from tornado.log import enable_pretty_logging

import urllib
import subprocess
import shlex
import logging
import numpy as np
import sys
import svgwrite
import json

from falcon_kit import kup, falcon, DWA, get_alignment
from falcon_kit.FastaReader import FastaReader

from bokeh.plotting import figure, output_file, show
from bokeh.plotting import figure
from bokeh.embed import components

enable_pretty_logging()

rmap = dict(zip("ACGTN","TGCAN"))

GDURL = "http://localhost:6503/GraphData/"
http_client = tornado.httpclient.HTTPClient()

def get_ctg_data(ctg, URL=GDURL):
    post_data = { 'req': 'ctg_path', 'ctg':ctg }
    body = urllib.urlencode(post_data)
    r = http_client.fetch(URL, method='POST', headers=None, body=body)
    return json.loads(r.body)

def get_utg_data(utg_list, URL=GDURL):
    post_data = { 'req': 'utgs', 'ulist':json.dumps(utg_list) }
    body = urllib.urlencode(post_data)
    r = http_client.fetch(URL, method='POST', headers=None, body=body)
    return json.loads(r.body)

def get_ctg_of_node(n, URL=GDURL):
    post_data = { 'req': 'node_to_ctgs', 'nlist':json.dumps([n]) }
    body = urllib.urlencode(post_data)
    r = http_client.fetch(URL, method='POST', headers=None, body=body)
    return json.loads(r.body)

def get_ctg_of_nodes(n, URL=GDURL):
    post_data = { 'req': 'node_to_ctgs', 'nlist':json.dumps(n) }
    body = urllib.urlencode(post_data)
    r = http_client.fetch(URL, method='POST', headers=None, body=body)
    return json.loads(r.body)

def get_ctg_sg(ctg, URL=GDURL):
    post_data = { 'req': 'contig_sg', 'ctg':ctg }
    body = urllib.urlencode(post_data)
    r = http_client.fetch(URL, method='POST', headers=None, body=body)
    return json.loads(r.body)


def get_local_sg(v, layers=10, max_nodes=1800, URL=GDURL):
    post_data = { 'req': 'local_sg', 'v':v, "layers":layers, "max_nodes":max_nodes }
    body = urllib.urlencode(post_data)
    r = http_client.fetch(URL, method='POST', headers=None, body=body)
    return json.loads(r.body)

def get_kmer_matches(seq1, seq0):
    K = 8
    lk_ptr = kup.allocate_kmer_lookup( 1 << (K * 2) )
    sa_ptr = kup.allocate_seq( len(seq0) )
    sda_ptr = kup.allocate_seq_addr( len(seq0) )
    kup.add_sequence( 0, K, seq0, len(seq0), sda_ptr, sa_ptr, lk_ptr)
    #kup.mask_k_mer(1 << (K * 2), lk_ptr, 16)
    kmer_match_ptr = kup.find_kmer_pos_for_seq(seq1, len(seq1), K, sda_ptr, lk_ptr)
    kmer_match = kmer_match_ptr[0]
    aln_range = kup.find_best_aln_range(kmer_match_ptr, K, K*50, 50)
    
    x,y = zip( * [ (kmer_match.query_pos[i], kmer_match.target_pos[i]) for i in range(kmer_match.count )] )
    kup.free_kmer_match(kmer_match_ptr)
    return x, y, aln_range



class ExamineReadAlignment(tornado.web.RequestHandler):

    def post(self):
        chr_ = self.get_argument("chr", "NA")
        start = int(self.get_argument("start", -1))
        end = int(self.get_argument("end", -1))
        strand = self.get_argument("strand","NA")
        read_name = self.get_argument("read_name", "NA")
        read_seq = self.get_argument("read_seq", "NA")
        ref_seq = self.get_argument("ref_seq", "NA")

        ref_seq = ref_seq.upper()
        s = []
        for c in ref_seq:
            if c not in ["A", "C", "G", "T"]:
                s.append("A")
            else:
                s.append(c)
        ref_seq = "".join(ref_seq)

        #the sequnce from IGV is always the same direction as the reference  
        #if strand == "NEGATIVE":
        #	read_seq = "".join( [rmap[c] for c in read_seq[::-1]] )


        p = figure(width=600, height=600, webgl=True, 
                   tools="crosshair, pan, box_zoom, wheel_zoom, previewsave, undo, redo, reset",
                   toolbar_location="above")

    	x, y, ar = get_kmer_matches(read_seq, ref_seq)
        y = np.array(y) + start
        x = np.array(x)
        p.segment(x0=x, y0=y, x1=x+8, y1=y+8,line_width=2)

        read_seq = "".join( [rmap[c] for c in read_seq[::-1]] )
    	x, y, ar = get_kmer_matches(read_seq, ref_seq)
        y = np.array(y) + start
        x = len(read_seq)-np.array(x)
        p.segment(x0=x, y0=y, x1=x-8, y1=y+8,line_width=2)

        p.xaxis.axis_label = read_name
        p.yaxis.axis_label = chr_
        script, div = components(p)
        js = json.dumps( {"msg":"dot_plot", 
                          "script":script, 
                          "div": div,
                          "read_info": {"name":read_name,
                                        "len":len(read_seq),
                                        "map":"%s:%d-%d" % (chr_,start,end)}} )

        
        for c in PlotSocket.clients:
            c.write_message( js )


    	self.write("Dot Plot Done") 

class ShowLocalSG(tornado.web.RequestHandler):
    
    def post(self):
        
        v = self.get_argument("v", "NA")
        layers = self.get_argument("layers", 90)
        max_nodes = self.get_argument("max_nodes", 1800)
        print "ShowLocalSG called for node: "+v
        self._get_local_sg(v, layers = layers, max_nodes=max_nodes)

    def _get_local_sg(self, v, layers=60, max_nodes=1800):
        #v = "010913479:E"
        neighbor_ctgs = set()
        g = get_local_sg(v, layers=layers, max_nodes=max_nodes)
        all_nodes = g["nodes"]
        all_edges = g["edges"]
        
        links = []
        node_ctg = {}
        print len(list(all_nodes))
        for n, ctgs in get_ctg_of_nodes( list(all_nodes) ):
            node_ctg[n] = ctgs
            neighbor_ctgs.update( ctgs )
        #print len(node_ctg)
        
        
        ctg = "X"
        nodes = set()
        for s, t in all_edges:
            ctg = set(node_ctg.get(s, set())) & set(node_ctg.get(t, set()))
            if len(ctg) >= 1:
                ctg = ctg.pop()
            else:
                ctg = "X"

            col = "#F44"
            links.append( (s, "x", t, col, ctg) )
            nodes.add(s.split(":")[0])
            nodes.add(t.split(":")[0])

        for n in list(nodes):
            links.append( (n+":B", "x", n+":E", "white", "r") )
            
        for n, ctgs in get_ctg_of_nodes( list(all_nodes) ):
            node_ctg[n] = " / ".join(tuple(ctgs))
                
        s1 = json.dumps(links)
        s2 = json.dumps(node_ctg)
        s3 = json.dumps(sorted(list(neighbor_ctgs)))
        self.write( json.dumps({"links":links, 
                                "node_to_ctg":node_ctg, 
                                "ctg_list":sorted(list(neighbor_ctgs)),
                                "center_node": v}) )
        #with open("graph_data.json","w") as f:
        #    print >>f, "var graph_data = {links:%s, node_to_ctg:%s, ctg_list:%s}" % (s1,s2,s3)
        #import os
        #os.system("open show_asm_graph.html")            


class PlotSocket(tornado.websocket.WebSocketHandler):
    clients = []
    def open(self):
        PlotSocket.clients.append(self)
        print "Websocket opened"

    def on_message(self, message):
        pass
    #@self.write_message(u"test:%s" % repr(self))

    def on_close(self):
        print "Websocket close"
        PlotSocket.clients.remove(self)

    #def check_origin(self, origin):
    #    return True


class MainHandler(tornado.web.RequestHandler):
	def get(self):
		self.write("Hello, world")

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/plotsocket/", PlotSocket),
    (r"/ShowLocalSG/", ShowLocalSG),
    (r"/ExamineReadAlignment/", ExamineReadAlignment),
    (r"/view/(.*)",tornado.web.StaticFileHandler,  {"path": "../view/"})],
    autoreload=True, debug=True)

if __name__ == "__main__":
    from tornado.options import options
    options.logging = "DEBUG"
    logging.debug("starting torando web server")
    application.listen(6502)
    tornado.ioloop.IOLoop.current().start()
