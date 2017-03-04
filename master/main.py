from config import REDIS_URL
from flask import Flask, jsonify
from flask_ask import Ask, statement
import redis

app = Flask(__name__)
ask = Ask(app, "/alexa")
r = redis.StrictRedis.from_url(REDIS_URL)
ps = r.pubsub()
ps.subscribe(["hunter"])


@ask.intent('ServerStatusIntent')
def getServerStatus():
    r.publish('hunter', "Q_CPUPERCENT")
    clients = r.smembers("HUNTER_CLIENTS")
    responses = []

    for item in ps.listen():
        if item['type'] == "message":
            data = item['data'].decode('utf-8')

            parts = data.split()

            if parts[0] == "RESPONSE":
                comm, question, node, answer = parts
                responses.append((comm, question, node, answer))

            if len(responses) == len(clients):
                break

    vals = [float(x[3]) for x in responses]
    print(vals)

    loads = {
        "low": len([x for x in responses if float(x[3]) < 25.0]),
        "mid": len([x for x in responses if float(x[3]) >= 25.0 and float(x[3]) < 75.0]),
        "high": len([x for x in responses if float(x[3]) >= 75.0 and float(x[3]) < 90.0]),
        "fire": len([x for x in responses if float(x[3]) >= 90.0])
    }

    toappend = ""

    if loads['fire'] > 0:
        toappend = ", you might want to fix that."

    return statement("Of your {} servers, {} are not being used much, {} are "
                     "in a medium state, {} are being highly used, and {} are"
                     " on fire{}".format(
                        len(clients),
                        loads['low'],
                        loads['mid'],
                        loads['high'],
                        loads['fire'],
                        toappend))


@app.route("/")
def index():
    r.publish('hunter', "Q_CPUPERCENT")
    clients = r.smembers("HUNTER_CLIENTS")
    responses = []

    for item in ps.listen():
        if item['type'] == "message":
            data = item['data'].decode('utf-8')

            parts = data.split()

            if parts[0] == "RESPONSE":
                comm, question, node, answer = parts
                responses.append((comm, question, node, answer))

            if len(responses) == len(clients):
                break

    vals = [float(x[3]) for x in responses]
    print(vals)

    loads = {
        "low": len([x for x in responses if float(x[3]) < 25.0]),
        "mid": len([x for x in responses if float(x[3]) >= 25.0 and float(x[3]) < 75.0]),
        "high": len([x for x in responses if float(x[3]) >= 75.0 and float(x[3]) < 90.0]),
        "fire": len([x for x in responses if float(x[3]) >= 90.0])
    }

    return jsonify(loads=loads, count=len(clients))

if __name__ == "__main__":
    app.run("0.0.0.0", 5000, True)
