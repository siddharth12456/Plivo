def DebugPrint(logFP, outputString):
    print(outputString)
    logFP.write( "%s\n" % outputString )



def byteify(input):
    """A helper function that converts unicode strings to byte strings. It
        should be called after importing json. (i.e. json.load() or
        json.loads()).

    Args:
        input (dict, list or unicode): The object to be converted to strings

    Returns:
        dict, list or str: The bytestring that once was unicode strings

    """
    if isinstance(input, dict):
        return {byteify(key): byteify(value) for key, value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

def FormatParams(dictParams):
    """Returns the arguments for the tests as a neatly formatted string
    to write to the test report."""

    if len(dictParams) == 0:
        return 'None'
    params = ''

    i = 0
    for key in dictParams:
        value = str( dictParams[ key ] )
        value = value.replace( ",", " " )
        params += '%s: [%s]  ' % (key, value )
    return params


def FormatParamsPart(dictParams):
    """Returns the arguments for the tests as a neatly formatted string
    to write to the test report."""

    if len(dictParams) == 0:
        return 'None'

    param_values = ''
    expect_values = ''

    # i = 0
    for key in dictParams:

        if key == 'description':
            continue

        value = str(dictParams[key])
        value = value.replace(",", "   ")

        # print 'VALUEEE: ', value, key

        if key == 'expectation':
            expect_values += '[%s] ' % (value)

        elif key == 'parameters':  # in value:
            # print ' PATH key i herererere ', key, dictParams['parameters'], dictParams['parameters'].keys()
            if 'property ' in dictParams['parameters'].keys():
                # print ' PATH PROPERTY '
                if 'path' in dictParams['parameters']['property']:
                    val = dictParams['parameters']['property']['path'][-1]
                    dictParams['parameters']['property']['path'] = [val]
                    # value['property']['path'] = [ value['parameters']['property']['path'] [-1]  ]
                    # print 'PATH  PROP: ', val, dictParams['parameters']
                    value = str(dictParams['parameters']).replace(",", "   ")

            param_values += '[%s] ' % (value)

        else:

            param_values += '[%s]  ' % (value)

        # print 'PARAMssss: ', expect_values, param_values

    return param_values, expect_values