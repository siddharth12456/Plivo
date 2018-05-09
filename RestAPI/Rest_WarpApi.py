import requests
import RestUtils
import Global

from  AmpleApiUtils import *


@DecoRestAPI
def getNumberPlivo(*arg, **kwargs):
    path1 = "Account/{auth_id}/Number/"
    method1 = 'get'
    ntype = 'Number'
    operations = [path1, method1, ntype]
    return operations


@DecoRestAPI
def UnregisterDevice(*args, **kwargs):
    path1 = "/em/rest/devices/unregister"
    method1 = 'post'

    operations = [path1, method1]
    return operations