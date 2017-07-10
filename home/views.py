# pylint: disable=broad-except
# justification: need to catch broad exceptions at entry point to log
# the stack trace to underlying exceptions

# pylint: disable=global-statement
# justification: by design
"""
Django views, handle requests from the client side pages
"""

from __future__ import absolute_import

import psutil
import json
import datetime
import os
import base64
import re
import sys
import traceback
import cPickle as pickle
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

from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib import auth
from django.contrib.auth.decorators import login_required

from home.task_comm import TaskComm
from home import tasks
from home import file_tools
from home import instrument_server
from home import QueryMetadata
from home.file_tools import FileManager

# server is instrument uploader specific information
configuration = instrument_server.UploaderConfiguration()

# pylint: enable=invalid-name

# development VERSION
VERSION = '2.2.2'


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

        # temp kludge because of large data sets being transferred for super users
        user = 'd3g909'

        print 'user_from_request: ' + user
        return user
    else:
        return None

def initialize_config():
    """ load configuration if not currently loaded """

    # initialize server settings from scratch
    err = configuration.initialize_settings()
    if err != '[]':
        return err

# @login_required(login_url=settings.LOGIN_URL)
def populate_upload_page(request):
    """
    formats the main uploader page with authorized user metadata
    """

    retval = login(request)
    if retval:
        return login_error(request, retval)

    network_user = user_from_request(request)
    if not network_user:
        return login_error(request, "Network user is not authorized")

    if not configuration.initialized:
        err = initialize_config()
        if err:
            return login_error(request, 'faulty configuration:  ' + err)

    # metadata to initialize the layout of the main page
    metadata = fresh_meta_obj(request);

    # get the Pacifica user
    pacifica_user = metadata.get_Pacifica_user(network_user)

    if not pacifica_user:
        return login_error(request, "Pacifica user is not found")

    # Render the upload page with the meta (just the render format) and the default root directory
    return render_to_response('home/uploader.html',
                              {'data_root': configuration.data_dir,
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
            request.session['data_dir'] = configuration.data_dir
        else:
            parent = request.POST.get('parent')
            if not parent:
                return HttpResponseServerError(json.dumps('missing root directory'),
                                               content_type='application/json')
            request.session['data_dir'] = parent

        time = os.path.getmtime(request.session['data_dir'])

        node = [{'title': request.session['data_dir'], 'key': request.session['data_dir'], 'folder': True,
                 'lazy': True, 'data': {'time': time}}]

        return HttpResponse(json.dumps(node), content_type='application/json')

    except Exception, ex:
        return report_err(ex)

def current_time():
    return datetime.datetime.now().strftime('%m.%d.%Y.%H.%M.%S')

def show_status_insert(request, message):
    """
    show the status of the existing upload task
    """
    bundle_size_str = request.session['bundle_size_str']
    free_size_str = request.session['free_size_str']
    return render_to_response('home/status_insert.html',
                              {'status': message,
                               'bundle_size': bundle_size_str,
                               'free_size': free_size_str},
                              RequestContext(request))

def post_upload_metadata(request):
    """
    populates the upload metadata from the upload form
    ripping out, left in for now to keep js structure on browser side
    """
    set_uploading(request, True)

    print 'post meta'

    return HttpResponse(json.dumps('success'), content_type='application/json')

    # do this here because the async call from the browser
    # may call for a status before spin_off_upload is started
    set_uploading(request, True)

    data = request.POST.get('form')
    try:
        form = json.loads(data)

        metadata.populate_metadata_from_form(form)

        return

    except Exception, ex:
        return report_err(ex)

# pylint: disable=too-many-return-statements
# justification: disagreement with style
def spin_off_upload(request):
    """
    spins the upload process off to a background celery process
    """

    file_manager = FileManager()

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

    set_uploading(request, True)

    if TaskComm.USE_CELERY:
        # check to see if background celery process is alive
        # Wait 5 seconds
        is_alive = ping_celery()
        print 'Celery lives = %s' % (is_alive)
        if not is_alive:
            set_uploading(request, False)
            return HttpResponseServerError(json.dumps('Celery is dead'),
                                           content_type='application/json')

    try:
        file_manager.common_path = request.session['common_path']
        file_manager.archive_path = request.session['archive_path']
        tuples = file_manager.get_bundle_files(files)

        bundle_filepath = os.path.join(
            configuration.target_dir, current_time() + '.tar')

        # load the metadata object with the most recent updates
        metadata = fresh_meta_obj(request)

        # fill the metadata object with the latest updates
        data = request.POST.get('form')
        try:
            form = json.loads(data)
            metadata.populate_metadata_from_form(form)

        except Exception, ex:
            return report_err(ex)

        meta_list = metadata.create_meta_upload_list()

        # spin this off as a background process and load the status page
        if TaskComm.USE_CELERY:
            upload_process = \
                tasks.upload_files.delay(ingest_server=configuration.ingest_server,
                               bundle_name=bundle_filepath,
                               file_list=tuples,
                               bundle_size=file_manager.bundle_size,
                               meta_list=meta_list,
                               auth=configuration.auth)
            request.session['upload_process'] = upload_process.task_id
            request.session.modified = True
        else:  # run local
            tasks.upload_files(ingest_server=configuration.ingest_server,
                               bundle_name=bundle_filepath,
                               file_list=tuples,
                               bundle_size=file_manager.bundle_size,
                               meta_list=meta_list,
                               auth=configuration.auth)
    except Exception, ex:
        set_uploading(request, False)

    return HttpResponse(json.dumps('success'), content_type='application/json')


def upload_files(request):
    """
    view for upload process spawn
    """

    # use this flag to determine status of upload in incremental status
    set_uploading(request, True)

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
                                'message': error_string},
                                RequestContext(request))

def login_user_locally(request):
    """
    if we have a new user, let's create a new Django user and log them in
    This is a dummy account so we can use the session middleware
    """

    # check to see if the user is already logged in
    #if (request.user.is_authenticated()):
    #    return

    username = user_from_request(request)
    if not username:
        return 'unable to authorize anonymous user'

    password = 'Pacifica'

    # does this user exist?
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = None

    if user is None:
        #create a new user
        user = User.objects.create_user(username=username, password=password)
    else:
        # set default password, overwriting and dangling users in database
        user.set_password(password)

    user.save()

    # we now have a local user that matches the already validated Pacifica user
    # authenticate and log them in locally
    user = authenticate(username=username, password=password)
    if user:
        if user.is_active:
            auth.login(request, user)
    else:
        return "Unable to create user"

def login(request):
    """
    Logs the user in
    If the login fails for whatever reason, authentication, invalid for instrument, etc.,
    returns to login page with error.
    Otherwise, gets the user data to populate the main page
    """

    logged_in = request.user.is_authenticated()

    # initialize server settings if they are not
    if not configuration.initialized:
        err = configuration.initialize_settings()
        if err != '[]':
            return ('faulty configuration:  ' + err)

    # timeout
    #SESSION_COOKIE_AGE = configuration.timeout * 60

    # the user has passed Pacifica authentication so log them in locally for a session
    err_str = login_user_locally(request)
    if err_str:
        return (err_str)

    # did that work?
    logged_in = request.user.is_authenticated
    logged_in = request.user.is_authenticated()
    if not request.user.is_authenticated():
        return ('Problem with local authentication')

    request.session['data_dir'] = configuration.data_dir
    request.session.modified = True

    # ok, passed all local authorization tests, valid user data is loaded

    #try:
    #    tasks.clean_target_directory(configuration.target_dir,
    #                                 configuration.server_path,
    #                                 session.current_user,
    #                                 session.password)
    #except:
    #    return login_error(request, "failed to clear tar directory")

    #return HttpResponseRedirect(reverse('home.views.populate_upload_page'))
    return

# pylint: disable=unused-argument
# justification: django required'
def logout(request):
    """
    logs the user out and returns to the main page
    which will bounce to the login page
    """

    return login_error(request, "Logged out")

# pylint: disable=unused-argument
# justification: django required
def logged_in(request):
    """
    logs the user out and returns to the main page
    which will bounce to the login page
    """

    return HttpResponse('TRUE')

def fresh_meta_obj(request):
    metadata = QueryMetadata.QueryMetadata(configuration.policy_server)
    metadata.load_meta()

    network_id = user_from_request(request)

    # get the Pacifica user, hopefully just once
    if 'metaStr' in request.session:
        unicode_string = request.session['metaStr']
        meta_string = unicode_string.encode('ascii','ignore')
        meta_list = pickle.loads(meta_string)
        metadata.meta_list = meta_list
    else:
        meta_string = pickle.dumps(metadata.meta_list)
        request.session['metaStr'] = meta_string
        request.session.modified = True

    # get the Pacifica user, hopefully just once
    if 'PacificaUser' in request.session:
        pacifica_user = request.session['PacificaUser']
    else:
        pacifica_user = metadata.get_Pacifica_user(network_id)
        request.session['PacificaUser'] = pacifica_user
        request.session.modified = True

    metadata.user = pacifica_user
    return metadata

# pylint: disable=unused-argument
# justification: django required
def initialize_fields(request):
    """
    initializes the metadata fields
    start from scratch on first load and subsequent reloads of page
    """

    # populates metadata for the current user
    # replace this call with Pacifica_user from cookie, dfh
    network_id = user_from_request(request)

    # start from scratch on first load and subsequent reloads of page
    metadata = fresh_meta_obj(request)

    updates = metadata.initial_population(network_id)

    retval = json.dumps(updates)

    # clean the selection lists from the metadata list
    # so that our header isn't freaking huge
    for meta in metadata.meta_list:
        meta.browser_field_population['selection_list'] = []

    # set the metadata string variable to pass metadata state back to the browser
    list_string = pickle.dumps(metadata.meta_list)
    request.session['metaStr'] = list_string;
    request.session.modified = True

    return HttpResponse(retval, content_type='application/json')


def select_changed(request):
    """
    get the updated metadata on a select field change
    """

    # clean metadata object
    metadata = fresh_meta_obj(request)

    # create the base metadata object and load with defaults
    form = json.loads(request.body)

    # fill in the dependencies for changed fields
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
        
        files = FileManager()
        if not files.accessible(parent):
            return retval

        files.error_string = ''

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

                if files.accessible(itempath):
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


def make_leaf(title, path, files):
    '''
    return a populated tree leaf
    '''
    if files.accessible(path):
        if os.path.isfile(path):
            size = os.path.getsize(path)
            is_folder = False
        elif os.path.isdir(path):
            size = files.get_size(path)
            is_folder = True

    files.bundle_size += size

    size_string = file_tools.size_string(size)
    return {'title': title + ' (' + size_string + ')',
            'key': path,
            'folder': is_folder,
            'data': {'size': size}}


def add_branch(branches, subdirectories, title, path, files):
    """
    recursively insert branch into a tree structure
    """
    # if we are at a leaf, add the leaf to the children list
    if len(subdirectories) < 2:
        leaf = make_leaf(title, path, files)
        if leaf:
            branches.append(leaf)
        return

    branch_name = subdirectories[0]

    for branch in branches:
        if branch['title'] == branch_name:
            children = branch['children']
            add_branch(children, subdirectories[1:], title, path, files)
            return

    # not found, add the branch
    branch = {'title': branch_name, 'key': 1,
              'folder': True, 'expanded': True, 'children': []}
    children = branch['children']
    add_branch(children, subdirectories[1:], title, path, files)
    branches.append(branch)


def make_tree(tree, subdirectories, partial_path, title, path, files):
    '''
    recursively split filepaths
    '''

    if not partial_path:
        children = tree['children']
        add_branch(children, subdirectories, title, path, files)
        return

    head, tail = os.path.split(partial_path)

    # prepend the tail
    subdirectories.insert(0, tail)
    make_tree(tree, subdirectories, head, title, path, files)

def update_free_space(request):
        """
        update the amount of free space currently available
        this should go in file_tools
        """
        # get the disk usage
        space = psutil.disk_usage(configuration.target_dir)

        # give ourselves a cushion for other processes
        free_space = int(.9 * space.free)
        free_size_str = file_tools.size_string(free_space)
        
        request.session['free_space'] = free_space
        request.session['free_size_str'] = free_size_str
        request.session.modified = True


def validate_space_available(request):
    """
    check the bundle size agains space available
    """

    update_free_space(request)

    if request.session['bundle_size'] == 0:
        return True
    return request.session['bundle_size'] < request.session['free_space']

def return_bundle(request, tree, message):
    """
    formats the return message from get_bundle
    """
    files = FileManager()
    
    # validate that the currently selected bundle will fit in the target space
    upload_enabled = validate_space_available(request)

    # disable the upload if there isn't enough space in the intermediate
    # directory
    tree[0]['enabled'] = upload_enabled
    if not upload_enabled:
        message = message + ' The amount of data you are trying to transfer is larger ' \
            'than the space available in the Uploader Controller.  '\
            'Reduce the size of the data set or contact an administrator' \
            'to help address this issue.'

    free = request.session['free_size_str']
    size = request.session['bundle_size_str']
    if message != '':
        tree[0]['data'] = 'Bundle: %s, Free: %s, Warning: %s' % (size, free, message)
    else:
        tree[0]['data'] = 'Bundle: %s, Free: %s' % (size, free)

    retval = json.dumps(tree)
    return HttpResponse(retval, content_type='application/json')

def get_archive_tree(request):
    """
    returns a nested structure that can be used to populate fancytree
    """

    meta = fresh_meta_obj(request)

    newlist = sorted(meta.meta_list, key=lambda x: x.directory_order)

    nodes = []
    for node in newlist:
        if node.directory_order is not None:
            display = meta.get_display(node)
            nodes.append(display)

    tree = []
    children = tree
    lastnode = {}
    archive_path = ''

    for node_name in nodes:
        node = {"title": node_name,
                "key": 1,
                "folder": True,
                "expanded": True,
                "children": [],
                "data": ""}
        children.append(node)
        children = node['children']
        lastnode = node

        # concatenate the archive path
        archive_path = os.path.join(archive_path, node_name)

    request.session['archive_path'] = archive_path
    request.session.modified = True

    return tree, lastnode

def get_bundle(request):
    """
    return a tree structure containing directories and files to be uploaded
    """
    files = FileManager()

    tree = []

    try:
        files.error_string = ''

        print 'get pseudo directory'
        tree, lastnode = get_archive_tree(request)
        files.bundle_size = 0

        request.session['bundle_size'] = files.bundle_size
        request.session['bundle_size_str'] = file_tools.size_string(files.bundle_size)
        request.session.modified = True

        pathstring = request.POST.get('packet')

        # can get a request with 0 paths, return empty bundle
        if not pathstring:
            return return_bundle(request, tree, '')

        paths = json.loads(pathstring)

        # if no paths, return the empty archive structure
        if not paths:
            return return_bundle(request, tree, '')

        common_path = request.session['data_dir']

        # add a final separator
        common_path = os.path.join(common_path, '')

        # used later to modify arc names
        files.common_path = common_path

        for itempath in paths:
            # title
            item = os.path.basename(itempath)

            # tree structure
            clipped_path = itempath.replace(common_path, '')
            subdirs = []
            make_tree(lastnode, subdirs, clipped_path, item, itempath, files)

        request.session['common_path'] = files.common_path
        request.session['bundle_size'] = files.bundle_size
        request.session['bundle_size_str'] = file_tools.size_string(files.bundle_size)
        request.session.modified = True

        return return_bundle(request, tree, files.error_string)

    except Exception, ex:
        print_err(ex)
        return return_bundle(request, tree, 'get_bundle failed:  ' + ex.message)

def get_celery_process(request):
    try:
        id = request.session['upload_process']
        res = AsyncResult(id)
        return res
    except:
        return None

# pylint: disable=unused-argument
# justification: django required
def xxxget_state(request):
    """
    returns the status of the uploader
        logged_in
        uploading
        idle
    """

    upload_process = get_celery_process(request)

    state = 'idle'

    if upload_process:
        print upload_process.task_id
        res = AsyncResult(upload_process.task_id)
        if not res.ready():
            state += 'uploading'

    retval = json.dumps({'state': state})
    return HttpResponse(retval)

def get_status(upload_process):
    """    get status from backend    """

    if (TaskComm.USE_CELERY):
        if upload_process == None:
            return 'Initializing', ''

        state = upload_process.state
        result = upload_process.result
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

def set_uploading(request, value):
    request.session['is_uploading'] = value
    request.session.modified = True

def get_uploading(request):
    return request.session['is_uploading']

def incremental_status(request):
    """
    updates the status page with the current status of the background upload process
    """

    upload_process = None

    if TaskComm.USE_CELERY:
        upload_process = get_celery_process(request)
        if not upload_process:
            retval = json.dumps({'state': 'WAITING', 'result': 'waiting for upload to spin up'})
            return HttpResponse(retval)

    try:
        if request.POST:
            if upload_process:
                upload_process.revoke(terminate=True)
            state = 'CANCELLED'
            result = ''
            set_uploading(request, False)

            print state
        else:
            if not get_uploading(request):
                state = 'CANCELLED'
                result = ''
                retval = json.dumps({'state': state, 'result': result})
                return HttpResponse(retval)
        
        state, result = get_status(upload_process)

        if state is not None:
            if state == 'DONE':
                ingest_result = json.loads(result)
                job_id = ingest_result['job_id']
                print 'completed job ', job_id

                # create URL for status server
                result = configuration.status_server + str(job_id)

                set_uploading(request, False)

        # create json structure
        retval = json.dumps({'state': state, 'result': result})

        return HttpResponse(retval)

    except Exception, ex:
        print_err(ex)
        retval = json.dumps({'state': 'Status Error', 'result': ex.message})
        return HttpResponse(retval)
