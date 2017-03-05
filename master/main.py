from flask import Flask, jsonify
from flask_ask import Ask, statement, question
import random
import redis

from config import REDIS_URL

app = Flask(__name__)
ask = Ask(app, "/alexa")
r = redis.StrictRedis.from_url(REDIS_URL)
ps = r.pubsub()
ps.subscribe(["hunter"])


@ask.launch
def startStatus():
    welcome = "Welcome to server status"
    return question(welcome)


@ask.intent('ServerStatusIntent')
def getServerStatus():
    r.publish('hunter', "Q_CPUPERCENT")
    clients = r.smembers("HUNTER_CLIENTS")
    responses = []

    if len(clients) == 0:
        return statement("I don't know about any servers to check. Maybe set some up?")

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

    loads = {
        "low": len([x for x in responses if float(x[3]) < 25.0]),
        "mid": len([x for x in responses if float(x[3]) >= 25.0 and float(x[3]) < 75.0]),
        "high": len([x for x in responses if float(x[3]) >= 75.0 and float(x[3]) < 90.0]),
        "fire": len([x for x in responses if float(x[3]) >= 90.0])
    }

    avg = sum(vals) / len(vals)
    
    parts = []

    if avg < 25.0:
        output = random.choice([
            "Everything seems fine. ",
            "Nothing much to report. ",
            "All good. ",
        ])
    elif avg < 75.0:
        output = random.choice([
            "Some machines may need attention. ",
            "Some cause for concern. ",
        ])
    else:
        output = random.choice([
            "Bollocks. ",
            "Bollocks. ",
            "It's hitting the fan! ",
            "Not good! ",
            "Oh boy... ",
        ])

    if len(clients) > 1:
        output += "Out of {} servers, ".format(len(clients))
    else:
        output += "Your server "

    def quald(val):
        if val == 1:
            qualifier = "is"
        else:
            qualifier = "are"
        return '{} {}'.format(val if val>1 else '', qualifier)

    if loads['low']:
        parts.append(
            "{} idling".format(quald(loads['low']))
        )

    if loads['mid']:
        parts.append(
            "{} seeing increased load".format(quald(loads['mid']))
        )

    if loads['high']:
        parts.append(
            "{} under high load".format(quald(loads['high']))
        )

    if loads['fire']:
        parts.append(
            "{} on fire. {}".format(quald(loads['fire'], random.choice([
                "You might want to fix that...",
            ])))
        )

    if len(parts) > 1:
        output += ", ".join(parts[:-1]) + ", and " + parts[-1]
    else:
        output += parts[0]

    output += '.'

    return statement(output)


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
