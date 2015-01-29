#pylint: disable=no-member

"""
Django views, handle requests from the client side pages
"""

from __future__ import absolute_import

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse

import json

import datetime

from urlparse import urlparse

import os
import platform

from uploader import test_authorization
from uploader import user_info

from home.models import Filepath
from home.models import Metadata

from home import tasks

class MetaData(object):
    """
    structure used to pass upload metadata back and forth to the upload page
    """

    label = ''
    value = ''
    name = ''

    def __init__(self):
        pass

class FolderMeta(object):
    """
    meta data about a folder, including filecount, directory count, and the total bytes.
    """

    fileCount = 0
    dir_count = 0
    totalBytes = 0

    def __init__(self):
        pass

class SessionData(object):
    """
    meta data about a folder, including filecount, directory count, and the total bytes.
    """

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


# Module level variables
session_data = SessionData()

def current_directory(history):
    """
    builds the current directory based on the navigation history
    """

    directory = ''
    for path in history:
        directory = os.path.join(directory, path)
        directory = directory + "/"

    return directory

def folder_size(folder):
    """
    recursively totals up total size of the files in the folder and sub folders
    """

    total_size = os.path.getsize(folder)
    for item in os.listdir(folder):
        itempath = os.path.join(folder, item)
        if os.path.isfile(itempath):
            total_size += os.path.getsize(itempath)
        elif os.path.isdir(itempath):
            total_size += folder_size(itempath)

    return total_size

def folder_meta(folder, meta):
    """
    gets the meta data for a folder
    number of folders
    number of files
    total size
    """

    meta.dir_count += 1

    for item in os.listdir(folder):
        itempath = os.path.join(folder, item)
        if os.path.isfile(itempath):
            meta.totalBytes += os.path.getsize(itempath)
            meta.fileCount += 1
        elif os.path.isdir(itempath):
            folder_meta(itempath, meta)

def file_tuples_recursively(folder, tuple_list, root_dir):
    """
    recursively gets file tuples for a folder
    """

    for item in os.listdir(folder):
        path = os.path.join(folder, item)
        if os.path.isfile(path):
            relative_path = path.replace(root_dir, '')
            tuple_list.append((path, relative_path))
        elif os.path.isdir(path):
            file_tuples_recursively(path, tuple_list, root_dir)

def file_tuples(selected_list, tuple_list, root_dir):
    """
    gets all the file tuples for a list of either folders or files
    tuples consist of the absolute path where the local file can be found
    and the relative path used to store the file in the archive
    """
    for path in selected_list:
        if os.path.isfile(path):
            # the relative path is the path without the root directory
            relative_path = path.replace(root_dir, '')
            tuple_list.append((path, relative_path))
        elif os.path.isdir(path):
            file_tuples_recursively(path, tuple_list, root_dir)

def upload_size_string(total_size):
    """
    returns the upload size as a string with the appropriate units
    """

    # less than a Kb show b
    if total_size < 1024:
        return str(total_size) + " b"
    # less than an Mb show Kb
    if total_size < 1048576:
        kilobytes = float(total_size) / 1024.0
        return str(round(kilobytes, 2)) + " Kb"
    # less than a Gb show Mb
    elif total_size < 1073741824:
        megabytes = float(total_size) / 1048576.0
        return str(round(megabytes, 2)) + " Mb"
    # else show in Gb
    else:
        gigabytes = float(total_size) / 1073741824.0
        return str(round(gigabytes, 2)) + " Gb"

def upload_meta_string(folder):
    """
    returns the meta data for a folder as a string to be displayed to the user
    """
    meta = FolderMeta()
    folder_meta(folder, meta)

    print '{0}|{1}'.format(str(meta.fileCount), str(meta.totalBytes))

    meta.dir_count -= 1
    meta_str = 'folders {0} | files {1} | {2}'.\
        format(str(meta.dir_count), str(meta.fileCount), upload_size_string(meta.totalBytes))

    return meta_str

def file_size_string(filename):
    """
    returns a string with the file size in appropriate units
    """

    total_size = os.path.getsize(filename)

    return upload_size_string(total_size)

#@login_required(login_url='/login/')
def populate_upload_page(request):
    """
    formats the main uploader page
    """

    global session_data

    # first time through go to login page
    if session_data.password == '':
        return render_to_response('home/login.html', \
            {'message': ""}, context_instance=RequestContext(request))

    root_dir = current_directory(session_data.directory_history)

    if root_dir == "": # first time through, initialize
        data_path = Filepath.objects.get(name="dataRoot")
        if data_path is not None:
            root_dir = data_path.fullpath
        elif "Linux" in platform.platform(aliased=0, terse=0):
            root_dir = "/home"
        else:
            root_dir = "c:\\"

        if root_dir.endswith("\\"):
            root_dir = root_dir[:-1]
        session_data.directory_history.append(root_dir)
        root_dir = current_directory(session_data.directory_history)

        # create a list of metadata entries to pass to the list upload page
        for meta in Metadata.objects.all():
            meta_entry = MetaData()
            meta_entry.label = meta.label
            meta_entry.name = meta.name
            meta_entry.value = ""
            session_data.meta_list.append(meta_entry)

    checked_dirs = []
    unchecked_dirs = []
    checked_files = []
    unchecked_files = []

    contents = os.listdir(root_dir)

    for path in contents:
        full_path = os.path.join(root_dir, path)

        if os.path.isdir(full_path):
            if full_path in session_data.selected_dirs:
                checked_dirs.append(path)
            else:
                unchecked_dirs.append(path)
        else:
            if full_path in session_data.selected_files:
                checked_files.append(path)
            else:
                unchecked_files.append(path)

    # Render list page with the documents and the form
    return render_to_response('home/uploader.html', \
        {'instrument': session_data.instrument,
         'proposalList': session_data.proposal_list,
         'proposal':session_data.proposal_verbose,
         'directoryHistory': session_data.directory_history,
         'metaList': session_data.meta_list,
         'checkedDirs': checked_dirs,
         'uncheckedDirs': unchecked_dirs,
         'checkedFiles': checked_files,
         'uncheckedFiles': unchecked_files,
         'selectedDirs': session_data.selected_dirs,
         'dirSizes': session_data.dir_sizes,
         'selectedFiles': session_data.selected_files,
         'fileSizes': session_data.file_sizes,
         'current_time': session_data.current_time,
         'user': session_data.user
        },
                              context_instance=RequestContext(request))


def modify(request):
    """
    modifies the data underlying the main upload page depending on the request
    the main request catagories are:
        file sytem navigation
        selected list management
        upload request
    """

    print 'modify ' + request.get_full_path()

    global session_data

    root_dir = current_directory(session_data.directory_history)

    if request.POST:

        print request.POST

        if request.POST.get("Clear"):
            session_data.selected_files = []
            session_data.selected_dirs = []

        for meta in session_data. meta_list:
            value = request.POST.get(meta.name)
            if value:
                meta.value = value
                print meta.name + ": " + meta.value

        session_data.proposal_verbose = request.POST.get("proposal")
        print "proposal:  " + session_data.proposal_verbose

        split = session_data.proposal_verbose.split()
        session_data.proposal_id = split[0]

        print session_data.proposal_id

        if request.POST.get("Upload Files & Metadata"):

            print "uploading now"

            data_path = Filepath.objects.get(name="dataRoot")
            if data_path is not None:
                root_dir = data_path.fullpath
            else:
                root_dir = ""

            # get the correct \/ orientation for the OS
            root = root_dir.replace("\\", "/")

            #create a list of tuples to meet the call format
            tuples = []
            file_tuples(session_data.selected_files, tuples, root)
            file_tuples(session_data.selected_dirs, tuples, root)
            print tuples

            # create the groups dictionary
            #{"groups":[{"name":"FOO1", "type":"Tag"}]}
            groups = {}
            for meta in session_data.meta_list:
                groups[meta.name] = meta.value

            session_data.current_time = datetime.datetime.now().time().strftime("%m.%d.%Y.%H.%M.%S")

            target_path = Filepath.objects.get(name="target")
            if target_path is not None:
                target_dir = target_path.fullpath
            else:
                target_dir = root_dir

            bundle_name = os.path.join(target_dir, session_data.current_time + ".tar")

            server_path = Filepath.objects.get(name="server")
            if server_path is not None:
                full_server_path = server_path.fullpath
            else:
                full_server_path = "dev1.my.emsl.pnl.gov"

            # spin this off as a background process and load the status page
            session_data.bundle_process = \
                tasks.upload_files.delay(bundle_name=bundle_name,
                                         instrument_name=session_data.instrument,
                                         proposal=session_data.proposal_id,
                                         file_list=tuples,
                                         groups=groups,
                                         server=full_server_path,
                                         user=session_data.user,
                                         password=session_data.password)

            return render_to_response('home/status.html', \
                {'instrument': session_data.instrument,
                 'status': 'Starting Upload',
                 'proposal':session_data.proposal_verbose,
                 'metaList':session_data. meta_list,
                 'current_time': session_data.current_time,
                 'user': session_data.user},
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

        if mod_type == 'enterDir':
            root_dir = os.path.join(root_dir, path)
            session_data.directory_history.append(path)

        elif mod_type == 'toggleFile':
            if full not in session_data.selected_files:
                session_data.selected_files.append(full)
                session_data.file_sizes.append(file_size_string(full))
            else:
                index = session_data.selected_files.index(full)
                session_data.selected_files.remove(full)
                del session_data.file_sizes[index]

        elif mod_type == 'toggleDir':
            if full not in session_data.selected_dirs:
                session_data.selected_dirs.append(full)
                session_data.dir_sizes.append(upload_meta_string(full))
            else:
                index = session_data.selected_dirs.index(full)
                session_data.selected_dirs.remove(full)
                del session_data.dir_sizes[index]

        elif mod_type == "upDir":
            index = int(path)
            del session_data.directory_history[index:]
            print current_directory(session_data.directory_history)

    return HttpResponseRedirect(reverse('home.views.populate_upload_page'))

def login(request):
    """
    Logs the user in
    If the login fails for whatever reason, authentication, invalid for instrument, etc.,
    returns to login page with error.
    Otherwise, gets the user data to populate the main page
    """

    global session_data

    session_data.user = session_data.password = ''

    if request.POST:
        print "Post"
        session_data.user = request.POST['username']
        session_data.password = request.POST['password']

        server_path = Filepath.objects.get(name="server")
        if server_path is not None:
            full_server_path = server_path.fullpath
        else:
            full_server_path = "dev1.my.emsl.pnl.gov"

        authorized = test_authorization(protocol="https",
                                        server=full_server_path,
                                        user=session_data.user,
                                        insecure=True,
                                        password=session_data.password,
                                        negotiate=False,
                                        verbose=True)

        if not authorized:
            session_data.password = ""
            return render_to_response('home/login.html', \
                {'message': "User or Password is incorrect"}, \
                context_instance=RequestContext(request))

        print "password accepted"

        info = user_info(protocol="https",
                         server=full_server_path,
                         user=session_data.user,
                         insecure=True,
                         password=session_data.password,
                         negotiate=False,
                         verbose=True)

        json_parsed = 0
        try:
            info = json.loads(info)
            json_parsed = 1
        except Exception:
            print "json failure"
        if json_parsed:
            print json.dumps(info, sort_keys=True, indent=4, separators=(',', ': '))

            obj = Filepath.objects.get(name="instrument")
            if obj:
                session_data.instrument = obj.fullpath
            else:
                session_data.instrument = "unknown"

            print "instrument:  " + session_data.instrument

            print "instruments"
            instruments = info["instruments"]

            instrument_list = []
            valid_instrument = False
            for inst_id, inst_block in instruments.iteritems():
                inst_name = inst_block.get("instrument_name")
                inst_str = inst_id + "  " + inst_name
                instrument_list.append(inst_str)
                if session_data.instrument == inst_id:
                    valid_instrument = True
                print inst_str
                print ""

            if not valid_instrument:
                session_data.password = ""
                return render_to_response('home/login.html', \
                    {'message': "User is not valid for this instrument"}, \
                    context_instance=RequestContext(request))

            print "props"
            props = info["proposals"]
            session_data.proposal_list = []
            for prop_id, prop_block in props.iteritems():
                title = prop_block.get("title")
                prop_str = prop_id + "  " + title
                session_data.proposal_list.append(prop_str)
                print prop_str

                #for later
                instruments = prop_block.get("instruments")
                for i in instruments:
                    for j in i:
                        print j
                print ""

        return HttpResponseRedirect(reverse('home.views.populate_upload_page'))
    else:
        print "no Post"
        return render_to_response('home/login.html', context_instance=RequestContext(request))

def logout(request):
    """
    logs the user out and returns to the main page
    which will bounce to the login page
    """
    global session_data

    session_data.user = session_data.password = ''

    return HttpResponseRedirect(reverse('home.views.populate_upload_page'))

def incremental_status(request):
    """
    updates the status page with the current status of the background upload process
    """

    global session_data

    output = session_data.bundle_process.status
    state = output
    print state

    output = session_data.bundle_process.result
    result = output
    print result

    if result is not None:
        if "http" in result:
            state = 'DONE'
            result = result.strip('"')

    # create json structure
    retval = json.dumps({'state':state, 'result':result})

    return HttpResponse(retval)
