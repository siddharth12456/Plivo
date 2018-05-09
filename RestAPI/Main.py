import os
import Global
import RestUtils
import time
import os
import subprocess
import json
import traceback
import logging
import datetime as dt
import requests
# from Rest_Wrap_dnp import *
import sys
from Rest_WarpApi import *
import json



# from reportGenator import *
# reload(sys)


def Sleep(sleep_time):
    seconds = int(sleep_time)
    print('sleeping for %s seconds' % str(sleep_time))
    RestUtils.DebugPrint(RestUtils.logFP, "Sleeping for %s seconds" % str(sleep_time))
    #    elapsed = 0
    time.sleep(int(sleep_time))
    #    while elapsed < seconds:
    #        time.sleep(1)
    #        elapsed += 1
    return Global.PASS, ''


def ConfigureLogging(parsed_config):
    Global.log_path = parsed_config['log_path']

    configured_log_level = parsed_config['log_level'].lower()
    if configured_log_level == 'debug':
        log_level = logging.DEBUG
    elif configured_log_level == 'info':
        log_level = logging.INFO
    elif configured_log_level == 'warning':
        log_level = logging.WARNING
    elif configured_log_level == 'error':
        log_level = logging.ERROR
    elif configured_log_level == 'critical':
        log_level = logging.CRITICAL
    else:
        log_level = logging.DEBUG
    log_location = '%s/Plivo.log' % (parsed_config['log_path'])
    logging.basicConfig(filename=log_location, level=log_level, filemode='w',
                        format='%(asctime)s - %(levelname)s - %(message)s')







def SetupConnections(parsed_connections):
    session = None
    gotServerName = False
    gotUsername = False
    gotPassword = False
    gotdbUsername = False
    gotdbPassword = False
    gotdbServer = False
    server = ""
    username = ""
    password = ""
    dbServer = ""
    dbUsername = ""
    dbPassword = ""
    print( parsed_connections)
    for key, value in parsed_connections.items():
        if key == 'Server':
            server = value
            gotServerName = True
        elif key == 'Username':
            username = value
            gotUsername = True
        elif key == 'Password':
            password = value
            gotPassword = True
        elif key == 'mySQL Username':
            dbUsername = value
            gotdbUsername = True
        elif key == 'mySQL Password':
            dbPassword = value
            gotdbPassword = True
        elif key == 'mySQL Server':
            dbServer = value
            gotdbServer = True
        elif key == 'Connections':
            #   Configure Testset connections
            Global.connections = value

    if gotServerName and gotUsername and gotPassword:
        RestUtils.server = 'https://' + server
        RestUtils.username = username
        RestUtils.password = password
        # Suppress warnings due to invalid SSL cert
        requests.packages.urllib3.disable_warnings()
        session = requests.session()
        # Do not check authenticity of SSL certs
        session.verify = False
        # Login and recieve the SessionID; it is stored in the session's cookies
        logLine = ('Created a new session with server: %s, username: %s, and password %s.' % (
        RestUtils.server, RestUtils.username, RestUtils.password))
        RestUtils.logFP.write(logLine)
        print(logLine)
        #RestUtils.GetSessionID(session)
        RestUtils.session = session
        logLine = 'Got SessionID, but have not tested any requests yet'
        RestUtils.logFP.write(logLine)
        print(logLine)
    else:
        DebugPrint(RestUtils.logFP, "Need Plivo URL, username, and password to log on.")
        return False

    return True


def RunTestStep(test_name, testCount, stepCount, step, testcaseCSVfile):
    function_name = step['function_name']

    del step['function_name']
    del step['skip']
    try:
        del step['comment']
        # del step['description']
    except:
        pass
    args = RestUtils.byteify(step)

    # call each step
    testStartTime = time.time()
    RestUtils.DebugPrint(RestUtils.logFP,
               '\n%s - Test #%d:%d %s' % (time.strftime('%H:%M:%S'), testCount, stepCount, function_name))
    try:
        testComment = "RunTestStep: %s " % test_name
        RestUtils.DebugPrint(RestUtils.logFP, "function_name is %s" % str(function_name))
        #print(getNumber)
        result, testComment = globals()[function_name](**args)

        #RestUtils.DebugPrint(RestUtils.logFP, 'Main-RunTestStep() result is %s\n' % result)
    except:
        RestUtils.DebugPrint(RestUtils.logFP, str(traceback.print_exc()))
        # testComment = 'Exception in test step. May cause other test steps to fail. Continuing . . .'
        #RestUtils.DebugPrint(RestUtils.logFP, testComment)
        result = Global.FAIL
    testElapsedTime = time.time() - testStartTime
    timeString = "%.2f" % round(testElapsedTime, 3)

    if result == Global.PASS:
        testResult = 'PASS'
    else:
        testResult = 'FAIL'

    formatted_args = RestUtils.FormatParams(args)
    # formatted_args, expected_values = FormatParamsPart(args)
    testcaseCSVfile.write('%d : %d %s, %s, %s, %s, %s\n'
                          % (testCount, stepCount, function_name, formatted_args, testResult, timeString, testComment))
    testcaseCSVfile.flush()

    # formatted_args = FormatParamsNoDesc(args)
    formatted_args, expected_values = RestUtils.FormatParamsPart(args)
    logCSVFP_line = ' ,%s, %s, %s, %s, %s, %s\n' % (
    function_name, formatted_args, expected_values, testResult, timeString, testComment)

    RestUtils.DebugPrint(RestUtils.logFP, "Test: %s  Step: %d  %s  Result: %s  %s\n" % (
    test_name, stepCount, function_name, testResult, testComment))
    return result, testComment, logCSVFP_line


def RunTest(testCount, test, log_file_directory):
    ##HiptestObj = #Hiptest("sroy@sentient-energy.com", "test123")
    test_name = test['Test_Name']
    #Hiptest_name = test['#HiptestName']
    test_id = "46692"
    # response = ##HiptestObj.get_test_run("46692", "136388")
    # print(response.json())
    # print('The automation #Hiptest run cycle is------->' + str(response.json()['data']['attributes']['name']))
    description = test['Description']
    steps = test['Steps']

    testcaseCSVfilename = '%s/%s.csv' % (log_file_directory, test_name)
    testcaseCSVfile = open(testcaseCSVfilename, 'w')
    testcaseCSVfile.write("Test Name: %s,Target: %s\n" % (test_name, Global.target))
    testcaseCSVfile.write("Test Steps, Parameters, Step Result, Total Run Time, Comment\n")

    testComment = None
    totalPass = 0
    totalFail = 0
    totalSkip = 0
    stepCount = 0

    reportPass = 0
    reportFail = 0

    functions_called = []

    result = Global.PASS
    testResult = "PASS"
    RestUtils.DebugPrint(RestUtils.logFP, "Before Test: %s" % test_name)
    testStartTime = time.time()
    logCSVFP_test_steps = ''
    # run the test steps
    for step in steps:
        if test == 'End_Test':
            break
        stepCount += 1
        function_name = step["function_name"]
        if step['skip']:
            # Skip test steps with skip flag set to true
            testcaseOutputLine = '%d : %d %s, , SKIP, ,\n' % (testCount, stepCount, function_name)
            testcaseCSVfile.write(testcaseOutputLine)
            testcaseCSVfile.flush()
            RestUtils.DebugPrint(RestUtils.logFP,
                       "%d : %d  Test %s Step: %s Result: SKIP\n" % (testCount, stepCount, test_name, function_name))
            totalSkip += 1
            continue
        result = Global.PASS
        result, stepComment, logCSVFP_line = RunTestStep(test_name, testCount, stepCount, step, testcaseCSVfile)

        if not (function_name == "Sleep" or function_name.startswith("Database")):
            logCSVFP_test_steps += logCSVFP_line
            if result == Global.FAIL:
                reportFail += 1
            else:
                reportPass += 1

        if result == Global.FAIL:
            totalFail += 1
            testResult = "FAIL"
            if testComment is None:
                testComment = stepComment
        else:
            totalPass += 1

    testElapsedTime = time.time() - testStartTime
    timeString = "%.2f" % round(testElapsedTime, 3)
    testcaseOutputLine = '%d : %s, , %s, %s, %s\n' % (testCount, test_name, testResult, timeString, testComment)
    testcaseCSVfile.write(testcaseOutputLine)
    #HiptestDict = ##HiptestObj.generate_test_id_pairs('46692', '136388')
    testcaseCSVfile.flush()

    # testOutputLine = '%d : %s, , , , %s ,%s ,%s\n' % ( testCount, test_name, testResult, timeString, testComment )
    testOutputLine = '%d : %s, , , , , %s \n' % (testCount, test_name, timeString)

    RestUtils.testReportCSVFP.write(testOutputLine)
    RestUtils.testReportCSVFP.write(logCSVFP_test_steps)

    RestUtils.testReportCSVFP.write(' ,    Steps Passed   : %d\n' % reportPass)
    RestUtils.testReportCSVFP.write(' ,    Steps Failed     : %d\n' % reportFail)

    RestUtils.testReportCSVFP.flush()

    testcaseCSVfile.write('Total Steps in Testcase, %d\n' % stepCount)
    testcaseCSVfile.write('Total Steps Skipped, %d\n' % totalSkip)
    testcaseCSVfile.write('Total Steps Passed, %d\n' % totalPass)
    testcaseCSVfile.write('Total Steps Failed, %d\n' % totalFail)

    RestUtils.DebugPrint(RestUtils.logFP, "After Test: %s  Result: %s" % (test_name, testResult))
    RestUtils.DebugPrint(RestUtils.logFP, 'Total Test Time: %s seconds' % timeString)
    RestUtils.DebugPrint(RestUtils.logFP, 'Total Steps in Testcase: %d' % stepCount)
    RestUtils.DebugPrint(RestUtils.logFP, 'Total Steps Skipped: %d' % totalSkip)
    RestUtils.DebugPrint(RestUtils.logFP, 'Total Steps Passed: %d' % totalPass)
    RestUtils.DebugPrint(RestUtils.logFP, 'Total Steps Failed: %d\n' % totalFail)
    testcaseCSVfile.close()

    return totalPass, totalFail, totalSkip, stepCount, reportPass, reportFail


def RunAllTests(tests, log_file_directory):
    # Run tests
    # initialize test reporting params:
    testCount = 0
    totalPass = 0
    totalFail = 0
    totalSkip = 0
    startTime = time.time()
    totalStepPass = 0
    totalStepFail = 0
    totalStepSkip = 0
    totalStepCount = 0
    testStepPass = 0
    testStepFail = 0
    testStepSkip = 0
    testStepCount = 0
    totalReportPass = 0
    totalReportFail = 0
    totalReportSkip = 0

    # run the tests
    for test in tests:
        if test == 'End_Test':
            break
        testCount += 1
        reportPass = 0
        reportFail = 0
        if test['skip']:
            # Skip tests with skip flag set to true
            test_name = test['Test_Name']
            RestUtils.DebugPrint(RestUtils.logFP, "%d  Test %s Result: SKIP\n" % (testCount, test_name))
            totalSkip += 1
            continue

        # Two modes: module-wise and test-wise
        # Module mode will assume that the tests are in a different
        #  file. It will open the testfile (should be in test-wise
        #  format) and run the tests one by one.
        # Test-wise mode will assume the test is in the main test file
        #  and calls the test directly.
        # Both modes can be mixed in one file.
        if 'Module' in test:
            RestUtils.testReportCSVFP.write('Module: %s\n' % test['Module'])
            with open(test['test_json'], 'r') as submodule_json:
                parsed_submodule = json.load(submodule_json)
            for submodule_test in parsed_submodule['Tests']:
                testCount += 1
                if submodule_test['skip']:
                    test_name = test['Test_Name']
                    RestUtils.DebugPrint(RestUtils.logFP, "%d  Test %s Result: SKIP\n" % (testCount, test_name))
                    totalSkip += 1
                    continue

                testStepPass, testStepFail, testStepSkip, testStepCount, _, _ = RunTest(stepCount, testCount,
                                                                                        submodule_test,
                                                                                        log_file_directory)
                if testStepFail == 0:
                    totalPass += 1
                else:
                    totalFail += 1
                totalStepPass += testStepPass
                totalStepFail += testStepFail
                totalStepSkip += testStepSkip
                totalStepCount += testStepCount

        else:
            testStepPass, testStepFail, testStepSkip, testStepCount, reportPass, reportFail = \
                RunTest(testCount, test, log_file_directory)
            if testStepFail == 0:
                totalPass += 1
            else:
                totalFail += 1
            totalStepPass += testStepPass
            totalStepFail += testStepFail
            totalStepSkip += testStepSkip
            totalStepCount += testStepCount

            totalReportPass += reportPass
            totalReportFail += reportFail
            # totalReportSkip += reportSkip

    # finalize the test report
    totalTime = time.time() - startTime
    timeString = "%.2f" % round(totalTime, 3)

    RestUtils.testReportCSVFP.write('Total Run Time (seconds), %s\n' % (timeString))
    #    RestUtils.logCSVFP.write('Total Steps, %d\n' % (totalStepCount) )
    #    RestUtils.logCSVFP.write('Total Steps Pass, %d\n' % (totalStepPass) )
    #    RestUtils.logCSVFP.write('Total Steps Fail, %d\n' % (totalStepFail) )
    #    RestUtils.logCSVFP.write('Total Steps Skip, %d\n' % (totalStepSkip) )
    RestUtils.testReportCSVFP.write('Total Test Passed, %d\n' % totalReportPass)
    RestUtils.testReportCSVFP.write('Total Test Failed, %d\n' % totalReportFail)
    # RestUtils.logCSVFP.write( 'Total Test Skipped  : %d\n' % totalReportSkip )

    #    RestUtils.DebugPrint( RestUtils.logFP, 'Total Testcase Steps: %s' % totalStepCount )
    #    RestUtils.DebugPrint( RestUtils.logFP, 'Total Skipped: %d' % totalStepSkip )
    #    RestUtils.DebugPrint( RestUtils.logFP, 'Total Passed : %d' % totalStepPass )
    #    RestUtils.DebugPrint( RestUtils.logFP, 'Total Failed : %d' % totalStepFail )

    #    RestUtils.DebugPrint( RestUtils.logFP, 'Total Test Time: %s seconds' % timeString )
    #    RestUtils.DebugPrint( RestUtils.logFP, 'Total Testcases: %d' % testCount )
    #    RestUtils.DebugPrint( RestUtils.logFP, 'Total Skipped: %d' % totalSkip )
    RestUtils.DebugPrint(RestUtils.logFP, 'Total Passed: %d' % totalReportPass)
    RestUtils.DebugPrint(RestUtils.logFP, 'Total Failed: %d' % totalReportFail)


if __name__ == '__main__':
    """Order of events is: Main -> SetupConfig -> SetupConnections -> RunAllTests -> Send email -> done"""
    if len(sys.argv) == 3:
        #  Get test config. In template, there are:
        #  parsed_config["Config"] - contains test variables
        #  parsed_config["Email"] - configure email report
        executionTime = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(sys.argv[1], 'r') as config_json:
            parsed_config = json.load(config_json)

        # Get test connections. In template, there are:
        #  parsed_connections["Connections"] - Plivo ip address
        with open(sys.argv[2], 'r') as connections_json:
            parsed_connections = json.load(connections_json)

        # with open(sys.argv[3], 'r') as test_json:
        #     parsed_json = json.load(test_json)

        test_filecount = 0
        parsed_json = dict()
        for item in parsed_config['tests_group']:
            if parsed_config['tests_group'][item]:
                parsed_json_path = str(parsed_config['InputTestfiles'][item])
                # print('The test group -------'+str(item)+' will be executed in this run '+'Input files path is --------'+str(parsed_json_path))
                with open(parsed_json_path, 'r') as connections_json:
                    test_temp = json.load(connections_json)
                    print(test_temp)
                    if test_filecount == 0:
                        parsed_json.update(test_temp)

                    else:
                        parsed_json['Tests'] = test_temp['Tests'] + parsed_json['Tests']
                    test_filecount = test_filecount + 1
        # kick off the test
        # print(test_filecount)
        # print(test_filecount['Tes '])

        # initialize test values
        Global.test_count = 0

        ConfigureLogging(parsed_config['Config'])
        log_file_directory = parsed_config['Config']['test_report_path']
        RestUtils.testReportCSVFP = open('%s/test_report.csv' % log_file_directory, 'w')
        RestUtils.logFP = open("%s/full.log" % log_file_directory, 'w')
        # RestUtils.DebugPrint( RestUtils.logFP, 'Main-RunAllTests(): test_json is %s\n' % test_json )
        okay = SetupConnections(parsed_connections)
        if not okay:
            print("Unable to run tests without valid connection.\n")
            exit()

        RunAllTests(parsed_json['Tests'], log_file_directory)

        RestUtils.testReportCSVFP.close()

        # genrateReport(executionTime)
        RestUtils.logFP.close()

        #Global.sysChild.logfile.close()
        #Global.sysChild.close()
    else:
        print('Missing input file.\n')
        print('Usage: python %s config_file connection_file test_file\n' % sys.argv[0])
