from __future__ import absolute_import

from celery import shared_task, current_task

from bundler import bundle
from uploader import upload

from time import sleep

import sys

@shared_task
def uploadFiles(bundle_name = '', 
                   instrument_name = '', 
                   proposal = '', 
                   file_list=[], 
                   groups = [],
                   server='',
                   user='',
                   password=''
                   ):

    current_task.update_state("PROGRESS", meta={'Status': "Starting Bundle/Upload Process"})
        

    bundle(bundle_name = bundle_name, 
                   instrument_name = instrument_name,
                   proposal = proposal, 
                   file_list=file_list, 
                   recursive = False, 
                   verbose = True, 
                   groups = groups)    


    current_task.update_state(state="PROGRESS", meta={'Status': "Starting Upload"})
        
            
    res = upload(bundle_name=bundle_name,
                   protocol="https",
                   server=server,
                   user=user,
                   insecure=True,
                   password=password,
                   negotiate = False,
                   verbose=True
                   )

    print >> sys.stderr, "upload completed"

    current_task.update_state("PROGRESS", meta={'Status': "Completing Upload Process"})
            
    if "http" in res:
       print >> sys.stderr, "Status Page: %s" % res
       current_task.update_state(state='SUCCESS', meta={'url': res})
       return res
    else:
        return "Upload Failed"


