import docker
import time
import random
import redis
import flask
from flask_ask import Ask, statement, question
from config import REDIS_URL

CONTAINER_CHOICES = [
    "nginx",
    "redis",
    "busybox",
    "ubuntu",
    "alpine",
    "registry",
    "mysql",
    "mongo",
    "elasticsearch",
    "hello-world",
    "swarm",
    "postgres",
    "node",
    "httpd",
    "logstash",
    "debian",
    "centos",
    "wordpress",
    "ruby",
    "python",
    "kibana",
    "java",
    "jenkins",
    "php",
    "rabbitmq",
    "consul",
    "golang",
    "docker",
    "haproxy",
    "mariadb"
]

app = flask.Flask(__name__)
ask = Ask(app, "/alexa")
r = redis.StrictRedis.from_url(REDIS_URL)
pubsub = r.pubsub()
pubsub.subscribe(["hunter"])


client = docker.DockerClient(base_url='unix://var/run/docker.sock', version='auto')
state_next = None


@ask.intent('DockerChaosIntent')
def docker_chaos():
    containers = client.containers.list()
    if not containers:
        return statement("Can't find anything to kill")
    
    you_die_now = random.choice(containers)
    try:
        you_die_now.kill()
        you_die_now.remove(force=True)
    except:
        pass
    return statement(random.choice([
        "Done. {} has been decomissioned".format(you_die_now.name.replace("_", " ")),
        "Showing {} the door".format(you_die_now.name.replace("_", " ")),
        "Say goodbye to {}".format(you_die_now.name.replace("_", " "))
    ]))


@ask.intent('DockerStartIntent')
def start_docker():
    theChosenOne = random.choice(CONTAINER_CHOICES) + ":latest"
    print("Going to start {}".format(theChosenOne))
    client.containers.run(theChosenOne, detach=True)
    return statement("Starting {}".format(theChosenOne))


@ask.intent('DockerPSIntent')
def ps():
    containers = []
    c_types = set()
    for container in client.containers.list():
        containers.append(container.name.replace("_", " "))
        c_types.add(container.attrs['Config']['Image'])

    if not containers:
        return statement("There are no containers running at the current time")
    
    if len(containers) == 1:
        return statement("You are running {} which is image {}".format(containers[0], ' '.join(c_types)))

    c_types = list(c_types)
    if len(c_types) > 1:
        j_cts = ', '.join(c_types[:-1]) + ' and ' + c_types[-1]
    else:
        j_cts = ' and '.join(c_types)
    output = "You are currently running {} containers, called ".format(j_cts)

    if len(containers) == 2:
        output += "{}, and {}".format(containers[0], containers[1])
    else:
        for container in containers[:-1]:
            output += "{}, ".format(container)
        output += "and {}".format(containers[-1])
    return statement(output)


def rmall_confirmed():
    for container in client.containers.list():
        try:
            container.kill()
            time.sleep(0.1)
            container.remove(force=True)
        except:
            pass
    return statement


@ask.intent('DockerRMAllIntent')
def rmall():
    global state_next
    state_next = rmall_confirmed
    return question("Are you sure you want to remove all containers?")


@ask.intent('ConfirmIntent')
def confirm():
    global state_next
    nxt = state_next()
    state_next = None
    return nxt






@ask.launch
def startStatus():
    welcome = "Welcome to server status"
    return question(welcome)


@ask.intent('WhatServersAreDownIntent')
def getServerDown():
    clients = [c.decode('utf-8').split("@",1)[0] for c in r.smembers("HUNTER_CLIENTS")]
    if len(clients) == 0:
        return statement("I don't think any servers are turned on.")

    return statement("The following servers are online: {}".format(", ".join(clients)))


@ask.intent('ServerStatusIntent')
def getServerStatus():
    r.publish('hunter', "Q_CPUPERCENT")
    clients = r.smembers("HUNTER_CLIENTS")
    responses = []

    if len(clients) == 0:
        return statement("I don't know about any servers to check. Maybe set some up?")

    for item in pubsub.listen():
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

    for item in pubsub.listen():
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

    return flask.jsonify(loads=loads, count=len(clients))


