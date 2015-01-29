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
from uploader import test_authorization
from uploader import user_info

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

# Module level variables
user = ''
current_time = ''
instrument = ''
password = ''
proposal_verbose = ''
proposal_id = ''
selected_dirs = []
selected_files = []
dir_sizes = []
file_sizes = []
directory_history = []

# meta data values
meta_list = []

# proposals
proposal_list = []

# process that handles bundling and uploading
bundle_process = None


def current_directory(history):
    directory = ''
    for path in history:
        directory = os.path.join(directory, path)
        directory = directory + "/"

    return directory

def folder_size(folder):
    total_size = os.path.getsize(folder)
    for item in os.listdir(folder):
        itempath = os.path.join(folder, item)
        if os.path.isfile(itempath):
            total_size += os.path.getsize(itempath)
        elif os.path.isdir(itempath):
            total_size += folder_size(itempath)
            
    return total_size

def folder_meta(folder, meta):

    meta.dir_count += 1

    for item in os.listdir(folder):
        itempath = os.path.join(folder, item)
        if os.path.isfile(itempath):
            meta.totalBytes += os.path.getsize(itempath)
            meta.fileCount += 1
        elif os.path.isdir(itempath):
            folder_meta(itempath, meta)

def file_tuples_recursively(folder, tuple_list, root_dir):

    for item in os.listdir(folder):
        path = os.path.join(folder, item)
        if os.path.isfile(path):
            relative_path = path.replace(root_dir, '')
            tuple_list.append((path, relative_path))
        elif os.path.isdir(path):
            file_tuples_recursively(path, tuple_list, root_dir)

# bundler takes a list of tuples
def file_tuples(selected_list, tuple_list, root_dir):

    for path in selected_list:
        if os.path.isfile(path):
            # the relative path is the path without the root directory
            relative_path = path.replace(root_dir, '')
            tuple_list.append((path, relative_path))
        elif os.path.isdir(path):
            file_tuples_recursively(path, tuple_list, root_dir)

def upload_size_string(total_size):
    # less than a Kb show b
    if (total_size < 1024):
        return str(total_size) + " b"
    # less than an Mb show Kb
    if (total_size < 1048576):
        kilobytes = float(total_size) / 1024.0
        return str(round(kilobytes, 2)) + " Kb"
    # less than a Gb show Mb
    elif (total_size < 1073741824):
        megabytes = float(total_size) / 1048576.0
        return str(round(megabytes, 2)) + " Mb"
    # else show in Gb
    else:
        gigabytes = float(total_size) / 1073741824.0
        return str(round(gigabytes, 2)) + " Gb"

def upload_meta_string(folder):

    meta = FolderMeta()
    folder_meta(folder, meta)

    print '{0}|{1}'.format(str(meta.fileCount), str(meta.totalBytes))

    meta.dir_count -= 1
    meta_str = 'folders {0}|files {1}|{2}'.format(str(meta.dir_count),str(meta.fileCount),upload_size_string(meta.totalBytes))

    return meta_str

def file_size_string(filename):

    total_size = os.path.getsize(filename)

    return upload_size_string(total_size)

#@login_required(login_url='/login/')
def list(request):

    global user
    print user

    global password
    # first time through go to login page
    if (password == ""):
        return render_to_response('home/login.html', \
            {'message': ""}, context_instance=RequestContext(request))

    global selected_dirs
    global dir_sizes
    global selected_files
    global file_sizes
    global directory_history
    global meta_list
    global proposal_list
    global proposal_verbose
    global current_time

    root_dir = current_directory(directory_history)

    if root_dir == "": # first time through, initialize
        data_path = Filepath.objects.get(name="dataRoot")
        if (data_path is not None):
            root_dir = data_path.fullpath
        elif ("Linux" in platform.platform(aliased=0, terse=0)):
            root_dir = "/home"
        else:
            root_dir = "c:\\"

        if (root_dir.endswith("\\")):
            root_dir = root_dir[:-1]
        directory_history.append(root_dir)
        root_dir = current_directory(directory_history)

        # create a list of metadata entries to pass to the list upload page
        for meta in Metadata.objects.all():
            meta_entry = MetaData()
            meta_entry.label = meta.label
            meta_entry.name = meta.name
            meta_entry.value = ""
            meta_list.append(meta_entry)

    checked_dirs = []
    unchecked_dirs = []
    checked_files = []
    unchecked_files = []

    contents = os.listdir(root_dir)

    for path in contents:

        full_path = os.path.join(root_dir, path)

        if (os.path.isdir(full_path)):
            if (full_path in selected_dirs):
                checked_dirs.append(path)
            else:
                unchecked_dirs.append(path)
        else:
            if (full_path in selected_files):
                checked_files.append(path)
            else:
                unchecked_files.append(path)

    # Render list page with the documents and the form
    return render_to_response('home/uploader.html',
        {'instrument': instrument, 
         'proposalList': proposal_list,
         'proposal':proposal_verbose,  
         'directoryHistory': directory_history, 
         'metaList': meta_list,
         'checkedDirs': checked_dirs, 
         'uncheckedDirs': unchecked_dirs, 
         'checkedFiles': checked_files, 
         'uncheckedFiles': unchecked_files, 
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
    global meta_list
    global proposal_verbose
    global current_time
    global bundle_process
    global proposal_id

    root_dir = current_directory(directory_history)

    if request.POST:

        print request.POST

        if (request.POST.get("Clear")):
            selected_files = []
            selected_dirs = []

        for meta in meta_list:
            value = request.POST.get(meta.name)
            if (value):
                meta.value = value
                print meta.name + ": " + meta.value

        proposal_verbose = request.POST.get("proposal")  
        print "proposal:  " + proposal_verbose

        split = proposal_verbose.split()
        proposal_id = split[0]

        print proposal_id

        if (request.POST.get("Upload Files & Metadata")):

            print "uploading now"

            data_path = Filepath.objects.get(name="dataRoot")
            if (data_path is not None):
                root_dir = data_path.fullpath
            else:
                root_dir = ""

            # get the correct \/ orientation for the OS
            root = root_dir.replace("\\", "/")

            #create a list of tuples to meet the call format
            tuples = []
            file_tuples(selected_files, tuples, root)
            file_tuples(selected_dirs,tuples, root)
            print tuples

            # create the groups dictionary
            #{"groups":[{"name":"FOO1", "type":"Tag"}]}
            groups = {}
            for meta in meta_list:
                groups[meta.name] = meta.value

            current_time = datetime.datetime.now().time().strftime("%m.%d.%Y.%H.%M.%S")

            target_path = Filepath.objects.get(name="target")
            if (target_path is not None):
                target_dir = target_path.fullpath
            else:
                target_dir = root_dir

            bundle_name = os.path.join(target_dir, current_time + ".tar")

            server_path = Filepath.objects.get(name="server")
            if (server_path is not None):
                full_server_path = server_path.fullpath
            else:
                full_server_path = "dev1.my.emsl.pnl.gov"

            #return HttpResponseRedirect(reverse('home.views.list'))
            # spin this off as a background process and load the status page
            #task = tasks.sleeptask.delay(1, list)
            bundle_process = tasks.upload_files.delay(bundle_name = bundle_name,
                                                      instrument_name=instrument,
                                                      proposal=proposal_id,
                                                      file_list=tuples,
                                                      groups=groups,
                                                      server=full_server_path,
                                                      user=user,
                                                      password=password)

            return render_to_response('home/status.html',
                                      {'instrument': instrument,
                                      'status': 'Starting Upload',
                                      'proposal':proposal_verbose,
                                      'metaList': meta_list,
                                      'current_time': current_time,
                                      'user': user},
                                      context_instance=RequestContext(request))
    else:
        value_pair = urlparse(request.get_full_path())
        params = value_pair.query.split("=")
        mod_type = params[0]
        path = params[1]

        # spaces
        path = path.replace("%20", " ")
        # backslash
        path = path.replace("%5C", "\\")

        full = os.path.join(root_dir, path)

        if (mod_type == 'enterDir'):
            root_dir = os.path.join(root_dir, path)
            directory_history.append(path)

        elif (mod_type == 'toggleFile'):
            if (full not in selected_files):
                selected_files.append(full) 
                file_sizes.append(file_size_string(full))
            else:
                index = selected_files.index(full)
                selected_files.remove(full) 
                del file_sizes[index]
        elif (mod_type == 'toggleDir'):
            if (full not in selected_dirs):
                selected_dirs.append(full) 
                dir_sizes.append(upload_meta_string(full))
            else:
                index = selected_dirs.index(full)
                selected_dirs.remove(full) 
                del dir_sizes[index]
        elif (mod_type == "upDir"):
            index = int(path)
            del directory_history[index:]
            print current_directory(directory_history)

    return HttpResponseRedirect(reverse('home.views.list'))

def load_user_info():
    info = user_info(protocol="https",
                   server=sPath,
                   user=user,
                   insecure=True,
                   password=password,
                   negotiate = False,
                   verbose=True)
    print info
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
    global proposal_list
    global instrument

    user = password = ''

    print "logging in"

    if request.POST:
        print "Post"
        user = request.POST['username']
        password = request.POST['password']

        server_path = Filepath.objects.get(name="server")
        if (server_path is not None):
            full_server_path = server_path.fullpath
        else:
            full_server_path = "dev1.my.emsl.pnl.gov"

        authorized = test_authorization(protocol="https",
                                  server=full_server_path,
                                  user=user,
                                  insecure=True,
                                  password=password,
                                  negotiate = False,
                                  verbose=True)

        if (not authorized):
            password = ""     
            return render_to_response('home/login.html', {'message': "User or Password is incorrect"}, context_instance=RequestContext(request))

        print "password accepted"

        info = user_info(protocol="https",
                   server=full_server_path,
                   user=user,
                   insecure=True,
                   password=password,
                   negotiate = False,
                   verbose=True)

        json_parsed = 0
        try:
            info = json.loads(info)
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

            instrument_list = []
            valid_instrument = False
            for inst_id, inst_block in instruments.iteritems():
                inst_name = inst_block.get("instrument_name")
                inst_str = inst_id + "  " + inst_name
                instrument_list.append(inst_str)
                if (instrument == inst_id):
                    valid_instrument = True
                print inst_str
                print ""

            if (not valid_instrument):
                password = ""
                return render_to_response('home/login.html', {'message': "User is not valid for this instrument"}, context_instance=RequestContext(request))

            print "props"
            props = info["proposals"]
            proposal_list = []
            for prop_id, prop_block in props.iteritems():
                title = prop_block.get("title")
                prop_str = prop_id + "  " + title
                proposal_list.append(prop_str)
                print prop_str

                #for later
                instruments = prop_block.get("instruments")
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
    global meta_list
    global proposal_verbose
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
                 'proposal':proposal_verbose,
                 'metaList': meta_list,
                 'current_time': current_time,
                 'user': user},
                context_instance=RequestContext(request))


def incremental_status(request):

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
