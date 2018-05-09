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
            if "alertsubscriptions" in full_path:
                print("changed the full_path")
                full_path = '/em/rest/alertsubscriptions/addorupdate'

            if "sites" in full_path:
                restParams['params'] = {"type": "SITE", "name": "rest_site1", "poleLocation": "", "address": "",
                                        "lon": "",
                                        "lat": "", "overrideGps": False}
                restParams['params']["name"] = payload['group_tree'][3]

            print(str(RestUtils.server + full_path) + '---this the post url')
            print(str(restParams))
            response = RestUtils.session.post(RestUtils.server + full_path, **restParams)
            responseJson = response.json()
            print "post response is %s\n" % response

        elif method == 'export':
            timeParams = restParams['params']

            restParams = {'allow_redirects': True, 'params': timeParams}

            # restParams['params'] = {'timestamp' : st_milli, 'endtimestamp' : end_milli, 'timezone': 'America/Los_Angeles'}
            print 'REST -- PARAMS: ', restParams

            response = RestUtils.session.get(RestUtils.server + full_path, **restParams)
            print "get export response is %s\n" % response

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

        if ntype == 'PROGRESS' and str(expectation['status']) != "FAIL":
            # check for job progress
            RestUtils.DebugPrint(RestUtils.logFP, '%s  -  Now waiting for the job to be completed. Checking progress...'
                       % (datetime.now().strftime(time_fmt)[:-3]))

            if len(operations) > 3:
                path2 = operations[3]  # path for checking job status
            else:
                path2 = full_path

            timeout = kwargs['timeout']
            timeout = int(timeout)
            RestUtils.DebugPrint(RestUtils.logFP, 'tttttttttttimeout is %d\n ' % (timeout))

            path2 = re.sub('{orgId}', orgId, path2)
            print '01if ntype == PROGRESS: path2 is %s' % path2
            print ('02rrrrrrrrrrrrrresponse is %s, expectation is %s\n ' % (response, expectation))
            RestUtils.DebugPrint(RestUtils.logFP, '30response.text is %s, expectation is %s\n ' % (response.text, expectation))

            if 'jobStatus' in expectation or 'otapStatus' in expectation:
                _, jobName = RestUtils.getJobName(path2, expectation['status'])

                if 'jobStatus' in expectation and 'otapStatus' not in expectation:
                    path2 = '%s/%s' % (path2, 'details')
                    # data_item = 'configDetails'
                    params = {'configJobName': jobName}
                else:  # otap
                    path2 = '%s/%s/%s' % (path2, jobName, 'devices')
                    path = "/em/rest/upgrade/softwares/jobs"
                    RestUtils.DebugPrint(RestUtils.logFP, 'AmpleApiUtils.py - 00path is %s\n ' % (path))
                    RestUtils.DebugPrint(RestUtils.logFP, 'AmpleApiUtils.py - 00path2 is %s\n ' % (path2))
                    # data_item = 'jobStatusDetail'
                    params = {}
                    path2 = path

            elif 'deviceStatus' in expectation:
                params = {'pageNo': '1', 'pageSize': '10'}
                # data_item = ''

            elif 'waveformStatus' in expectation:
                # data_item = ''
                params = {}

            elif 'logiStatus' in expectation:
                params = restParams['params']
                # data_item = expectation['logiStatus']  #  'pointData'

            else:
                RestUtils.DebugPrint(RestUtils.logFP,
                           'Status should be device/profile/waveform/otap status - for checking progress...')
                return Global.FAIL, ''

            result, logLine = CheckProgressJobStatus(devices, path2, expectation, params, timeout)
            if result == "Need to retry":
                print("siddharth code is reached")
                jobNamePath = "/em/rest/upgrade/softwares/jobs"
                # time.sleep(10)
                response = RestUtils.session.get(RestUtils.server + jobNamePath, allow_redirects=True)
                jobName = response.json()['data'][0]['jobName']
                full_path = "/em/rest/upgrade/softwares/jobs/" + jobName + "/devices/retrymultiple"
                print(str(restParams) + 'post params')
                full_path3 = "/em/rest/upgrade/softwares/jobs/" + jobName + "/devices"
                response = RestUtils.session.get(RestUtils.server + full_path3, allow_redirects=True)
                jobId = response.json()['data']['deviceDetails'][0]['id']
                print("siddharth" + str(jobId))
                list1 = [jobId]
                print("siddharth the retry full path is" + full_path)
                response = RestUtils.session.post(RestUtils.server + full_path, json=list1, params=params,
                                                  allow_redirects=True)
                time.sleep(5)
                print("siddharth----------------------------------------" + str(response.json()))
                result = CheckProgressJobStatus(devices, path2, expectation, params, timeout)
                if result == "Need to retry":
                    return Global.FAIL, 'Failed after retry also'
            startTime = default_timer()

            # result not True
            if not result:
                return Global.FAIL, logLine

        if ntype == 'data':

            if 'value' in expectation:
                item = expectation['item']
                value = expectation['value']
                if responseJson['data'][0][item] != value:
                    return Global.FAIL, 'No matching data found'

            # Continue with printing all the response data
            RestUtils.DebugPrint(RestUtils.logFP, 'Checking for response data. ')
            count = 0
            for each in responseJson['data']:
                RestUtils.DebugPrint(RestUtils.logFP, 'DATA: %s' % (each))
                count = count + 1

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


# Helper functions for: device, Otap, profile, logi, waveform - that need to check job progress.
def CheckProgressJobStatus(devices, path, expectation, params, wait_time):
    # Check the Job status, within alloted time.

    slept = 0
    A, B = 2, 3  # variables for Fibonacci sequence...
    logLine = ''

    time_fmt = "%H:%M:%S.%f"  # format for log timestame

    print 'INPUTS::devices - ', devices
    print 'INPUTS::path - ', path
    print 'INPUTS::expectation - ', expectation
    print 'INPUTS::wait_time - ', wait_time

    RestUtils.DebugPrint(RestUtils.logFP, 'wait_time is %d\n' % wait_time)
    RestUtils.DebugPrint(RestUtils.logFP, 'HTTP Method: POST/GET  :::  URL Path for Job Status: %s' % path)

    while slept < wait_time:
        response = RestUtils.session.post(RestUtils.server + path, json={}, params=params, allow_redirects=True)
        RestUtils.DebugPrint(RestUtils.logFP, 'slept is %d, wait_time is %d\n' % (slept, wait_time))
        RestUtils.DebugPrint(RestUtils.logFP, '00params is %s\n' % (params))
        RestUtils.DebugPrint(RestUtils.logFP, '%s  -  05Response: %s' % (datetime.now().strftime(time_fmt)[:-3], response.text))

        if 'deviceStatus' in expectation:
            RestUtils.DebugPrint(RestUtils.logFP, 'deviceStatus is is in expection %s' % expectation)
            RestUtils.logFP.flush()

            device = response.json()['data']['devices']
            RestUtils.DebugPrint(RestUtils.logFP, 'deviceList is %s' % device)
            RestUtils.logFP.flush()
            # for device in deviceList:
            RestUtils.DebugPrint(RestUtils.logFP, "%s   ===>   %s\n%s   ===>   %s" % (
            device[0]['serialNumber'], devices[0], device[0]['status'], expectation['deviceStatus']))
            RestUtils.DebugPrint(RestUtils.logFP,
                       "device[serialNumber] is %s, devices[0] is %s, device[0][status] is %s, expectation[deviceStatus] is %s\n" % (
                       device[0]['serialNumber'], devices[0], device[0]['status'], expectation['deviceStatus']))
            RestUtils.logFP.flush()

            if device[0]['serialNumber'] == devices[0] and device[0]['status'] == expectation['deviceStatus']:
                return True, ''


            elif slept < wait_time:
                RestUtils.DebugPrint(RestUtils.logFP,
                           '\n04Waited %s seconds, no result yet. Sleeping for 2 seconds..., wait_time is %d ' % (
                           slept, wait_time))
                time.sleep(2)
                slept += 2

                logLine = 'Waited for %d seconds, could not finish the job.' % (slept)
                continue
        else:
            # if 'deviceStatus' not in expectation :
            # check for OTAP or Config status, LogI status
            print "if 'deviceStatus' not in expectationnnnnnnnnnnnnnnnnnn %s\n" % expectation
            #            response = RestUtils.session.get(RestUtils.server + path, params=params, allow_redirects=True)
            if 'configStatus' not in expectation and 'logiStatus' not in expectation:
                response = RestUtils.session.get(RestUtils.server + path, allow_redirects=True)
            RestUtils.DebugPrint(RestUtils.logFP,
                       'AmpleApiUtils.py get RestUtils.server: %s\n  path is %s\n' % (RestUtils.server, path))
            RestUtils.DebugPrint(RestUtils.logFP,
                       '%s  -  06Response: %s' % (datetime.now().strftime(time_fmt)[:-3], response.text))
            RestUtils.DebugPrint(RestUtils.logFP, '07Response status code is %d' % response.status_code)

            if not response.status_code == 200:
                if slept < wait_time:
                    RestUtils.DebugPrint(RestUtils.logFP,
                               '\n05Waited %s seconds, no result yet. Sleeping for 2 seconds..., wait_time is %d ' % (
                               slept, wait_time))
                    time.sleep(2)
                    slept += 2

                    logLine = 'Waited for %d seconds, could not finish the job.' % (slept)
                    continue
                else:
                    logLine = 'Bad status returned while trying to get upgrade job details'
                    return Global.FAIL, logLine

            jobJson = response.json()
            jobItem = response.json()['data']
            RestUtils.DebugPrint(RestUtils.logFP, "01response.text is %s\n" % response.text)
            RestUtils.DebugPrint(RestUtils.logFP, "00jobJson is %s\n" % jobJson)
            RestUtils.DebugPrint(RestUtils.logFP, "00jobItem is %s\n" % jobItem)
            if 'waveformStatus' in expectation:
                print "iiiiiiiiiiiiiiiif 'waveformStatus' in expectation\n"
                RestUtils.DebugPrint(RestUtils.logFP, "02jobJson[data'] is %s\n" % jobJson['data'])
                RestUtils.DebugPrint(RestUtils.logFP, "response is %s\n" % response)
                if len(jobJson['data']) > 0:
                    # for item in jobJson['data']:
                    item_status = jobItem[0]['captures'][0]['details']['status']
                    RestUtils.DebugPrint(RestUtils.logFP, "item_status is %s\n" % item_status)
                    RestUtils.DebugPrint(RestUtils.logFP, "\nDecoRestAPI() - 03rrrrrrrrrrrrrrresponse is %s" % response)

                    RestUtils.DebugPrint(RestUtils.logFP,
                               'Waveform response progress status [CAPTURES] :  item_status is %s' % item_status)
                    RestUtils.DebugPrint(RestUtils.logFP,
                               "jobJson['status'] is %s, expectation['status'] is %s, expectation['waveformStatus'] is %s\n" % (
                               jobJson['status'], expectation['status'], expectation['waveformStatus']))
                    if jobJson['status'] == expectation['status'] and item_status == expectation['waveformStatus']:
                        RestUtils.DebugPrint(RestUtils.logFP, '00HTTP Response: %s' % response.text)

                        return Global.PASS, 'Found waveform for respective site'
                    elif slept < wait_time:
                        RestUtils.DebugPrint(RestUtils.logFP,
                                   '\n06Waited %s seconds, no result yet. Sleeping for 2 seconds..., wait_time is %d ' % (
                                   slept, wait_time))
                        time.sleep(2)
                        slept += 2

                        logLine = 'Waited for %d seconds, could not finish the job.' % (slept)
                        continue

                elif slept < wait_time:
                    RestUtils.DebugPrint(RestUtils.logFP,
                               '\n00Waited %s seconds, no result yet. Sleeping for 2 seconds..., wait_time is %d ' % (
                               slept, wait_time))
                    time.sleep(2)
                    slept += 2

                    logLine = 'Waited for %d seconds, could not finish the job.' % (slept)
                    continue
                else:
                    logLine = 'Waited for %d seconds, could not finish the job.' % (slept)
                    return False, logLine
            else:
                print "000if not 'waveformStatus' in expectation:\n"
                RestUtils.DebugPrint(RestUtils.logFP, "CheckProgressJobStatus() 000response.json() is %s\n" % response.json())
                RestUtils.DebugPrint(RestUtils.logFP,
                           "CheckProgressJobStatus() 001response.json()['data'] is %s\n" % response.json()['data'])
                RestUtils.DebugPrint(RestUtils.logFP, "CheckProgressJobStatus() 000jobItem is %s\n" % jobItem)
                print '################### None\n'
                if 'otapStatus' in expectation:
                    RestUtils.DebugPrint(RestUtils.logFP, "if 'otapStatus' in expectation :\n")
                    RestUtils.DebugPrint(RestUtils.logFP, "%s   ===>   %s\n%s   ===>   %s\n%s   ===>   %s" % (
                        response.json()['status'], expectation['status'],
                        response.json()['data'][0]['status'], expectation['jobStatus'],
                        jobItem[0]['serialNumbers'][0], devices[0]))
                    print("siddharth---0000" + str(jobItem[0]['status']))
                    if jobItem[0]['status'] == "FAILED":
                        RestUtils.DebugPrint(RestUtils.logFP,
                                   '%s  -  Response: %s' % (
                                       datetime.now().strftime(time_fmt)[:-3], jobItem[0]['status']))
                        return "Need to retry"

                    if (response.json()['status'] == expectation['status'] and
                            response.json()['data'][0]['status'] == expectation['jobStatus'] and
                            jobItem[0]['serialNumbers'][0] == devices[0]):
                        return Global.PASS, ''
                    elif slept < wait_time:
                        RestUtils.DebugPrint(RestUtils.logFP,
                                   '\n01Waited %s seconds, no result yet. Sleeping for 2 seconds..., wait_time is %d ' % (
                                   slept, wait_time))
                        time.sleep(2)
                        slept += 2

                        logLine = 'Waited for %d seconds, could not finish the job.' % (slept)
                        continue

                elif 'configStatus' in expectation:
                    if 'jobStatus' in expectation:
                        RestUtils.DebugPrint(RestUtils.logFP, "01jobJson is %s\n" % jobJson)
                        RestUtils.DebugPrint(RestUtils.logFP, "jobItem is %s\n" % jobItem)
                        RestUtils.DebugPrint(RestUtils.logFP, "expectation is %s\n" % expectation)
                        RestUtils.logFP.flush()

                        if (jobJson['status'] == expectation['status'] and
                                jobItem['configDetails'][0]['configStatus'] == expectation['configStatus'] and
                                jobItem['configDetails'][0]['jobStatus'] == expectation['jobStatus'] and
                                jobItem['configDetails'][0]['serialNumber'] == devices[0]):

                            RestUtils.DebugPrint(RestUtils.logFP, '%s  -  02Response: %s' % (
                            datetime.now().strftime(time_fmt)[:-3], jobItem['configDetails'][0]['jobStatus']))
                            return True, ''
                        elif slept < wait_time:
                            RestUtils.DebugPrint(RestUtils.logFP,
                                       '\n02Waited %s seconds, no result yet. Sleeping for 2 seconds..., wait_time is %d ' % (
                                       slept, wait_time))
                            time.sleep(2)
                            slept += 2

                            logLine = 'Waited for %d seconds, could not finish the job.' % (slept)
                            continue
                        else:
                            logLine = "Did not get the expected status yet."
                            return False, logLine


                elif 'logiStatus' in expectation:
                    RestUtils.DebugPrint(RestUtils.logFP, 'logiStatus in expectation')
                    RestUtils.DebugPrint(RestUtils.logFP, '222jobItem is %s\n' % jobItem)
                    RestUtils.logFP.flush()

                    try:
                        if (jobJson['status'] == expectation['status']):
                            if (jobItem['pointData'][0]['ai'] > 0 and jobItem['pointData'][0]['at'] > 0 or
                                    jobItem['pointData'][0]['bi'] > 0 and jobItem['pointData'][0]['bt'] > 0 or
                                    jobItem['pointData'][0]['ci'] > 0 and jobItem['pointData'][0]['ct'] > 0):
                                RestUtils.DebugPrint(RestUtils.logFP,
                                           'Current / Temperature [A,B,C] ==>  %s, %s, %s, %s, %s, %s: '
                                           % (jobItem['pointData'][0]['ai'], jobItem['pointData'][0]['at'],
                                              jobItem['pointData'][0]['bi'], jobItem['pointData'][0]['bt'],
                                              jobItem['pointData'][0]['ci'], jobItem['pointData'][0]['ct']))

                                return True, 'Found logi points for the site.'
                        else:
                            logLine = '00No LOGi value found in allotted time'
                            return False, 'Not found logi points for the site.'
                    except Exception as e:
                        if slept < wait_time:
                            RestUtils.DebugPrint(RestUtils.logFP,
                                       '\n03Waited %s seconds, no result yet. Sleeping for 2 seconds..., wait_time is %d ' % (
                                       slept, wait_time))
                            time.sleep(2)
                            slept += 2

                            logLine = 'Waited for %d seconds, could not finish the job.' % (slept)
                            RestUtils.DebugPrint(RestUtils.logFP, 'LogI data is not available yet. Trying again....')
                            continue
                        else:
                            logLine = '01No LOGi value found in allotted time'
                            return False, 'Not found logi points for the site.'
                # Get updated timestamp for 'now'
                if 'logiStatus' in expectation:
                    end_milli = int(time.time() * 1000)
                    params['endtimestamp'] = end_milli
                    print 'wrapper() inputParams >>>>>', params
                elif slept < wait_time:
                    RestUtils.DebugPrint(RestUtils.logFP,
                               '\n03Waited %s seconds, no result yet. Sleeping for 2 seconds..., wait_time is %d ' % (
                               slept, wait_time))
                    time.sleep(2)
                    slept += 2

                    logLine = 'Waited for %d seconds, could not finish the job.' % (slept)
                    continue

    return False, logLine


def update_dict(old_dict, new_data):
    # update the existing payload dict with new data

    xpath = new_data['path']
    xvalue = new_data['value']
    xlen = len(xpath)

    # traverse the dict path, update the property value
    if xlen == 5:
        old_dict[xpath[0]][xpath[1]][xpath[2]][xpath[3]][xpath[4]] = xvalue

    elif xlen == 4:
        old_dict[xpath[0]][xpath[1]][xpath[2]][xpath[3]] = xvalue

    elif xlen == 3:
        old_dict[xpath[0]][xpath[1]][xpath[2]] = xvalue

    elif xlen == 2:
        old_dict[xpath[0]][xpath[1]] = xvalue

    elif xlen == 1:
        old_dict[xpath[0]] = xvalue
    print(old_dict)
    return old_dict


