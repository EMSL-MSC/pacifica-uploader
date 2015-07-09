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


    ## if we enter an empty directory, reverse back up the history
    try:
        contents = os.listdir(root_dir)
    except Exception:
        session.files.undo_directory()
        return HttpResponseRedirect(reverse('home.views.populate_upload_page'))
    
    # get the display values for the current directory
    checked_dirs, unchecked_dirs, checked_files, unchecked_files = session.files.get_display_values()

    # validate that the currently selected bundle will fit in the target space
    uploadEnabled = session.validate_space_available(session.configuration["target"])

    message = 'Bundle: %s, Free: %s' % (session.files.bundle_size_str, session.free_size_str)
    if not uploadEnabled:
        message += ": Bundle exceeds free space"
    elif session.files.bundle_size==0:
        uploadEnabled = False

    # Render list page with the documents and the form
    return render_to_response('home/uploader.html', \
        {'instrument': session.concatenated_instrument(),
         'proposalList': session.proposal_list,
         'user_list': session.proposal_users,
         'proposal':session.proposal_friendly,
         'proposal_user':session.proposal_user,
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

    session.files.calculate_bundle_size()
    free_size_str = session.files.size_string(session.free_space)

    return render_to_response('home/status.html', \
                                 {'instrument':session.concatenated_instrument(),
                                  'status': message,
                                  'proposal':session.proposal_friendly,
                                  'metaList':session. meta_list,
                                  'current_time': session.current_time,
                                  'bundle_size': session.files.bundle_size_str,
                                  'free_size': free_size_str,
                                  'user': session.user_full_name},
                                  context_instance=RequestContext(request))

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

    # get the selected proposal string from the post as it may not have been set in a previous post
    session.load_request_proposal(request)
    session.load_request_proposal_user(request)

    tuples = session.files.get_bundle_files()

    # create the groups dictionary
    #{"groups":[{"name":"FOO1", "type":"Tag"}]}
    groups = {}
    for meta in session.meta_list:
        groups[meta.name] = meta.value

    insty = 'Instrument.%s' % (session.instrument)
    groups[insty] = session.instrument_friendly

    groups["EMSL User"] = session.proposal_user

    session.current_time = datetime.datetime.now().strftime("%m.%d.%Y.%H.%M.%S")

    target_path = session.configuration["target"]
    if target_path is None:
        login_error(request, "Missing upload target path")

    session.bundle_filepath = os.path.join(target_path, session.current_time + ".tar")

    # spin this off as a background process and load the status page
    if True:
        session.bundle_process = \
                tasks.upload_files.delay(bundle_name=session.bundle_filepath,
                                         instrument_name=session.instrument,
                                         proposal=session.proposal_id,
                                         file_list=tuples,
                                         bundle_size=session.files.bundle_size,
                                         groups=groups,
                                         server=session.server_path,
                                         user=session.user,
                                         password=session.password)
    else: # for debug purposes
        tasks.upload_files(bundle_name=session.bundle_filepath,
                                         instrument_name=session.instrument,
                                         proposal=session.proposal_id,
                                         file_list=tuples,
                                         bundle_size=session.files.bundle_size,
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

        if request.POST.get("proposal"):
            session.load_request_proposal(request)
            session.populate_proposal_users()

        if request.POST.get("proposal_user"):
            session.load_request_proposal_user(request)

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
            session.files.toggle_file(full)

        elif mod_type == 'toggleDir':
            session.files.toggle_dir(full)

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

def initialize_settings():
    """
    if the system hasn't been initialized, do so
    """
    try:
        root_dir = session.files.current_directory()

        if root_dir == '': # first time through, initialize
            data_path = session.configuration["dataRoot"]
            if data_path is not None:
                root_dir = os.path.normpath(data_path)
            else:
                return False


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
        else:
            return True
    except Exception, e:
        print e
        return False

    return True

def login(request):
    """
    Logs the user in
    If the login fails for whatever reason, authentication, invalid for instrument, etc.,
    returns to login page with error.
    Otherwise, gets the user data to populate the main page
    """

    global session

    #config_file = 'UploaderConfig.json'
    config_file = 'developmentUploaderConfig.json'
    if not os.path.isfile(config_file):
        session.write_default_config(config_file)
    session.read_config(config_file)

    # timeout
    try:
        timeout = session.configuration["timeout"]
        minutes = int(timeout)
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

    server_path = session.configuration["server"]
    if server_path is not None:
        session.server_path = server_path
    else:
        return login_error(request, 'Server path does not exist')

    
    # test to see if the user authorizes against EUS
    authorized = test_authorization(protocol="https",
                                    server=session.server_path,
                                    user=session.user,
                                    password=session.password)

    if not authorized:
        return login_error(request, 'User or Password is incorrect')

    inst = session.configuration["instrument"]
    if inst and inst is not '':
        session.instrument = inst
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

    if not initialize_settings():
        return login_error(request, 'Unable to initialize settings')


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
