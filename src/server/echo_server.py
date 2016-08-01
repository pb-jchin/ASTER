import tornado.ioloop
import tornado.web

import urllib
import json

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
        print "data received from read {}".format( read_name ) 
        # return a json object
        self.write( json.dumps( {"status":"OK",
            "msg":"information about read {} received".format(read_name),
            "payload":{ "read_length": len(read_seq) } } ) )

class MainHandler(tornado.web.RequestHandler):
	def get(self):
		self.write("please use ExamineReadAlignment/ as the end point")

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/ExamineReadAlignment/", ExamineReadAlignment),], 
    autoreload=True, debug=True)

if __name__ == "__main__":
    application.listen(6502)
    tornado.ioloop.IOLoop.current().start()
