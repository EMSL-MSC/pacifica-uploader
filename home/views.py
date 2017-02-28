# pylint: disable=broad-except
# justification: need to catch broad exceptions at entry point to log
# the stack trace to underlying exceptions

# pylint: disable=global-statement
# justification: by design
"""
Django views, handle requests from the client side pages
"""

from __future__ import absolute_import

import json
import datetime
import os
import base64
import re
import sys
import traceback
from time import sleep

from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect

from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseServerError

from django.core.urlresolvers import reverse

from celery.result import AsyncResult

from home.task_comm import TaskComm
from home import tasks
from home import session_data
from home import file_tools
from home import instrument_server
from home import QueryMetadata

# pylint: disable=invalid-name
# session is global need to fix later
session = session_data.SessionState()

# server is instrument uploader specific information
configuration = instrument_server.UploaderConfiguration()

metadata = None
# pylint: enable=invalid-name

# development VERSION
VERSION = '2.11.1.1.1'


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

def user_from_request(request):
    """ returns the user if in meta """

    if 'HTTP_AUTHORIZATION' in request.META:
        auth = request.META['HTTP_AUTHORIZATION']
        scheme, creds = re.split(r'\s+', auth)
        if scheme.lower() != 'basic':
            raise ValueError('Unknown auth scheme \"%s\"' % scheme)
        user = base64.b64decode(creds).split(':', 1)[0]
        print 'user_from_request: ' + user
        return user
    else:
        return None

def is_current_user(request):
    """ is this the user currently logged in? """

    new_user = user_from_request(request)

    print 'is_current_user: ' +  new_user

    return (new_user == session.network_id)

def validate_user_handler(request):
    """
    checks to see if:
        no one is logged in, in which case log this user in
        user is logged in and this is the current user, in which case just reload the page (losing context)
        a user is logged in and this is not that user, in which case block them out
    """

    print 'validate_user_handler'

    new_user = user_from_request(request)

    if not new_user:
        render = login_error(request, 'missing authorization')
        return render

    # pylint: disable=invalid-name
    global session
    # pylint: enable=invalid-name
    if session:
        # check to see if there is an existing user logged in
        if session.network_id and session.is_logged_in:

            # if the current user is still logged in and this is not that user
            if new_user != session.network_id:
                 # if timed out, log out, don't show page
                if session.is_timed_out():
                    logout(request)
                else:
                    name = metadata.get_user_name(session.network_id)
                    return login_error(request,
                                        'User %s is currently logged in' % name)
            else:
                session.touch()
                return # just reload the page if user is already logged in.
    
    print 'trying to log in:  ' + new_user
    # new valid user, log that bad boy in
    return login(request, new_user)

def populate_upload_page(request):
    """
    formats the main uploader page
    """

    validation_redirect = validate_user_handler(request)
    if validation_redirect:
        return validation_redirect

    # reset timeout
    session.touch()

    request.session.modified = True

    # update the free space when the page is loaded
    # move to file_tools dfh
    configuration.update_free_space()

    # Render the upload page with the meta (just the render format) and the default root directory
    return render_to_response('home/uploader.html',
                              {'data_root': session.files.data_dir,
                               'metaList': metadata.meta_list},
                              RequestContext(request))


def show_initial_status(request):
    """
    shows the status page with no message
    """
    return show_status_insert(request, '')

def print_err(ex):
    """ prints error """
    print >> sys.stderr, '-'*60
    print >> sys.stderr, 'Exception:'
    traceback.print_exc(file=sys.stderr)
    print >> sys.stderr, '-'*60

def report_err(ex):
    """ consolidates error reporting code """
    print_err(ex)
    return HttpResponseServerError(json.dumps(ex.message), content_type='application/json')


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

        time = os.path.getmtime(session.files.data_dir)

        node = [{'title': session.files.data_dir, 'key': session.files.data_dir, 'folder': True,
                 'lazy': True, 'data': {'time': time}}]

        return HttpResponse(json.dumps(node), content_type='application/json')

    except Exception, ex:
        return report_err(ex)



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
                              RequestContext(request))

def user_logged_in(request):
    """
    checks to see if:
        no one is logged in, in which case log this user in
        user is logged in and this is the current user, in which case just reload the page (losing context)
        a user is logged in and this is not that user, in which case block them out
    """

    print 'user_logged_in'

    new_user = user_from_request(request)

    if not new_user:
        return False

    # pylint: disable=invalid-name
    global session
    # pylint: enable=invalid-name
    if session:
        # check to see if there is an existing user logged in
        if session.network_id and session.is_logged_in:

            # if the current user is still logged in
            if new_user == session.network_id:
                 # if timed out, log out, don't show page
                if session.is_timed_out():
                    logout(request)
                else:
                    return True
    return False

def post_upload_metadata(request):
    """
    populates the upload metadata from the upload form
    """

    if not user_logged_in(request):
        return HttpResponse(json.dumps('failed'), content_type='application/json')


    # do this here because the async call from the browser
    # may call for a status before spin_off_upload is started
    session.is_uploading = True

    data = request.POST.get('form')
    try:
        form = json.loads(data)

        metadata.populate_metadata_from_form(form)

        session.current_time = datetime.datetime.now().strftime('%m.%d.%Y.%H.%M.%S')
        return HttpResponse(json.dumps('success'), content_type='application/json')

    except Exception, ex:
        return report_err(ex)

# pylint: disable=too-many-return-statements
# justification: disagreement with style
def spin_off_upload(request):
    """
    spins the upload process off to a background celery process
    """

    # initialize the task state
    if not TaskComm.USE_CELERY:
        TaskComm.set_state('', '')

    data = request.POST.get('files')
    try:
        if data:
            files = json.loads(data)
        else:
            return HttpResponseBadRequest(json.dumps('missing files in post'),
                                          content_type='application/json')
    except Exception, ex:
        return report_err(ex)

    if not files:
        return HttpResponseBadRequest(json.dumps('missing files in post'),
                                      content_type='application/json')

    session.is_uploading = True

    if TaskComm.USE_CELERY:
        # check to see if background celery process is alive
        # Wait 5 seconds
        is_alive = ping_celery()
        print 'Celery lives = %s' % (is_alive)
        if not is_alive:
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
        if TaskComm.USE_CELERY:
            session.upload_process = \
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
    except Exception, ex:
        session.is_uploading = False
        return report_err(ex)

    return HttpResponse(json.dumps('success'), content_type='application/json')


def upload_files(request):
    """
    view for upload process spawn
    """
    # use this flag to determine status of upload in incremental status
    session.is_uploading = True

    reply = spin_off_upload(request)

    return reply


########################################################################
# login and login related accessories
##########################################################################


def login_error(request, error_string):
    """
    returns page with an error message
    """

    return render_to_response(settings.LOGIN_VIEW,
                                {'site_version': VERSION,
                                'instrument': configuration.instrument,
                                'message': error_string},
                                RequestContext(request))



def login(request, new_user):
    """
    Logs the user in
    If the login fails for whatever reason, invalid for instrument, etc.,
    returns to login page with error.
    Otherwise, gets the user data to populate the main page
    """


    # initialize server settings from scratch
    configuration.initialized = False
    err = configuration.initialize_settings()
    if err != '[]':
        return login_error(request, 'faulty configuration:  ' + err)

    # loads the metadata structure from the config file so we can populate the initial html for the upload page
    # pylint: disable=invalid-name
    global metadata
    # pylint: enable=invalid-name
    metadata = QueryMetadata.QueryMetadata(configuration.policy_server)


    # after login you lose your session context
    global session
    session = session_data.SessionState()
    session.config = configuration

    # initialize the data dir for the session to the configured default
    # check to see if needed dfh
    session.files.data_dir = session.config.data_dir

    # try:
    #    tasks.clean_target_directory(configuration.target_dir)
    # except:
    #    return

    # keep a copy of the user so we can keep other users from stepping on them
    session.network_id = new_user
    session.is_logged_in = True
    session.touch()

    # current assumption for a single user system is that we have been called through the / url
    # which is the populate page
    # which accepts a 'none' as a valid login or NOP
    # if we made it this far, this must meet our definition of truth
    return

# pylint: disable=unused-argument
# justification: django required
def logout(request):
    """
    logs the user out and returns to the main page
    which will bounce to the login page
    """

    print 'logout'

    if is_current_user(request):
        session.network_id = None
        session.is_logged_in = False

    return login_error(request, "Logged out")

# pylint: disable=unused-argument
# justification: django required
def logged_in(request):
    """
    logs the user out and returns to the main page
    which will bounce to the login page
    """

    print 'logged_in'

    # timeout check.
    # this will clear the user
    if session.is_timed_out():
        logout(request)

    if is_current_user(request):
        return_val = 'TRUE'
    else:        
        return_val = 'FALSE'

    return HttpResponse(return_val)


# pylint: disable=unused-argument
# justification: django required
def initialize_fields(request):
    """
    initializes the metadata fields
    """
    # start from scratch on first load and subsequent reloads of page
    # pylint: disable=invalid-name
    global metadata
    # pylint: enable=invalid-name
    metadata = QueryMetadata.QueryMetadata(configuration.policy_server)

    # populates metadata for the current user
    # to have a common model for init and reload we need to set
    # the network id here
    metadata.initialize_user(session.network_id)

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
                        title = \
                            ('%s <span class="fineprint"> [Last Modified %s ]</span>') % \
                            (item, mod_time)
                        pathlist.append({'title': title, 'key': itempath,
                                         'folder': False, 'data': {'time': time}})
                    elif os.path.isdir(itempath):
                        pathlist.append(
                            {'title': item, 'key': itempath, 'folder': True,
                             'lazy': True, 'data': {'time': time}})

        retval = json.dumps(pathlist)

    except Exception, ex:        
        return report_err(ex)

    return HttpResponse(retval)


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
        # filtered = session.files.filter_selected_list(paths)

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

    except Exception, ex:
        print_err(ex)
        return return_bundle(tree, 'get_bundle failed:  ' + ex.message)

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

    if session.upload_process:
        print session.upload_process.task_id
        res = AsyncResult(session.upload_process.task_id)
        if not res.ready():
            state += 'uploading'

    retval = json.dumps({'state': state})
    return HttpResponse(retval)

def get_status():
    """    get status from backend    """

    if (TaskComm.USE_CELERY):
        if session.upload_process == None:
            return 'Initializing', ''

        state = session.upload_process.state
        result = session.upload_process.result
        if state == 'FAILURE':
            # we fail to succeed, expecting an error object
            try:
                result = result.args[0]
                val = json.loads(result)
                val['job_id']
                state = 'DONE'
            except KeyError:
                # if this isn't a successful upload (no job_id) then just return the args.
                pass
    else:
        state, result = TaskComm.get_state()
        
    return state, result


def incremental_status(request):
    """
    updates the status page with the current status of the background upload process
    """
    if TaskComm.USE_CELERY:
        if session.upload_process == None:
            retval = json.dumps({'state': '', 'result': ''})
            return HttpResponse(retval)

    # reset timeout
    session.touch()

    try:
        if request.POST:
            if session.upload_process:
                session.upload_process.revoke(terminate=True)
            session.cleanup_upload()
            state = 'CANCELLED'
            result = ''
            session.is_uploading = False

            print state
        else:
            if not session.is_uploading:
                state = 'CANCELLED'
                result = ''
                retval = json.dumps({'state': state, 'result': result})
                return HttpResponse(retval)
            
        state, result = get_status()

        if state is not None:
            if state == 'DONE':
                ingest_result = json.loads(result)
                job_id = ingest_result['job_id']
                print 'completed job ', job_id

                # create URL for status server
                result = configuration.status_server + str(job_id)

                # if we have successfully uploaded, cleanup the lists
                session.cleanup_upload()
                session.is_uploading = False

        # create json structure
        retval = json.dumps({'state': state, 'result': result})

        return HttpResponse(retval)

    except Exception, ex:
        print_err(ex)
        retval = json.dumps({'state': 'Status Error', 'result': ex.message})
        return HttpResponse(retval)
