import logging
import os
import psutil
import redis
import signal
import socket
import sys
import threading

from config import REDIS_URL


class HunterAgent(threading.Thread):
    def __init__(self, redis_url):
        threading.Thread.__init__(self)
        self.agent_hostname = socket.gethostname()
        self.agent_pid = os.getpid()
        self.agent_name = '{h.agent_hostname}@{h.agent_pid}'.format(h=self)

        self.logger = logging.getLogger(name=self.agent_name)

        self.redis_url = redis_url
        self.redis = redis.StrictRedis.from_url(self.redis_url)
        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe([
            'hunter'
        ])

        self.logger.debug("Created HunterAgent")

        self.commands = {
            "Q_CPUPERCENT": self.cpu_percent
        }

    def run(self):
        self.redis.publish('hunter', 'AGENT_BEGIN {h.agent_name}'.format(h=self))
        self.redis.sadd("HUNTER_CLIENTS", self.agent_name)
        for item in self.pubsub.listen():
            self.logger.debug("Received: {}".format(item))
            if item['type'] == "message":
                data = item['data'].decode('utf-8')
                try:
                    command, args = data.split(" ", 1)
                except ValueError:
                    command = data
                    args = None

                if command == "SHUTDOWN" and args == self.agent_name:
                    self.shutdown()
                    break

                if command in self.commands:
                    self.logger.debug("Dispatching Command: {}".format(command))
                    self.commands[command](command, args)


    def shutdown(self):
        self.logger.debug("Shutting Down")
        self.pubsub.unsubscribe()
        self.redis.publish('hunter', 'AGENT_END {h.agent_name}'.format(h=self))
        self.redis.srem("HUNTER_CLIENTS", self.agent_name)


    def _reply(self, question, answer):
        self.redis.publish('hunter', "RESPONSE {} {h.agent_name} {}".format(question, answer, h=self))


    def cpu_percent(self, cmd, args):
        self._reply(cmd, psutil.cpu_percent(interval=0.5))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    # data = psutil.cpu_percent(interval=1)

    # print(data)

    agent = HunterAgent(REDIS_URL)

    def ctrl_c_handler(signal, frame):
        agent.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, ctrl_c_handler)
    agent.run()
