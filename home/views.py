#pylint: disable=no-member
# justification:  dynamic methods

#pylint: disable=invalid-name
# justification: module level variables

"""
Django views, handle requests from the client side pages
"""

from __future__ import absolute_import

from django.conf import settings

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse


import json

import datetime

from urlparse import urlparse

#operating system and platform
import os
import platform
import stat

#celery heartbeat
import psutil
from subprocess import call

#uploader
from uploader import test_authorization
from uploader import job_status

#database imports
from home.models import Filepath
from home.models import Metadata

#session imports
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib import auth
from django.contrib.auth.decorators import login_required

# celery tasks
from home import tasks
from home import tar_man

# delay for celery heartbeat
from time import sleep

# for restarting Celery
import subprocess

from home import session_data

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

# Module level variables
session = session_data.session_state()

def login_user_locally(request):
    """
    if we have a new user, let's create a new Django user and log them
    in with a bogus password, "shrubbery".  Actual authentication will be done
    before this function is called.
    """
    username = request.POST['username']
    password = 'shrubbery'

    # does this user exist?
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = None

    if user is None:
        #create a new user
        user = User.objects.create_user(username=username, password=password)
        user.save()

    # we have a local user that matches the already validated EUS user
    # authenticate and log them in locally
    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            auth.login(request, user)


def ping_celery():
    """
    check to see if the celery process to bundle and upload is alive, alive!
    """
    ping_process = tasks.ping.delay();

    tries = 0
    while tries < 5:
        state = ping_process.status
        if state is not None:
            print state
            if state == "PING" or state == "SUCCESS":
                return True
        sleep (1)
        tries += 1

    return False

def start_celery():
    """
    starts the celery process
    """

    alive = ping_celery()
    if not alive:
        try:
            print 'attempting to start Celery'
            subprocess.Popen('celery -A UploadServer worker --loglevel=info', shell=True )
        except Exception, e:
            print e

    count = 0
    alive = False
    while not alive and count < 10:
        sleep(1)
        alive = celery_lives()
        count = count + 1

    return alive

#remove
#def current_directory(history):
#    """
#    builds the current directory based on the navigation history
#    """
#    directory = ''
#    for path in history:
#        directory = os.path.join(directory, path)

#    return directory

#remove
#def undo_directory(session):
#    index = len(session.files.directory_history) - 1
#    del session.files.directory_history[index:]

#remove
#def bundle_size(files, folders):
#    """
#    totals up total size of the files in the bundle
#    """
#    total_size = 0

#    for file_path in files:
#        total_size += os.path.getsize(file_path)

#    for folder in folders:
#        total_size += folder_size(folder)

#    return total_size

#def folder_size(folder):
#    """
#    recursively totals up total size of the files in the folder and sub folders
#    """

#    total_size = os.path.getsize(folder)
#    for item in os.listdir(folder):
#        itempath = os.path.join(folder, item)
#        if os.path.isfile(itempath):
#            total_size += os.path.getsize(itempath)
#        elif os.path.isdir(itempath):
#            total_size += folder_size(itempath)

#    return total_size

#def folder_meta(folder, meta):
#    """
#    gets the meta data for a folder
#    number of folders
#    number of files
#    total size
#    """

#    meta.dir_count += 1

#    for item in os.listdir(folder):
#        itempath = os.path.join(folder, item)
#        if os.path.isfile(itempath):
#            meta.totalBytes += os.path.getsize(itempath)
#            meta.fileCount += 1
#        elif os.path.isdir(itempath):
#            folder_meta(itempath, meta)

#def file_tuples_recursively(folder, tuple_list, root_dir):
#    """
#    recursively gets file tuples for a folder
#    """

#    #if we don't have access to this folder, bail
#    if not os.access(folder, os.R_OK & os.X_OK):
#        return

#    for item in os.listdir(folder):
#        path = os.path.join(folder, item)
#        if os.path.isfile(path):
#            if os.access(path, os.R_OK):
#                relative_path = os.path.relpath(path, root_dir)
#                tuple_list.append((path, relative_path))
#        elif os.path.isdir(path):
#            file_tuples_recursively(path, tuple_list, root_dir)

#def file_tuples(selected_list, tuple_list, root_dir):
#    """
#    gets all the file tuples for a list of either folders or files
#    tuples consist of the absolute path where the local file can be found
#    and the relative path used to store the file in the archive
#    """
#    for path in selected_list:
#        if os.path.isfile(path):
#            if os.access(path, os.R_OK):
#                # the relative path is the path without the root directory
#                relative_path = os.path.relpath(path, root_dir)
#                tuple_list.append((path, relative_path))
#        elif os.path.isdir(path):
#            file_tuples_recursively(path, tuple_list, root_dir)

#def size_string(total_size):
#    """
#    returns the upload size as a string with the appropriate units
#    """

#    # less than a Kb show b
#    if total_size < 1024:
#        return str(total_size) + " b"
#    # less than an Mb show Kb
#    if total_size < 1048576:
#        kilobytes = float(total_size) / 1024.0
#        return str(round(kilobytes, 2)) + " Kb"
#    # less than a Gb show Mb
#    elif total_size < 1073741824:
#        megabytes = float(total_size) / 1048576.0
#        return str(round(megabytes, 2)) + " Mb"
#    # else show in Gb
#    else:
#        gigabytes = float(total_size) / 1073741824.0
#        return str(round(gigabytes, 2)) + " Gb"

def upload_meta_string(folder):
    """
    returns the meta data for a folder as a string to be displayed to the user
    """
    meta = FolderMeta()
    session.files.folder_meta(folder, meta)

    print '{0}|{1}'.format(str(meta.fileCount), str(meta.totalBytes))

    meta.dir_count -= 1
    meta_str = 'folders {0} | files {1} | {2}'.\
        format(str(meta.dir_count), str(meta.fileCount), session.files.size_string(meta.totalBytes))

    return meta_str

#def file_size_string(filename):
#    """
#    returns a string with the file size in appropriate units
#    """

#    total_size = os.path.getsize(filename)

#    return size_string(total_size)


@login_required(login_url=settings.LOGIN_URL)
def populate_upload_page(request):
    """
    formats the main uploader page
    """
    global session

    # if not logged in
    if session.password == '':
        # call login error with no error message
        b = request.user.is_authenticated()
        return login_error(request, '')

    root_dir = session.files.current_directory()

    if root_dir == '': # first time through, initialize
        data_path = Filepath.objects.get(name="dataRoot")
        if data_path is not None:
            root_dir = data_path.fullpath
            root_dir = os.path.normpath(root_dir)
        else:
            return "error no root directory"


        if root_dir.endswith("\\"):
            root_dir = root_dir[:-1]
        session.files.directory_history.append(root_dir)
        root_dir = session.files.current_directory()

        # create a list of metadata entries to pass to the list upload page
        for meta in Metadata.objects.all():
            meta_entry = MetaData()
            meta_entry.label = meta.label
            meta_entry.name = meta.name
            meta_entry.value = ""
            session.meta_list.append(meta_entry)

    checked_dirs = []
    unchecked_dirs = []
    checked_files = []
    unchecked_files = []

    try:
        contents = os.listdir(root_dir)
    except Exception:
        session.files.undo_directory()
        return HttpResponseRedirect(reverse('home.views.populate_upload_page'))
    

    for path in contents:
        full_path = os.path.join(root_dir, path)

        if os.path.isdir(full_path):
            if full_path in session.files.selected_dirs:
                checked_dirs.append(path)
            else:
                unchecked_dirs.append(path)
        else:
            if full_path in session.files.selected_files:
                checked_files.append(path)
            else:
                unchecked_files.append(path)

    # validate that the currently selected bundle will fit in the target space
    uploadEnabled = validate_space_available(session)
    message = 'Bundle: %s, Free: %s' % (session.bundle_size_str, session.free_size_str)
    if not uploadEnabled:
        message += ": Bundle exceeds free space"
    elif session.bundle_size==0:
        uploadEnabled = False

    # Render list page with the documents and the form
    return render_to_response('home/uploader.html', \
        {'instrument': session.concatenated_instrument(),
         'proposalList': session.proposal_list,
         'user_list': session.proposal_users,
         'proposal':session.proposal_friendly,
         'directoryHistory': session.files.directory_history,
         'metaList': session.meta_list,
         'checkedDirs': checked_dirs,
         'uncheckedDirs': unchecked_dirs,
         'checkedFiles': checked_files,
         'uncheckedFiles': unchecked_files,
         'selectedDirs': session.files.selected_dirs,
         'dirSizes': session.files.dir_sizes,
         'selectedFiles': session.files.selected_files,
         'fileSizes': session.files.file_sizes,
         'current_time': session.current_time,
         'message': message,
         'uploadEnabled': uploadEnabled,
         'user': session.user_full_name
        },
                              context_instance=RequestContext(request))

def show_status(request, session, message):

    bundle_size_str = session.files.size_string(session.bundle_size)
    free_size_str = session.files.size_string(session.free_space)

    return render_to_response('home/status.html', \
                                 {'instrument':session.concatenated_instrument(),
                                  'status': message,
                                  'proposal':session.proposal_friendly,
                                  'metaList':session. meta_list,
                                  'current_time': session.current_time,
                                  'bundle_size': bundle_size_str,
                                  'free_size': free_size_str,
                                  'user': session.user_full_name},
                                  context_instance=RequestContext(request))


def validate_space_available(session):

    target_path = Filepath.objects.get(name="target")
    if target_path is not None:
        target_dir = target_path.fullpath
    else:
        target_dir = root_dir

    session.bundle_size = session.files.bundle_size()

    # get the disk usage
    space = psutil.disk_usage(target_dir)

    #give ourselves a cushion for other processes
    session.free_space = int(.9 * space.free)

    session.bundle_size_str = session.files.size_string(session.bundle_size)
    session.free_size_str = session.files.size_string(session.free_space)

    if (session.bundle_size == 0):
        return True
    return (session.bundle_size <  session.free_space)

def spin_off_upload(request, session):
    """
    spins the upload process off to a background celery process
    """
    # check to see if background celery process is alive
    # if not, start it.  Wait 5 seconds, if it doesn't start,
    # we're boned.
    alive = ping_celery()
    print 'Celery lives = %s' % (alive)
    if not alive:
        return show_status(request, session, 'Celery background process is not started')


    root_dir = session.files.current_directory()

    # get the meta data values from the post
    for meta in session. meta_list:
        value = request.POST.get(meta.name)
        if value:
            meta.value = value

    # get the selected proposal string from the post
    session.load_request_proposal(request)

    # get the root directory from the database
    data_path = Filepath.objects.get(name="dataRoot")
    if data_path is not None:
        root_dir = data_path.fullpath
    else:
        # handle error here
        root_dir = ""

    root = root_dir

    #create a list of tuples (filepath, arcpath)
    tuples = []
    session.files.file_tuples(session.files.selected_files, tuples, root)
    session.files.file_tuples(session.files.selected_dirs, tuples, root)

    # create the groups dictionary
    #{"groups":[{"name":"FOO1", "type":"Tag"}]}
    groups = {}
    for meta in session.meta_list:
        groups[meta.name] = meta.value

    insty = 'Instrument.%s' % (session.instrument)
    groups[insty] = session.instrument_friendly

    session.current_time = datetime.datetime.now().strftime("%m.%d.%Y.%H.%M.%S")

    target_path = Filepath.objects.get(name="target")
    if target_path is not None:
        target_dir = target_path.fullpath
    else:
        target_dir = root_dir

    session.bundle_filepath = os.path.join(target_dir, session.current_time + ".tar")

    # spin this off as a background process and load the status page
    if True:
        session.bundle_process = \
                tasks.upload_files.delay(bundle_name=session.bundle_filepath,
                                         instrument_name=session.instrument,
                                         proposal=session.proposal_id,
                                         file_list=tuples,
                                         bundle_size=session.bundle_size,
                                         groups=groups,
                                         server=session.server_path,
                                         user=session.user,
                                         password=session.password)
    else: # for debug purposes
        tasks.upload_files(bundle_name=session.bundle_filepath,
                                         instrument_name=session.instrument,
                                         proposal=session.proposal_id,
                                         file_list=tuples,
                                         bundle_size=session.bundle_size,
                                         groups=groups,
                                         server=session.server_path,
                                         user=session.user,
                                         password=session.password)

    return show_status(request, session, 'Starting Upload')

def modify(request):
    """
    modifies the data underlying the main upload page depending on the request
    the main request catagories are:
        file sytem navigation
        selected list management
        upload request
    """

    # print 'modify ' + request.get_full_path()

    global session

    root_dir = session.files.current_directory()

    if request.POST:

        print request.POST

        if request.POST.get("Clear"):
            session.clear_upload_lists()

        if request.POST.get("Upload Files & Metadata"):
            return spin_off_upload(request, session)

        if request.POST.get("Submit Proposal"):
            session.load_request_proposal(request)
            session.populate_proposal_users()

        if request.POST.get("proposal"):
            session.load_request_proposal(request)
            session.populate_proposal_users()

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
            # check to see if we have read permissions to this directory
            if (os.access(root_dir, os.R_OK & os.X_OK)):
                session.files.directory_history.append(path)

        elif mod_type == 'toggleFile':
            if full not in session.files.selected_files:
                session.files.selected_files.append(full)
                session.files.file_sizes.append(session.files.file_size_string(full))
            else:
                index = session.files.selected_files.index(full)
                session.files.selected_files.remove(full)
                session.files.file_sizes[index]

        elif mod_type == 'toggleDir':
            if full not in session.files.selected_dirs:
                if (os.access(root_dir, os.R_OK & os.X_OK)):
                    # test to see if we can get access
                    try:
                        files = os.listdir(full)
                        session.files.selected_dirs.append(full)
                        session.files.dir_sizes.append(upload_meta_string(full))
                    except Exception:
                        return HttpResponseRedirect(reverse('home.views.populate_upload_page'))
            else:
                index = session.files.selected_dirs.index(full)
                session.files.selected_dirs.remove(full)
                del session.files.dir_sizes[index]

        elif mod_type == "upDir":
            index = int(path)
            del session.files.directory_history[index:]

    return HttpResponseRedirect(reverse('home.views.populate_upload_page'))

"""
login and login related accesories
"""
#########################################################################################
def login_error(request, error_string):
    """
    returns to the login page with an error message
    """
    return render_to_response(settings.LOGIN_VIEW, \
                              {'message': error_string}, context_instance=RequestContext(request))

#def populate_user_info(session, info):
#    """
#    parses user information from a json struct
#    """
#    try:
#        info = json.loads(info)
#    except Exception:
#        return 'Unable to parse user information'

#    # print json.dumps(info, sort_keys=True, indent=4, separators=(',', ': '))

#    first_name = info["first_name"]
#    if not first_name:
#        return 'Unable to parse user name'
#    last_name = info["last_name"]
#    if not last_name:
#        return 'Unable to parse user name'

#    session.user_full_name = '%s (%s %s)' % (session.user, first_name, last_name)

#    instruments = info["instruments"]

#    try:
#        valid_instrument = False
#        for inst_id, inst_block in instruments.iteritems():
#            inst_name = inst_block.get("instrument_name")
#            inst_str = inst_id + "  " + inst_name
#            if session.instrument == inst_id:
#                session.instrument_friendly = inst_name
#                valid_instrument = True

#            #print inst_str
#            #print ""

#        if not valid_instrument:
#            return 'User is not valid for this instrument'
#    except Exception:
#        return 'Unable to parse user instruments'

#    """
#    need to filter proposals based on the existing instrument 
#    if there is no valid proposal for the user for this instrument
#    throw an error
#    """
#    #print "props"
#    props = info["proposals"]
#    session.proposal_list = []
#    for prop_id, prop_block in props.iteritems():
#        title = prop_block.get("title")
#        prop_str = prop_id + "  " + title

#        # list only proposals valid for this instrument
#        instruments = prop_block.get("instruments")

#        try:
#            if instruments is not None and len(instruments) > 0:
#                for inst_id in instruments: # eh.  inst_id is a list of 1 element.
#                    if session.instrument == str(inst_id):
#                        if prop_str not in session.proposal_list:
#                            session.proposal_list.append(prop_str)
#        except Exception, err:
#            return 'No valid proposals for this user on this instrument'

#    if len(session.proposal_list) == 0:
#        return 'No valid proposals for this user on this instrument'

#    session.proposal_list.sort(key=lambda x: int(x.split(' ')[0]), reverse=True)

#    # no errors found
#    return ''

def cookie_test(request):
    """
    This test needs to be called twice in a row.  The first call should fail as the
    cookie hasn't been set.  The second should succeed.  If it doesn't,
    you need to enable cookies on the browser.
    """
    # test that the browser is supporting cookies so we can maintain our session state
    if request.session.test_cookie_worked():
        request.session.delete_test_cookie()
        return render_to_response('home/cookie.html', {'message': 'Cookie Success'}, \
                                  context_instance=RequestContext(request))
    else:
        request.session.set_test_cookie()
        return render_to_response('home/cookie.html', {'message': 'Cookie Failure'}, \
            context_instance=RequestContext(request))

def login(request):
    """
    Logs the user in
    If the login fails for whatever reason, authentication, invalid for instrument, etc.,
    returns to login page with error.
    Otherwise, gets the user data to populate the main page
    """

    global session

    # timeout
    try:
        timeout = Filepath.objects.get(name="timeout")
        minutes = int(timeout.fullpath)
        SESSION_COOKIE_AGE = minutes * 60
    except Filepath.DoesNotExist:
        SESSION_COOKIE_AGE = 30 * 60

    # ignore GET
    if not request.POST:
        return login_error(request, '')

    """
    # check to see if there is an existing user logged in
    if (session.current_user):
        # if the current user is still logged in, throw an error
        if (session.current_user.is_authenticated()):
            return login_error(request, 'User %s is currently logged in' % session.user_full_name)
    # if this was the last user logged in, maintain the session state
    if (request.user is not session.current_user):
        cleanup_session(session)
    """

    session.cleanup_session()

    #even if this is the current user, we still need to re-authenticate them
    session.user = request.POST['username']
    session.password = request.POST['password']

    server_path = Filepath.objects.get(name="server")
    if server_path is not None:
        session.server_path = server_path.fullpath
    else:
        return login_error(request, 'Server path does not exist')

    
    # test to see if the user authorizes against EUS
    authorized = test_authorization(protocol="https",
                                    server=session.server_path,
                                    user=session.user,
                                    password=session.password)

    if not authorized:
        return login_error(request, 'User or Password is incorrect')

    inst = Filepath.objects.get(name="instrument")
    if inst and inst is not '':
        session.instrument = inst.fullpath
    else:
        return login_error(request, 'This instrument is undefined')

    err_str = session.populate_user_info()
    if err_str is not '':
        return login_error(request, err_str)

    # if the user passes EUS authentication then log them in locally for our session
    login_user_locally(request)

    # did that work?
    if not request.user.is_authenticated():
        return login_error(request, 'Problem with local authentication')

    # ok, passed all EUS and local authorization tests, valid user data is loaded
    # keep a copy of the user so we can keep other users from stepping on them if they are still
    # logged in
    session.current_user = request.user

    return HttpResponseRedirect(reverse('home.views.populate_upload_page'))

def logout(request):
    """
    logs the user out and returns to the main page
    which will bounce to the login page
    """

    # pass pylint
    request = request

    global session

    #logs out local user session
    # if the LOGOUT_URL is set to this view, we create a recursive call to here
    #logout(request)

    return HttpResponseRedirect(reverse('home.views.login'))

def incremental_status(request):
    """
    updates the status page with the current status of the background upload process
    """
    # pass pylint
    request = request

    global session

    if request.POST:
        if request.POST.get("Cancel Upload"):
            session.bundle_process.revoke(terminate=True)
            session.cleanup_upload()
            return HttpResponseRedirect(reverse('home.views.populate_upload_page'))

    state = session.bundle_process.status
    if state is None:
        state = "UNKNOWN"
    print state

    result = session.bundle_process.result
    if result is None:
        result = "UNKNOWN"
    print result

    if result is not None:
        if "http" in result:
            state = 'DONE'
            result = result.strip('"')
            job_id =  result
            tm = tar_man.tar_management()
            job_id = tm.parse_job(result)

            if (job_id is not ''):
                tm.add_tar(session.bundle_filepath, job_id)

            #if we have successfully uploaded, cleanup the lists
            session.cleanup_upload()

    # create json structure
    retval = json.dumps({'state':state, 'result':result})

    return HttpResponse(retval)
