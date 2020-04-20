import os
import re
import requests
import RestUtils
import Global
#from Utilities import *

import urllib
import pytz






from timeit import default_timer
from datetime import datetime
import time
import json


def DecoRestAPI(api_func):
    """
        This is the common decorator for REST API GET/POST/Export functions.
    """

    def wrapper(*args, **kwargs):
        """
            This inside function would be used as the common wrapper
            around the base REST API function.
            It starts with setting path, and parsing payloa and parameters from user input.
            Then it issues the http request, with the required path and payload/parameters.
            It returns Global.PASS or Global.FAIL.
        """

        RestUtils.DebugPrint(RestUtils.logFP, "AmpleApiUtils.py - DecoRestAPI(api_func)/wrapper() \n")
        time_fmt = "%H:%M:%S.%f"
        # format for timestame

        testName = 'REST API: %s' % (api_func.__name__)
        RestUtils.DebugPrint(RestUtils.logFP, "Test Name :  %s" % testName)
        RestUtils.DebugPrint(RestUtils.logFP, "INPUT Arguments:  %s" % json.dumps(kwargs))

        # Basic header items
        head = {'content-type': 'application/json'}
        RestUtils.DebugPrint(RestUtils.logFP, "head is:  %s" % head)
        restParams = {'headers': head, 'allow_redirects': True}

        try:
            expectation = kwargs['expectation']
        except Exception as e:
            # there is no expectation input from InputFile (json)
            RestUtils.DebugPrint(RestUtils.logFP, 'Invalid or nonexistent bad fileData: %s' % str(e))

        # paths, http methods - for the respective API function
        operations = api_func(*args, **kwargs)
        RestUtils.DebugPrint(RestUtils.logFP, "AmpleApiUtils.py - oooooooperations is:  %s" % operations)

        full_path = operations[0]
        if "{auth_id}" in full_path:
            auth_id= kwargs['auth_id']
            full_path=full_path.replace("{auth_id}",auth_id)
            print(full_path)
        method = operations[1]
        if len(operations) > 2:
            ntype = operations[2]
        else:
            ntype = ''
        RestUtils.DebugPrint(RestUtils.logFP, "AmpleApiUtils.py - nnnnnnnnnntype is:  %s" % ntype)


        if method == 'get':
            response = RestUtils.session.get(RestUtils.server + full_path, **restParams)
            print "get response is %s\n" % response
            RestUtils.DebugPrint(RestUtils.logFP, "\nDecoRestAPI() - 01rrrrrrrrrrrrrrresponse is %s" % response)

        elif method == 'post':

            print(str(restParams) + 'post params')


            print(str(RestUtils.server + full_path) + '---this the post url')
            print(str(restParams))
            response = RestUtils.session.post(RestUtils.server + full_path, **restParams)
            responseJson = response.json()
            print "post response is %s\n" % response

        else:
            RestUtils.DebugPrint(RestUtils.logFP, 'No specific method called on REST api')
            return Global.FAIL, ''

        RestUtils.DebugPrint(RestUtils.logFP, "30HTTP response status code %d" % response.status_code)

        if method != 'export':
            RestUtils.DebugPrint(RestUtils.logFP,
                       '%s  -  00HTTP response: %s' % (datetime.now().strftime(time_fmt)[:-3], response.text))

        logLine = ''
        if not response.status_code == requests.codes.ok:
            print "response.status_code is %d, requests.codes.ok is %d\n" % (response.status_code, requests.codes.ok)
            if expectation['status'] == "OK":
                logLine = 'Actual status code: %d, Expected status code(s): %s' \
                          % (response.status_code, requests.codes.ok)
                return Global.FAIL, logLine
            else:
                return Global.PASS, ''

        ##added  by sroy@sentient-energy.com to check in the response message

        if method == 'export':
            # write to the file
            with open(output_file, 'wb') as fd:
                for chunk in response.iter_content(chunk_size=1):
                    fd.write(chunk)

            RestUtils.DebugPrint(RestUtils.logFP,
                       '%s  -  31HTTP response: %s' % (datetime.now().strftime(time_fmt)[:-3], response))
            RestUtils.DebugPrint(RestUtils.logFP,
                       '%s  -  Test: %s  ---  COMPLETED.' % (datetime.now().strftime(time_fmt)[:-3], testName))

            fileSize = os.path.getsize(output_file)
            RestUtils.DebugPrint(RestUtils.logFP, 'Size of output file: %s Bytes' % fileSize)

            if fileSize > 0:
                return Global.PASS, ''

            else:
                return Global.FAIL, 'Empty file - No data'

        # For usual GET/POST methods, try to parse the response into json
        try:
            responseJson = response.json()
            logLine = responseJson['message']

        except:
            RestUtils.DebugPrint(RestUtils.logFP, 'Unable to parse response json')
            return False, ('Response Code: %s' % response)

        RestUtils.DebugPrint(RestUtils.logFP, '04Response Message: %s' % logLine)
        if responseJson['status'] != expectation['status']:
            return Global.FAIL, logLine

        # For negative test cases : expected is FAIL
        if not expectation.has_key("message"):
            if responseJson['status'] == expectation['status'] and expectation['status'] == 'FAIL':
                return Global.PASS, "Got expected result: %s" % logLine




            RestUtils.DebugPrint(RestUtils.logFP, '%d Expected data Found' % count)

        RestUtils.DebugPrint(RestUtils.logFP,
                   '%s  -  Test: %s  ---  COMPLETED.' % (datetime.now().strftime(time_fmt)[:-3], testName))
        if expectation.has_key("message"):
            if responseJson['status'].strip() == expectation['status'].strip() and expectation['message'].strip() == \
                    responseJson['message'].strip():
                if expectation.has_key('data'):
                    if responseJson['data'].strip() == expectation['data'].strip():
                        RestUtils.DebugPrint(RestUtils.logFP, 'Got expected data: %s' % responseJson['data'])
                        return Global.PASS, ''
                    else:
                        logLine = 'Actual data is: %s, Expected data is: %s' \
                                  % (responseJson['data'], expectation['data'])
                        print(responseJson['data'])
                        return Global.FAIL, logLine

                RestUtils.DebugPrint(RestUtils.logFP, 'Got expected message: %s' % responseJson['message'])
                return Global.PASS, ''


            else:
                logLine = 'Actual message is: %s, Expected message is: %s' \
                          % (responseJson['message'], expectation['message'])
                return Global.FAIL, logLine

        if responseJson['status'] == expectation['status']:
            RestUtils.DebugPrint(RestUtils.logFP, 'Got expected status: %s' % responseJson['status'])
            return Global.PASS, ''
        # Status not as expected - report FAIL
        else:
            RestUtils.DebugPrint(RestUtils.logFP, 'Expected status: %s, Got response: %s'
                       % (expectation['status'], responseJson['status']))
            return Global.FAIL, ''

    return wrapper


