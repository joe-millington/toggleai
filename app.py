import json
import logging
import sys
import configparser
import argparse

import tornado.ioloop
import tornado.web

import engines
from util import InvalidQueryError

parser = argparse.ArgumentParser()
parser.add_argument("config")
args = parser.parse_args()

config = configparser.ConfigParser()
config.read(args.config)

logging.basicConfig(
    format="%(asctime)s %(levelname)s: %(name)s: %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

cls = engines.__dict__[config['APP']['ENGINE']]

engine = cls(filepath=config['FILES']['CORPUS'], skiprows=1)


class QueryHandler(tornado.web.RequestHandler):
    def get(self):
        query = self.get_argument("q", None)
        if query:
            try:
                result = engine.evaluate_query(query, sort_by='Category Name')
                result = result.to_json()
            except InvalidQueryError as e:
                error = {
                  "errors": [
                    {
                      "title":  type(e).__name__,
                      "detail": str(e)
                    }
                  ]
                }
                self.write(json.dumps(error))
            else:
                self.write(json.dumps(result))
                # self.render('templates/search_html.html',
                #             results=result['data'],
                #             time=result['meta']['execution_time_ms'])


def make_app():
    return tornado.web.Application([
            (r"/", QueryHandler),
        ])


if __name__ == "__main__":
    app = make_app()
    port = int(config['APP']['PORT'])
    app.listen(port)
    logger.info(f'Listening on port {port}...')
    tornado.ioloop.IOLoop.current().start()
