from __future__ import absolute_import

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import auth

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse

import json
import pprint

import datetime
from time import sleep

from urlparse import urlparse

import os
import platform
import sys
from django.contrib.auth.models import User
from mhlib import PATH

from uploader import upload
from uploader import TestAuth
from uploader import UserInfo

from home.models import Filepath
from home.models import Metadata

from home import tasks

from celery import shared_task, current_task

from multiprocessing import Process

class MetaData(object):
    label = ""
    value = ""
    name = ""

    def __init__(self):
        pass

class FolderMeta(object):
    fileCount = 0
    dir_count = 0
    totalBytes = 0
    
    def __init__(self):
        pass

user = ''
current_time = ''
instrument = ''
password = ''
proposal = ''
propID = ''
selected_dirs = []
selected_files = []
dir_sizes = []
file_sizes = []
directory_history = []

# meta data values
metaList = []

# instruments
instrumentList = []
    
# instruments
proposalList = []

# process that handles bundling and uploading
bundle_process = None


def currentDirectory(history):
    dir = ''
    for path in history:
        dir = os.path.join(dir, path)
        dir = dir + "/"

    return dir

def getFolderSize(folder):
    total_size = os.path.getsize(folder)
    for item in os.listdir(folder):
        itempath = os.path.join(folder, item)
        if os.path.isfile(itempath):
            total_size += os.path.getsize(itempath)
        elif os.path.isdir(itempath):
            total_size += getFolderSize(itempath)
            
    return total_size

def getFolderMeta(folder, meta):

    meta.dir_count += 1

    for item in os.listdir(folder):
        itempath = os.path.join(folder, item)
        if os.path.isfile(itempath):
            meta.totalBytes += os.path.getsize(itempath)
            meta.fileCount += 1
        elif os.path.isdir(itempath):
            getFolderMeta(itempath, meta)

def getTuplesRecursive(folder, tuple_list, root_dir):

    for item in os.listdir(folder):
        path = os.path.join(folder, item)
        if os.path.isfile(path):
            relPath = path.replace(root_dir, '')
            tuple_list.append((path, relPath))
        elif os.path.isdir(path):
            getTuplesRecursive(path, tuple_list, root_dir)

# bundler takes a list of tuples
def getTuples(selected_list, tuple_list, root_dir):

    for path in selected_list:
        if os.path.isfile(path):
            # the relative path is the path without the root directory
            relPath = path.replace(root_dir, '')
            tuple_list.append((path, relPath))
        elif os.path.isdir(path):
            getTuplesRecursive(path, tuple_list, root_dir)

def getSizeString(total_size):
    # less than a Kb show b
    if (total_size < 1024):
        return str(total_size) + " b"
    # less than an Mb show Kb
    if (total_size < 1048576):
        kb = float(total_size) / 1024.0
        return str(round(kb, 2)) + " Kb"
    # less than a Gb show Mb
    elif (total_size < 1073741824):
        mb = float(total_size) / 1048576.0
        return str(round(mb, 2)) + " Mb"
    # else show in Gb
    else:
        gb = float(total_size) / 1073741824.0
        return str(round(gb, 2)) + " Gb"

def getFolderString(folder):

    meta = FolderMeta()
    getFolderMeta(folder, meta)

    print str(meta.fileCount) + "|" + str(meta.totalBytes)

    #total_size = getFolderSize(folder)
    meta.dir_count -= 1
    meta_str = 'folders ' + str(meta.dir_count) + '|files ' + str(meta.fileCount) + '|' + getSizeString(meta.totalBytes)

    return meta_str

def getFileString(filename):

    total_size = os.path.getsize(filename)

    return getSizeString(total_size)

#@login_required(login_url='/login/')
def list(request):

    global user
    print user

    global password
    # first time through go to login page
    if (password == ""):
        return render_to_response('home/login.html', {'message': ""}, context_instance=RequestContext(request))

    global selected_dirs
    global dir_sizes
    global selected_files
    global file_sizes
    global directory_history
    global metaList
    global instrumentList
    global proposalList
    global proposal
    global current_time

    rootDir = currentDirectory(directory_history)

    if rootDir == "": # first time through, initialize
        dataPath = Filepath.objects.get(name="dataRoot")
        if (dataPath is not None):
            rootDir = dataPath.fullpath
        elif ("Linux" in platform.platform(aliased=0, terse=0)):
            rootDir = "/home"
        else:
            rootDir = "c:\\"

        if (rootDir.endswith("\\")):
            rootDir = rootDir[:-1]
        directory_history.append(rootDir)
        rootDir = currentDirectory(directory_history)

        for meta in Metadata.objects.all():
            thingy = MetaData()
            thingy.label = meta.label
            thingy.name = meta.name
            thingy.value = ""
            metaList.append(thingy)

    checkedDirs = []
    uncheckedDirs = []
    checkedFiles = []
    uncheckedFiles = []

    contents = os.listdir(rootDir)

    for path in contents:

        fullPath = os.path.join(rootDir , path)

        if (os.path.isdir(fullPath)):
            if (fullPath in selected_dirs):
                checkedDirs.append(path)
            else:
                uncheckedDirs.append(path)
        else:
            if (fullPath in selected_files):
                checkedFiles.append(path)
            else:
                uncheckedFiles.append(path)

    # Render list page with the documents and the form
    return render_to_response('home/uploader.html',
        {'instrument': instrument, 
         'proposalList': proposalList,
         'proposal':proposal,  
         'directoryHistory': directory_history, 
         'metaList': metaList,
         'checkedDirs': checkedDirs, 
         'uncheckedDirs': uncheckedDirs, 
         'checkedFiles': checkedFiles, 
         'uncheckedFiles': uncheckedFiles, 
         'selectedDirs': selected_dirs, 
         'dirSizes': dir_sizes,
         'selectedFiles': selected_files, 
         'fileSizes': file_sizes,
         'current_time': current_time,
         'user': user},
        context_instance=RequestContext(request))


def modify(request):
    print 'modify ' + request.get_full_path()

    global user
    global password 
    global directory_history
    global selected_dirs
    global dir_sizes
    global selected_files
    global file_sizes
    global metaList
    global proposal
    global current_time
    global bundle_process
    global propID

    rootDir = currentDirectory(directory_history)

    if request.POST:

        print request.POST

        if (request.POST.get("Clear")):
            selected_files = []
            selected_dirs = []

        for m in metaList:
            value = request.POST.get(m.name)
            if (value):
                m.value = value
                print m.name + ": " + m.value

        proposal = request.POST.get("proposal")  
        print "proposal:  " + proposal

        split = proposal.split()
        propID = split[0]

        print propID

        if (request.POST.get("Upload Files & Metadata")):

            print "uploading now"

            dataPath = Filepath.objects.get(name="dataRoot")
            if (dataPath is not None):
                rootDir = dataPath.fullpath
            else:
                rootDir = ""

            # get the correct \/ orientation for the OS
            root = rootDir.replace("\\", "/")

            #create a list of tuples to meet the call format
            tupleList = []
            getTuples(selected_files, tupleList, root)            
            getTuples(selected_dirs, tupleList, root)
            print tupleList

            # create the groups dictionary
            #{"groups":[{"name":"FOO1", "type":"Tag"}]}
            groups = {}
            for m in metaList:
                groups[m.name] = m.value

            current_time = datetime.datetime.now().time().strftime("%m.%d.%Y.%H.%M.%S")

            targetPath = Filepath.objects.get(name="target")
            if (targetPath is not None):
                targetDir = targetPath.fullpath
            else:
                targetDir = rootDir

            bundleName = os.path.join(targetDir, current_time + ".tar")

            serverPath = Filepath.objects.get(name="server")
            if (serverPath is not None):
                sPath = serverPath.fullpath
            else:
                sPath = "dev1.my.emsl.pnl.gov"

            #return HttpResponseRedirect(reverse('home.views.list'))
            # spin this off as a background process and load the status page
            #task = tasks.sleeptask.delay(1, list)
            bundle_process = tasks.uploadFiles.delay(bundle_name = bundleName, 
                   instrument_name = instrument, 
                   proposal = propID, 
                   file_list=tupleList, 
                   groups = groups,
                   server=sPath,
                   user=user,
                   password=password)

            return render_to_response('home/status.html',
                {'instrument': instrument,
                 'status': 'Starting Upload',
                 'proposal':proposal,
                 'metaList': metaList,
                 'current_time': current_time,
                 'user': user},
                context_instance=RequestContext(request))
    else:
        o = urlparse(request.get_full_path())
        params = o.query.split("=")
        modType = params[0]
        path = params[1]

        # spaces
        path = path.replace("%20", " ")
        # backslash
        path = path.replace("%5C", "\\")

        full = os.path.join(rootDir, path)

        if (modType == 'enterDir'):
            rootDir = os.path.join(rootDir, path)
            directory_history.append(path)

        elif (modType == 'toggleFile'):
            if (full not in selected_files):
                selected_files.append(full) 
                file_sizes.append(getFileString(full))
            else:
                index = selected_files.index(full)
                selected_files.remove(full) 
                del file_sizes[index]
        elif (modType == 'toggleDir'):
            if (full not in selected_dirs):
                selected_dirs.append(full) 
                dir_sizes.append(getFolderString(full))
            else:
                index = selected_dirs.index(full)
                selected_dirs.remove(full) 
                del dir_sizes[index]
        elif (modType == "upDir"):
            index = int(path)
            del directory_history[index:]
            print currentDirectory(directory_history)

    return HttpResponseRedirect(reverse('home.views.list'))

def LoadUserInfo():
    userInfo = UserInfo(protocol="https",
                   server=sPath,
                   user=user,
                   insecure=True,
                   password=password,
                   negotiate = False,
                   verbose=True)
    print userInfo
    json_parsed = 0
    try:
        txt = json.loads(text)
        json_parsed = 1
    except Exception, ex:
        print "json failure"
    if json_parsed:
        print json.dumps(json.loads(text), sort_keys=True, indent=4, separators=(',', ': '))

def Login(request):
    global password   
    global user 
    global proposalList
    global instrument

    user = password = ''

    print "logging in"

    if request.POST:
        print "Post"
        user = request.POST['username']
        password = request.POST['password']

        serverPath = Filepath.objects.get(name="server")
        if (serverPath is not None):
            sPath = serverPath.fullpath
        else:
            sPath = "dev1.my.emsl.pnl.gov"

        auth = TestAuth(protocol="https",
                   server=sPath,
                   user=user,
                   insecure=True,
                   password=password,
                   negotiate = False,
                   verbose=True)

        if (not auth):
            password = ""     
            return render_to_response('home/login.html', {'message': "User or Password is incorrect"}, context_instance=RequestContext(request))

        print "password accepted"

        userInfo = UserInfo(protocol="https",
                   server=sPath,
                   user=user,
                   insecure=True,
                   password=password,
                   negotiate = False,
                   verbose=True)

        json_parsed = 0
        try:
            info = json.loads(userInfo)
            json_parsed = 1
        except Exception, ex:
            print "json failure"
        if json_parsed:
            print json.dumps(info, sort_keys=True, indent=4, separators=(',', ': '))

            obj = Filepath.objects.get(name="instrument")
            if (obj):
                instrument = obj.fullpath
            else:
                instrument = "unknown"

            print "instrument:  " + instrument

            print "instruments"
            instruments = info["instruments"]
            #pprint.pprint(instruments)

            instrumentList = []
            validInstrument = False
            for instID, instBlock in instruments.iteritems():
                instName = instBlock.get("instrument_name")
                instStr = instID + "  " + instName
                instrumentList.append(instStr)
                if (instrument == instID):
                    validInstrument = True
                print instStr
                print ""

            if (not validInstrument):
                password = ""
                return render_to_response('home/login.html', {'message': "User is not valid for this instrument"}, context_instance=RequestContext(request))

            print "props"
            props = info["proposals"]
            proposalList = []
            for propID, propBlock in props.iteritems():
                title = propBlock.get("title")
                propStr = propID + "  " + title
                proposalList.append(propStr)
                print propStr

                #for later
                instruments = propBlock.get("instruments")
                for i in instruments:
                    for j in i:
                        print j
                print ""

        return HttpResponseRedirect(reverse('home.views.list'))
    else:
        print "no Post"
        return render_to_response('home/login.html', context_instance=RequestContext(request))

def Logout(request):
    global password
    global user

    user = password = ''

    return HttpResponseRedirect(reverse('home.views.list'))


def status(request):
    global user
    global metaList
    global proposal
    global current_time
    global instrument

    global bundle_process

    output = bundle_process.state
    state = json.dumps(output)
    print state

    output = bundle_process.result
    result = json.dumps(output)
    print result

    if (bundle_process.status == 'SUCCESS'):
        return HttpResponseRedirect(reverse('home.views.list'))

    else:
        return render_to_response('home/status.html',
                {'instrument': instrument,
                 'status': state + " " + result,
                 'proposal':proposal,
                 'metaList': metaList,
                 'current_time': current_time,
                 'user': user},
                context_instance=RequestContext(request))


def incStatus(request):

    global bundle_process

    output = bundle_process.status
    state = output
    print state

    output = bundle_process.result
    result = output
    print result

    #if (bundleProcess.status == 'SUCCESS'):
    #    state = 'PROGRESS'

    if (result is not None):
        if "http" in result:
            state = 'DONE'
            result = result.strip('"')

    # create json structure
    retval = json.dumps({'state':state, 'result':result})

    return HttpResponse(retval)

    return HttpResponse(result)
