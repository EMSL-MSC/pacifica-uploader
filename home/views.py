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

# Module level variables
session = session_data.session_state()
version = '0.98.17'

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
    
    root_dir = session.data_dir

    if not root_dir or root_dir == '':
        return login_error(request, 'Data share is not configured')

    try:
        contents = os.listdir(root_dir)
    except Exception:
        return login_error(request, 'error accessing Data share')

    # validate that the currently selected bundle will fit in the target space
    files = []
    uploadEnabled = session.validate_space_available(files)

    message = 'Bundle: %s, Free: %s' % (session.files.bundle_size_str, session.free_size_str)
    if not uploadEnabled:
        message += ": Bundle exceeds free space"
    elif session.files.bundle_size==0:
        uploadEnabled = False

    variable_lookup = {
        'instrument' : "Selected Instrument",
        'user_list' : "User List", 'proposal' : "Proposal Name",
        'proposal_user' : "Proposal User",
        'data_root' : "Root Directory for Upload",
        'current_time' : "Upload Time", 'message' : "Message",
        
    }

    # Render list page with the documents and the form
    return render_to_response('home/uploader.html', \
        {'instrument': session.concatenated_instrument(),
         'proposalList': session.proposal_list,
         'user_list': session.proposal_users,
         'proposal':session.proposal_friendly,
         'proposal_user':session.proposal_user,
         'proposal_users':session.proposal_users,
         'data_root':session.data_dir,
         'metaList': session.meta_list,
         'current_time': session.current_time,
         'message': message,
         'uploadEnabled': uploadEnabled,
         'user': session.user_full_name,
         'value_lookup' : variable_lookup
        },
                              context_instance=RequestContext(request))

def show_initial_status(request):
    global session

    return show_status(request, session, "")

def show_status(request, session, message):
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
        return HttpResponse(json.dumps("Celery background process is not started"), content_type="application/json", status=500)

    packet = request.POST.get('packet')
    try:
        print "got packet"
        if (packet):
            json_obj = json.loads(packet)
            form = json_obj['form']
            files = json_obj['files']
        else:
            return
    except Exception, e:
        print e
        return

    # get the meta data values from the post
    for meta in session. meta_list:
        value = form[meta.name]
        if value:
            meta.value = value

    # get the selected proposal string from the post as it may not have been set in a previous post
    session.load_proposal(form['proposal'])
    session.load_proposal_user(form['proposal_user'])

    tuples = session.files.get_bundle_files(files, session.data_dir)

    # create the groups dictionary
    #{"groups":[{"name":"FOO1", "type":"Tag"}]}
    groups = {}
    for meta in session.meta_list:
        groups[meta.name] = meta.value

    insty = 'Instrument.%s' % (session.instrument)
    groups[insty] = session.instrument_friendly
    groups["EMSL User"] = session.proposal_user

    session.current_time = datetime.datetime.now().strftime("%m.%d.%Y.%H.%M.%S")

    session.bundle_filepath = os.path.join(session.target_dir, session.current_time + ".tar")

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

    return HttpResponse(json.dumps("success"), content_type="application/json")

def upload_files(request):
    print "upload!"
    return spin_off_upload(request, session)

def modify(request):
    """
    modifies the data underlying the main upload page depending on the request
    the main request catagories are:
        file sytem navigation
        selected list management
        upload request
    """

    global session

    if request.POST:

        print request.POST

        # todo make this jquery
        proposal = request.POST.get("proposal")
        if proposal:
            session.load_proposal(proposal)
            session.populate_proposal_users()

    return HttpResponseRedirect(reverse('home.views.populate_upload_page'))

"""
login and login related accesories
"""
#########################################################################################
def login_error(request, error_string):
    """
    returns to the login page with an error message
    """
    if not session.initialized:
        session.initialize_settings()

    return render_to_response(settings.LOGIN_VIEW, \
                              {'site_version':version, 'instrument': session.instrument, 'message': error_string}, context_instance=RequestContext(request))


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

    # initialize session settings from scratch
    session.initialized = False
    err = session.initialize_settings()
    if err != '':
        return login_error(request, 'faulty configuration:  ' + err)

    # timeout
    SESSION_COOKIE_AGE = session.timeout * 60

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

    
    # test to see if the user authorizes against EUS
    err_str = test_authorization(protocol="https",
                                    server=session.server_path,
                                    user=session.user,
                                    password=session.password)

    if err_str:
        return login_error(request, err_str)

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

    try:
        tasks.clean_target_directory(session.target_dir, session.server_path, session.current_user, session.password)
    except:
        return login_error(request, "failed to clear tar directory")

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

def get_proposal_users(request):
    global session

    prop = request.POST.get("proposal")
    session.load_proposal(prop)
    users = session.populate_proposal_users(session.proposal_id)
    retval = json.dumps(users)

    return HttpResponse(retval, content_type="application/json")


def get_children(request):
    try:
        retval = ""
        parent = request.GET.get("parent")

        if not parent:
            return ""

        list = []
        if os.path.isdir(parent):
            for item in os.listdir(parent):
                itempath = os.path.join(parent, item)
                
                if os.path.isfile(itempath):
                    list.append({"title": item, "key": itempath, "folder": False})
                elif os.path.isdir(itempath):
                    list.append({"title": item, "key": itempath, "folder": True, "lazy": True})
        retval = json.dumps(list)

    except Exception, e:
        print e
        return err_response("upload failed")

    return HttpResponse(retval)

def error_response(err_str):
    return HttpResponse(json.dumps("Error: " + err_str), content_type="application/json", status=500)


def make_leaf(title, path):
    ''' 
    return a populated tree leaf
    '''
    if os.path.isfile(path):
        size = os.path.getsize(path)
        is_folder = False
    elif os.path.isdir(path):
        size = session.files.get_size(path)
        is_folder = True

    size_string = session.files.size_string(size) 
    return {"title": title + " (" + size_string + ")", "key": path, "folder": is_folder, "data":{"size":size}}

def add_branch(branches, subdirectories, title, path):
    ''' 
    recursively insert branch into a tree structure
    '''
    # if we are at a leaf, add the leaf to the children list
    if len(subdirectories) < 2:
        leaf = make_leaf (title, path)
        branches.append(leaf)
        return

    branch_name = subdirectories[0]

    for branch in branches:
        if branch['title'] == branch_name:
            children = branch['children']
            add_branch(children, subdirectories[1:], title, path)
            return

    # not found, add the branch
    branch = {"title": branch_name, "key": 1, "folder": True, "expanded": True, "children": []}
    children = branch['children']
    add_branch(children, subdirectories[1:], title, path)
    branches.append (branch)

def make_tree (tree, subdirectories, partial_path, title, path):
    ''' 
    recursively split filepaths 
    '''

    if not partial_path:
        children = tree['children']
        add_branch(children, subdirectories, title, path)
        return

    head, tail = os.path.split (partial_path)

    # prepend the tail
    subdirectories.insert(0, tail)
    make_tree(tree, subdirectories, head, title, path)

def get_bundle(request):
    try:
        retval = ""
        pathstring = request.POST.get("packet")

        if not pathstring:
            return error_response("bad input to get_bundle")

        paths = json.loads(pathstring)

        if not paths:
            return error_response("bad input to get_bundle")

        # this actually should be done already by getting parent nodes
        filtered = session.files.filter_selected_list(paths)

        common_path = os.path.commonprefix(filtered)
        #get rid of dangling prefixes
        common_path, tail = os.path.split(common_path)
        common_path = os.path.join (common_path, '')

        tree = []

        tree.append ({"title": session.proposal_friendly, "key": 1, "folder": True,"expanded": True, "children": []})
        children = tree[0]['children']
        inst_node = {"title": session.instrument_friendly, "key": 1, "folder": True,"expanded": True, "children": []}
        children.append(inst_node)

        for itempath in paths:
            # title
            item = os.path.basename(itempath)

            # tree structure
            clipped_path = itempath.replace(common_path, '')
            subdirs = []
            make_tree(inst_node, subdirs, clipped_path, item, itempath)
                
        retval = json.dumps(tree)

    except Exception, e:
        print e
        return err_response("get_bundle failed")

    return HttpResponse(retval, content_type="application/json")
    
def incremental_status(request):
    """
    updates the status page with the current status of the background upload process
    """
    # pass pylint
    request = request

    global session

    if request.POST:
        if request.POST.get("Cancel Upload"):
            if session.bundle_process:
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

            #if we have successfully uploaded, cleanup the lists
            session.cleanup_upload()

            result = "https://%s/myemsl/status/index.php/status/view/j/%s" % (session.server_path, job_id)

    # create json structure
    retval = json.dumps({'state':state, 'result':result})

    return HttpResponse(retval)
