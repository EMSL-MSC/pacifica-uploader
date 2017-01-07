﻿# pylint: disable=no-member
# justification:  dynamic methods

# pylint: disable=invalid-name
# justification: module level variables

# pylint: disable=too-many-return-statements
# justification: argument with style

# pylint: disable=broad-except
# justification: argument with style

"""
Django views, handle requests from the client side pages
"""

from __future__ import absolute_import

from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect

from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseServerError

from django.core.urlresolvers import reverse

import json

import datetime

# operating system
import os

import home.task_comm

# session imports
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib import auth
from django.contrib.auth.decorators import login_required

# celery tasks
from home import tasks
# for checking celery status
from celery.result import AsyncResult

# delay for celery heartbeat
from time import sleep

# for restarting Celery
import subprocess

from home import session_data
from home import file_tools
from home import instrument_server
from home import QueryMetadata

# Module level variables
# session is user specific information
session = session_data.SessionState()

# server is instrument uploader specific information
configuration = instrument_server.UploaderConfiguration()

metadata = None

# development version
version = '2.02'


def login_user_locally(request):
    """
    if we have a new user, let's create a new Django user and log them
    in. Actual EUS authentication will be done before this function is called.
    """
    username = request.POST['username']
    password = request.POST['password']

    # does this user exist?
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = None

    if user is None:
        # create a new user
        user = User.objects.create_user(username=username, password=password)
        user.save()
    else:
        # user exists but their password may have changed
        # if we make it this far, user has been validated by EUS
        # so store the 'new' password
        user.set_password(password)
        user.save()

    # we now have a local user that matches the already validated EUS user
    # authenticate and log them in locally
    user = authenticate(username=username, password=password)
    if user:
        if user.is_active:
            auth.login(request, user)
    else:
        return 'Unable to create user'


def ping_celery():
    """
    check to see if the celery process to bundle and upload is alive, alive!
    """
    ping_process = tasks.ping.delay()

    tries = 0
    while tries < 5:
        state = ping_process.status
        if state is not None:
            print state
            if state == 'PING' or state == 'SUCCESS':
                return True
        sleep(1)
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
            subprocess.Popen(
                'celery -A UploadServer worker --loglevel=info', shell=True)
        except Exception, e:
            print e

    count = 0
    alive = False
    while not alive and count < 10:
        sleep(1)
        alive = ping_celery()
        count = count + 1

    return alive


@login_required(login_url=settings.LOGIN_URL)
def populate_upload_page(request):
    """
    formats the main uploader page
    """
    # if not logged in
    if session.password == '':
        # call login error with no error message
        return login_error(request, '')

    if session.is_timed_out():
        return logout(request)

    # reset timeout
    session.touch()

    request.session.modified = True
    # age = request.session.get_expiry_age()

    root_dir = session.files.data_dir

    if not root_dir or root_dir == '':
        return login_error(request, 'Data share is not configured')

    try:
        os.listdir(root_dir)
    except Exception:
        return login_error(request, 'error accessing Data share')

    # update the free space when the page is loaded
    # this will update after an upload is done
    configuration.update_free_space()

    # Render list page with the documents and the form
    return render_to_response('home/uploader.html',
                              {'data_root': session.files.data_dir,
                               'metaList': metadata.meta_list,
                               'user': session.user_full_name},
                              context_instance=RequestContext(request))


def show_initial_status(request):
    """
    shows the status page with no message
    """
    return show_status_insert(request, '')


def set_data_root(request):
    """
    explicitly set the data root
    """
    try:
        mode = request.POST.get('mode')

        # if empty root, restore the original
        if mode == 'restore':
            session.restore_session_root()
        else:
            parent = request.POST.get('parent')
            if not parent:
                return HttpResponseServerError(json.dumps('missing root directory'),
                                               content_type='application/json')

            session.set_session_root(parent)

        return HttpResponse(json.dumps('success'), content_type='application/json')

    except Exception, e:
        return HttpResponseServerError(json.dumps(e.message), content_type='application/json')


def show_status(request, message):
    """
    show the status of the existing upload task
    """
    session.current_time = datetime.datetime.now().strftime('%m.%d.%Y.%H.%M.%S')

    return render_to_response('home/status.html',
                              {
                                  'status': message,
                                  'metaList': metadata.meta_list,
                                  'current_time': session.current_time,
                                  'bundle_size': session.files.bundle_size_str,
                                  'free_size': configuration.free_size_str,
                                  'user': session.user_full_name},
                              context_instance=RequestContext(request))


def show_status_insert(request, message):
    """
    show the status of the existing upload task
    """
    session.current_time = datetime.datetime.now().strftime('%m.%d.%Y.%H.%M.%S')

    return render_to_response('home/status_insert.html',
                              {'status': message,
                               'metaList': metadata. meta_list,
                               'current_time': session.current_time,
                               'bundle_size': session.files.bundle_size_str,
                               'free_size': configuration.free_size_str},
                              context_instance=RequestContext(request))


def post_upload_metadata(request):
    """
    populates the upload metadata from the upload form
    """
    data = request.POST.get('form')
    try:
        form = json.loads(data)

        metadata.populate_metadata_from_form(form)

        session.current_time = datetime.datetime.now().strftime('%m.%d.%Y.%H.%M.%S')
        return HttpResponse(json.dumps('success'), content_type='application/json')

    except Exception, e:
        return HttpResponseServerError(json.dumps(e.message), content_type='application/json')


def spin_off_upload(request):
    """
    spins the upload process off to a background celery process
    """

    # initialize the task state
    home.task_comm.set_state('', '')

    data = request.POST.get('files')
    try:
        if data:
            files = json.loads(data)
        else:
            return HttpResponseBadRequest(json.dumps('missing files in post'),
                                          content_type='application/json')
    except Exception, e:
        return HttpResponseBadRequest(json.dumps(e.message), content_type='application/json')

    if not files:
        return HttpResponseBadRequest(json.dumps('missing files in post'),
                                      content_type='application/json')

    session.is_uploading = True

    if home.task_comm.USE_CELERY:
        # check to see if background celery process is alive
        # Wait 5 seconds
        session.celery_is_alive = ping_celery()
        print 'Celery lives = %s' % (session.celery_is_alive)
        if not session.celery_is_alive:
            session.is_uploading = False
            return HttpResponseServerError(json.dumps('Celery is dead'),
                                           content_type='application/json')

    try:
        tuples = session.files.get_bundle_files(files)

        session.current_time = datetime.datetime.now().strftime('%m.%d.%Y.%H.%M.%S')

        session.bundle_filepath = os.path.join(
            configuration.target_dir, session.current_time + '.tar')

        meta_list = metadata.create_meta_upload_list()

        # spin this off as a background process and load the status page
        if home.task_comm.USE_CELERY:
            session.bundle_process = \
                tasks.upload_files.delay(ingest_server=configuration.ingest_server,
                                         bundle_name=session.bundle_filepath,
                                         file_list=tuples,
                                         bundle_size=session.files.bundle_size,
                                         meta_list=meta_list)
        else:  # run local
            tasks.upload_files(ingest_server=configuration.ingest_server,
                               bundle_name=session.bundle_filepath,
                               file_list=tuples,
                               bundle_size=session.files.bundle_size,
                               meta_list=meta_list)
    except Exception, e:
        session.is_uploading = False
        return HttpResponseServerError(json.dumps(e.message), content_type='application/json')

    return HttpResponse(json.dumps('success'), content_type='application/json')


def upload_files(request):
    """
    view for upload process spawn
    """
    try:
        # use this flag to determine status of upload in incremental status
        session.is_uploading = True

        reply = spin_off_upload(request)

        return reply

    except Exception, e:
        return e.message


"""
login and login related accesories
"""
##########################################################################


def login_error(request, error_string):
    """
    returns to the login page with an error message
    """
    if not configuration.initialized:
        configuration.initialize_settings()

    return render_to_response(settings.LOGIN_VIEW,
                              {'site_version': version,
                               'instrument': configuration.instrument,
                               'message': error_string},
                              context_instance=RequestContext(request))


def cookie_test(request):
    """
    This test needs to be called twice in a row.  The first call should fail as the
    cookie hasn't been set.  The second should succeed.  If it doesn't,
    you need to enable cookies on the browser.
    """
    # test that the browser is supporting cookies so we can maintain our
    # session state
    if request.session.test_cookie_worked():
        request.session.delete_test_cookie()
        return render_to_response('home/cookie.html', {'message': 'Cookie Success'},
                                  context_instance=RequestContext(request))
    else:
        request.session.set_test_cookie()
        return render_to_response('home/cookie.html', {'message': 'Cookie Failure'},
                                  context_instance=RequestContext(request))


def login(request):
    """
    Logs the user in
    If the login fails for whatever reason, authentication, invalid for instrument, etc.,
    returns to login page with error.
    Otherwise, gets the user data to populate the main page
    """

    # initialize server settings from scratch
    configuration.initialized = False
    err = configuration.initialize_settings()
    if err != '':
        return login_error(request, 'faulty configuration:  ' + err)

    # timeout
    #SESSION_COOKIE_AGE = configuration.timeout * 60

    # ignore GET
    if not request.POST:
        return login_error(request, '')

    new_user = request.POST['username']
    new_password = request.POST['password']

    global session
    if session:
        # check to see if there is an existing user logged in
        if session.current_user:
            # if the session is timed out, logout the current user
            if session.is_timed_out():
                logout(request)
            else:
                # if the current user is still logged in and this is not that
                # user, throw an error
                if new_user != session.user:
                    return login_error(request,
                                       'User %s is currently logged in' % session.user_full_name)

    # after login you lose your session context
    session = session_data.SessionState()
    session.config = configuration

    # initialize the data dir for the session to the configured default
    session.files.data_dir = session.config.data_dir

    # loads the metadata structure from the config file
    global metadata
    metadata = QueryMetadata.QueryMetadata(
        configuration.policy_server, new_user)

    # log them in locally for our session
    err_str = login_user_locally(request)
    if err_str:
        return login_error(request, err_str)

    # did that work?
    if not request.user.is_authenticated():
        return login_error(request, 'Problem with local authentication')

    # try:
    #    tasks.clean_target_directory(configuration.target_dir)
    # except:
    #    return login_error(request, 'failed to clear tar directory')

    # keep a copy of the user so we can keep other users from stepping on them if they are still
    # logged in
    session.current_user = request.user
    session.is_logged_in = True
    session.password = new_password
    session.touch()

    return HttpResponseRedirect(reverse('home.views.populate_upload_page'))


def logout(request):
    """
    logs the user out and returns to the main page
    which will bounce to the login page
    """

    session.current_user = None

    # logs out local user session
    # if the LOGOUT_URL is set to this view, we create a recursive call to here
    auth.logout(request)

    session.is_logged_in = False

    return HttpResponseRedirect(reverse('home.views.login'))

# pylint: disable=unused-argument
# justification: django required
def initialize_fields(request):
    """
    initializes the metadata fields
    """

    updates = metadata.initial_population()

    retval = json.dumps(updates)

    return HttpResponse(retval, content_type='application/json')


def select_changed(request):
    """
    get the updated metadata on a select field change
    """

    # reset timeout
    session.touch()

    form = json.loads(request.body)

    updates = metadata.populate_dependencies(form)

    retval = json.dumps(updates)

    return HttpResponse(retval, content_type='application/json')


def get_children(request):
    """
    get the children of a parent directory, used for lazy loading
    """
    try:
        # return empty list on error, folder permissions, etc.
        pathlist = []
        retval = json.dumps(pathlist)

        parent = request.GET.get('parent')
        if not parent:
            return retval

        if not session.files.accessible(parent):
            return retval

        session.files.error_string = ''

        if os.path.isdir(parent):
            lazy_list = os.listdir(parent)
            lazy_list.sort(key=lambda s: s.lower())

            # simple filter for hidden files in linux
            # replace with configurable regex later
            #regex  = re.compile('\.(.+?)')
            filtered = [i for i in lazy_list if not i[0] == '.']

            # folders first
            for item in filtered:
                itempath = os.path.join(parent, item)
                time = os.path.getmtime(itempath)
                mod_time = datetime.datetime.fromtimestamp(
                    time).strftime('%m/%d/%Y %I:%M%p')

                if session.files.accessible(itempath):
                    if os.path.isfile(itempath):
                        pathlist.append(
                            {'title': item + ' ' +
                             '<span class="fineprint"> [Last Modified ' + mod_time +
                             ']</span>', 'key': itempath,
                             'folder': False, 'data': {'time': time}})
                    elif os.path.isdir(itempath):
                        pathlist.append(
                            {'title': item, 'key': itempath, 'folder': True,
                             'lazy': True, 'data': {'time': time}})

        retval = json.dumps(pathlist)

    except Exception, e:
        print e
        return error_response('lazyload failed')

    return HttpResponse(retval)


def error_response(err_str):
    """
    send an http error response with an appropriate error message
    """
    return HttpResponse(json.dumps('Error: ' + err_str),
                        content_type='application/json',
                        status=500)


def make_leaf(title, path):
    '''
    return a populated tree leaf
    '''
    if session.files.accessible(path):
        if os.path.isfile(path):
            size = os.path.getsize(path)
            is_folder = False
        elif os.path.isdir(path):
            size = session.files.get_size(path)
            is_folder = True

    session.files.bundle_size += size

    size_string = file_tools.size_string(size)
    return {'title': title + ' (' + size_string + ')',
            'key': path,
            'folder': is_folder,
            'data': {'size': size}}


def add_branch(branches, subdirectories, title, path):
    """
    recursively insert branch into a tree structure
    """
    # if we are at a leaf, add the leaf to the children list
    if len(subdirectories) < 2:
        leaf = make_leaf(title, path)
        if leaf:
            branches.append(leaf)
        return

    branch_name = subdirectories[0]

    for branch in branches:
        if branch['title'] == branch_name:
            children = branch['children']
            add_branch(children, subdirectories[1:], title, path)
            return

    # not found, add the branch
    branch = {'title': branch_name, 'key': 1,
              'folder': True, 'expanded': True, 'children': []}
    children = branch['children']
    add_branch(children, subdirectories[1:], title, path)
    branches.append(branch)


def make_tree(tree, subdirectories, partial_path, title, path):
    '''
    recursively split filepaths
    '''

    if not partial_path:
        children = tree['children']
        add_branch(children, subdirectories, title, path)
        return

    head, tail = os.path.split(partial_path)

    # prepend the tail
    subdirectories.insert(0, tail)
    make_tree(tree, subdirectories, head, title, path)


def return_bundle(tree, message):
    """
    formats the return message from get_bundle
    """
    # validate that the currently selected bundle will fit in the target space
    upload_enabled = session.validate_space_available()
    # disable the upload if there isn't enough space in the intermediate
    # directory
    tree[0]['enabled'] = upload_enabled
    if not upload_enabled:
        message = message + ' The amount of data you are trying to transfer is larger ' \
            'than the space available in the Uploader Controller.  '\
            'Reduce the size of the data set or contact an administrator' \
            'to help address this issue.'

    session.files.bundle_size_str = file_tools.size_string(
        session.files.bundle_size)
    if message != '':
        tree[0]['data'] = 'Bundle: %s, Free: %s, Warning: %s' % (
            session.files.bundle_size_str, configuration.free_size_str, message)
    else:
        tree[0]['data'] = 'Bundle: %s, Free: %s' % (
            session.files.bundle_size_str, configuration.free_size_str)

    retval = json.dumps(tree)
    return HttpResponse(retval, content_type='application/json')


def get_bundle(request):
    """
    return a tree structure containing directories and files to be uploaded
    """

    # reset timeout
    session.touch()

    try:
        session.files.error_string = ''

        tree, lastnode = session.get_archive_tree(metadata)
        session.files.bundle_size = 0

        pathstring = request.POST.get('packet')

        # can get a request with 0 paths, return empty bundle
        if not pathstring:
            return return_bundle(tree, '')

        paths = json.loads(pathstring)

        # if no paths, return the empty archive structure
        if not paths:
            return return_bundle(tree, '')

        # this actually should be done already by getting parent nodes
        filtered = session.files.filter_selected_list(paths)

        common_path = session.files.data_dir

        # add a final separator
        common_path = os.path.join(common_path, '')

        # used later to modify arc names
        session.files.common_path = common_path

        for itempath in paths:
            # title
            item = os.path.basename(itempath)

            # tree structure
            clipped_path = itempath.replace(common_path, '')
            subdirs = []
            make_tree(lastnode, subdirs, clipped_path, item, itempath)

        return return_bundle(tree, session.files.error_string)

    except Exception, e:
        return return_bundle(tree, 'get_bundle failed:  ' + e.message)

# pylint: disable=unused-argument
# justification: django required
def get_state(request):
    """
    returns the status of the uploader
        logged_in
        uploading
        idle
    """
    state = 'idle'
    if session.is_logged_in:
        state = 'logged in: '

    if session.bundle_process:
        print session.bundle_process.task_id
        res = AsyncResult(session.bundle_process.task_id)
        if not res.ready():
            state += 'uploading'

    retval = json.dumps({'state': state})
    return HttpResponse(retval)


def incremental_status(request):
    """
    updates the status page with the current status of the background upload process
    """
    # pass pylint
    request = request

    # reset timeout
    session.touch()

    try:
        if request.POST:
            if session.bundle_process:
                session.bundle_process.revoke(terminate=True)
            session.cleanup_upload()
            state = 'CANCELLED'
            result = ''
            session.is_uploading = False

            print state
        else:
            if not session.is_uploading:
                state = 'CANCELLED'
                result = ''
                print state

            elif home.task_comm.USE_CELERY:
                if not session.bundle_process:
                    state = 'PENDING'
                    result = 'Spinning off background process'
                else:
                    state = session.bundle_process.status
                    if state is None:
                        state = 'UNKNOWN'
                    print state

                    result = session.bundle_process.result
                    if result is None:
                        result = ''
                    print result

            else:
                state, result = home.task_comm.get_state()

            if state == 'DONE':
                d = json.loads(result)
                job_id = d['job_id']
                print 'completed job ', job_id

                # if we have successfully uploaded, cleanup the lists
                session.cleanup_upload()
                session.is_uploading = False

        # create json structure
        retval = json.dumps({'state': state, 'result': result})

        return HttpResponse(retval)

    except Exception, e:
        print e.message
        session.is_uploading = False
        retval = json.dumps({'state': 'Status Error', 'result': e.message})
        return HttpResponse(retval)
