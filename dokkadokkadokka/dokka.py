import docker
import flask
import time
from choices import CONTAINER_CHOICES
from flask_ask import Ask, statement, question
from random import choice

app = flask.Flask(__name__)
ask = Ask(app, route="/alexa")
client = docker.DockerClient(base_url='unix://var/run/docker.sock', version='auto')

state_next = None


@ask.intent('DockerChaosIntent')
def docker_chaos():
    containers = client.containers.list()
    if not containers:
        return statement("Can't find anything to kill")
    
    you_die_now = choice(containers)
    try:
        you_die_now.kill()
        you_die_now.remove(force=True)
    except:
        pass
    return statement("No problem!")


@ask.intent('DockerStartIntent')
def start_docker():
    theChosenOne = choice(CONTAINER_CHOICES) + ":latest"
    print("Going to start {}".format(theChosenOne))
    client.containers.run(theChosenOne, detach=True)
    return statement("Starting {}".format(theChosenOne))


@ask.intent('DockerPSIntent')
def ps():
    containers = []
    c_types = set()
    for container in client.containers.list():
        containers.append("{}, ".format(container.name.replace("_", " ")))
        c_types.add(container.attrs['Config']['Image'])

    if not containers:
        return statement("There are no containers running at the current time")
    
    if len(containers) == 1:
        return statement("You are running {} which is image {}".format(containers[0], ' '.join(c_types)))

    output = "You are currently running {} containers, called ".format(' '.join(c_types))

    if len(containers) == 2:
        output += "{}, and {}".format(containers[0], containers[1])
    else:
        for container in containers[:-1]:
            output += "{}, ".format(container)
        output += "and {}".format(container)
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
