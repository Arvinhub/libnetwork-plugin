# Copyright 2015 Metaswitch Networks
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import socket
from time import sleep
import os
from subprocess import check_output, STDOUT
from subprocess import CalledProcessError
from tests.st.utils.exceptions import CommandExecError
import re
import json

LOCAL_IP_ENV = "MY_IP"
logger = logging.getLogger(__name__)


def get_ip():
    """
    Return a string of the IP of the hosts interface.
    Try to get the local IP from the environment variables.  This allows
    testers to specify the IP address in cases where there is more than one
    configured IP address for the test system.
    """
    try:
        ip = os.environ[LOCAL_IP_ENV]
    except KeyError:
        # No env variable set; try to auto detect.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    return ip


def log_and_run(command):
    try:
        logger.info(command)
        return check_output(command, shell=True, stderr=STDOUT).rstrip()
    except CalledProcessError as e:
            # Wrap the original exception with one that gives a better error
            # message (including command output).
            raise CommandExecError(e)


def retry_until_success(function, retries=10, ex_class=Exception):
    """
    Retries function until no exception is thrown. If exception continues,
    it is reraised.

    :param function: the function to be repeatedly called
    :param retries: the maximum number of times to retry the function.
    A value of 0 will run the function once with no retries.
    :param ex_class: The class of expected exceptions.
    :returns: the value returned by function
    """
    for retry in range(retries + 1):
        try:
            result = function()
        except ex_class:
            if retry < retries:
                sleep(1)
            else:
                raise
        else:
            # Successfully ran the function
            return result

def assert_number_endpoints(host, expected):
    """
    Check that a host has the expected number of endpoints in Calico
    Parses the "calicoctl endpoint show" command for number of endpoints.
    Raises AssertionError if the number of endpoints does not match the
    expected value.

    :param host: DockerHost object
    :param expected: int, number of expected endpoints
    :return:
    """
    hostname = host.get_hostname()
    output = host.calicoctl("endpoint show")
    lines = output.split("\n")
    actual = 0

    for line in lines:
        columns = re.split("\s*\|\s*", line.strip())
        if len(columns) > 1 and columns[1] == hostname:
                actual = columns[4]
                break

    if int(actual) != int(expected):
        msg = "Incorrect number of endpoints: \n" \
              "Expected: %s; Actual: %s" % (expected, actual)
        raise AssertionError(msg)

def assert_profile(host, profile_name):
    """
    Check that profile is registered in Calico
    Parse "calicoctl profile show" for the given profilename

    :param host: DockerHost object
    :param profile_name: String of the name of the profile
    :return: Boolean: True if found, False if not found
    """
    output = host.calicoctl("profile show")
    lines = output.split("\n")
    found = False

    for line in lines:
        columns = re.split("\s*\|\s*", line.strip())
        if len(columns) > 1 and profile_name == columns[1]:
                found = True
                break

    if not found:
        raise AssertionError("Profile %s not found in Calico" % profile_name)

def get_profile_name(host, network):
    """
    Get the profile name from Docker
    A profile is created in Docker for each Network object.
    The profile name is a randomly generated string.

    :param host: DockerHost object
    :param network: Network object
    :return: String: profile name
    """
    info_raw = host.execute("docker network inspect %s" % network.name)
    info = json.loads(info_raw)

    # Network inspect returns a list of dicts for each network being inspected.
    # We are only inspecting 1, so use the first entry.
    return info[0]["Id"]

def assert_network(host, network):
    """
    Checks that the given network is in Docker
    Raises an exception if the network is not found

    :param host: DockerHost object
    :param network: Network object
    :return: None
    """
    try:
        host.execute("docker network inspect %s" % network.name)
    except CommandExecError:
        raise AssertionError("Docker network %s not found" % network.name)
