from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import auth

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

import datetime

from urlparse import urlparse

import os
import platform
import sys
from django.contrib.auth.models import User
from mhlib import PATH

from bundler import bundle
from uploader import upload
from uploader import UploadBundle
from uploader import OpenSession
from uploader import TestAuth
from home.models import Filepath
from django.db.backends.oracle.creation import PASSWORD

rootDir = ""
user = ""
password = ""
selectedDirs = []
selectedFiles = []
directoryHistory = []

def currentDirectory(history):
    dir = ""
    for path in history:
        dir = os.path.join(dir , path)
        if (not path.endswith("/")):
            dir = dir + "/"
        
    return dir
        
    
#@login_required(login_url='/login/')
def list(request):
    
    global user
    print user
    
    global password
    if (password == ""):
        return render_to_response('home/login.html', context_instance=RequestContext(request))
 
    global selectedDirs
    global selectedFiles
    global directoryHistory
    
    rootDir = currentDirectory(directoryHistory)
    
    dataPath = Filepath.objects.get(name="dataRoot")
    
    if rootDir == "":
        if (dataPath is not None):
            rootDir = dataPath.fullpath
        elif ("Linux" in platform.platform(aliased=0, terse=0)):
            rootDir = '/home'
        else:
            rootDir = 'c:/'
        directoryHistory.append(rootDir)
        
    print currentDirectory(directoryHistory)
    
    checkedDirs = []
    uncheckedDirs = []
    checkedFiles  = []
    uncheckedFiles = []
    
    contents = os.listdir(rootDir)
    
    for path in contents:
        
        fullPath = os.path.join(rootDir , path)
        
        if (os.path.isdir(fullPath)):
            if (fullPath in selectedDirs):
                checkedDirs.append(path)
            else:
                uncheckedDirs.append(path)
        else: 
            if (fullPath in selectedFiles):
                checkedFiles.append(path)
            else:
                uncheckedFiles.append(path)
    
    # Render list page with the documents and the form
    return render_to_response(
        'home/uploader.html',
        {'directoryHistory': directoryHistory, 
         'checkedDirs': checkedDirs, 
         'uncheckedDirs': uncheckedDirs, 
         'checkedFiles': checkedFiles, 
         'uncheckedFiles': uncheckedFiles, 
         'selectedDirs': selectedDirs,
         'selectedFiles': selectedFiles},
        context_instance=RequestContext(request))
    
def modify(request):
    print 'modify ' + request.get_full_path()
    
    global selectedList
    global user
    global password
    global directoryHistory
    
    
    if request.POST:
        if (request.POST.get("Clear")):
            selectedList = []
            
        if (request.POST.get("upDir")):
            dir = os.path.dirname(rootDir)
            if (os.path.exists(dir)):
                rootDir = dir   
                
        if (request.POST.get("Select All")):
            contents = os.listdir(rootDir)  
            for path in contents:
                fullPath = os.path.join(rootDir , path)
                if (not os.path.isdir(fullPath)):
                    if (fullPath not in selectedList):
                        selectedList.append(fullPath)
                
        if (request.POST.get("Upload")):
            
            #create a list of tuples to meet the call format
            tupleList = []
            for path in selectedList:
                tupleList.append( ( path, None ) )
            
            current_time = datetime.datetime.now().time().strftime("%m.%d.%Y.%H.%M.%S")
            #current_date = datetime.datetime.now().date().strftime("%H.%M.%S")
            
            targetPath = Filepath.objects.get(name="target")
            if (targetPath is not None):
                targetDir = targetPath.fullpath
            else:
                targetDir = rootDir
            
            bundleName = os.path.join(targetDir, current_time + ".tar")
            
            print bundleName
            
            serverPath = Filepath.objects.get(name="server")
            if (serverPath is not None):
                sPath = serverPath.fullpath
            else:
                sPath = "dev1.my.emsl.pnl.gov"
                
            
            #return HttpResponseRedirect(reverse('home.views.list'))
            
            
            bundle(bundle_name = bundleName, 
                   instrument_name = "insty", 
                   tarfile = True, 
                   proposal = "45796", 
                   file_list=tupleList, 
                   recursive = False, 
                   verbose = True, 
                   groups = None)    
            
            """
            sesh = OpenSession(protocol="https",
                   server=sPath,
                   user="d3e889",
                   insecure=True,
                   password="12Freakin",
                   negotiate = False,
                   verbose=True
                   )
            
            boolVal = TestAuth(protocol="https",
                   server=sPath,
                   user="d3e889",
                   insecure=True,
                   password="12Freakin",
                   negotiate = False,
                   verbose=True
                   )
            
            res = UploadBundle( bundle_name=bundleName, session=sesh)
            """
            
            print user
            
            res = upload(bundle_name=bundleName,
                   protocol="https",
                   server=sPath,
                   user=user,
                   insecure=True,
                   password=password,
                   negotiate = False,
                   verbose=True
                   )
                   
            
            if "http" in res:
                return  HttpResponseRedirect(res)
            
        
    else:
        o = urlparse(request.get_full_path())
        params = o.query.split("=")
        modType = params[0]
        path = params[1]
                
        # spaces
        path = path.replace ("%20", " ")
        # backslash
        path = path.replace ("%5C", "\\")
        
        full = os.path.join(rootDir, path)
        
        if (modType == 'enterDir'):
            rootDir = os.path.join(rootDir, path)
            directoryHistory.append(path)
            print "rootDir = " + rootDir
            
        elif (modType == 'toggleFile'):
            if (full not in selectedFiles):
                selectedFiles.append(full) 
            else:
                selectedFiles.remove(full) 
                
        elif (modType == 'toggleDir'):
            if (full not in selectedDirs):
                selectedDirs.append(full) 
            else:
                selectedDirs.remove(full) 
    
    return HttpResponseRedirect(reverse('home.views.list'))

def Login(request):
    global password   
    global user 
    
    user = password = ''
    
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
                   verbose=True
                   )
            
        if (not auth):
            password = ""      
            """
            user = authenticate(username=name, password=pword)
            if user is not None:
                # the password verified for the user
                if user.is_active:
                    print("User is valid, active and authenticated")
                    login(request, user)
                    return HttpResponseRedirect(reverse('home.views.list'))
                else:
                    print("The password is valid, but the account has been disabled!")
            else: #create a new user and log them in  
                user = User.objects.create_user(username=name, email='', password=password)
                user.save()
                user = authenticate(username=name, password=password)
                login(request, user)
                print "created"
            """
            
        print "finally"
        return HttpResponseRedirect(reverse('home.views.list'))
    else:
        print "no Post"
        return render_to_response('home/login.html', context_instance=RequestContext(request))


    