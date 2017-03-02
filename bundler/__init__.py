#! /usr/bin/env python

"""
A Bundler module that aggregates files into a single bundle
"""
from __future__ import division

import sys
import stat
import time
import os.path
import hashlib
import tarfile
import tempfile
import json
import mimetypes
import datetime as DT

import traceback

from home.task_comm import task_error, TaskComm

class FileBundler(object):
    """
    An 'Abstract' Base Class that provide a template by which bundlers using
    specific formats/libraries shall be defined
    """

    def __init__(self, bundle_path):
        """
        Initializes a Bundler

        :Parameters:
            bundle_path
                The path to the target bundle file
        """
        self.bundle_path = os.path.abspath(bundle_path)

        self.file_meta = {}

        self.percent_complete = 0
        self.running_size = 0
        self.last_percent = 0
        self.bundle_size = 0

    def hash_file(self, file_path, file_arcname):
        """
        Bundle in a file or directory

        :Parameters:
            file_path
                The path to the file to bundle
            file_arcname
                An alternative name to use for the file inside of the bundle
        """

        file_path = os.path.abspath(file_path)

        # If the file_arcname argument is None use the base file name as the
        # arc name
        if file_arcname is None:
            file_arcname = os.path.basename(file_path)

        if not os.path.exists(file_path):
            task_error("%s doesn't exist" % file_path)
        if not os.access(file_path, os.R_OK):
            task_error("Can't read from %s" % file_path)

        file_mode = os.stat(file_path)[stat.ST_MODE]
        if not stat.S_ISDIR(file_mode) and not stat.S_ISREG(file_mode):
            task_error("Unknown file type for %s" % file_path)

        file_in = None
        try:
            # open to read binary.  This is important.
            file_in = open(file_path, 'rb')
        except IOError:
            task_error("Couldn't read from file: %s" % file_path)

        # hash file 1Mb at a time
        hashval = hashlib.sha1()
        while True:
            data = file_in.read(1024 * 1024)
            if not data:
                break
            hashval.update(data)

            # update file bundle status

            self.running_size += len(data)

            self.percent_complete = 100.0 * self.running_size / self.bundle_size

            # only update significant progress
            if self.percent_complete - self.last_percent > 1:
                self.report_percent_complete()
                self.last_percent = self.percent_complete

        file_hash = hashval.hexdigest()

        # print 'hash:  ' + file_hash
        file_in.close()

        modified_name = os.path.join('data', file_arcname)
        (file_dir, file_name) = os.path.split(modified_name)

        # linuxfy the directory
        file_dir = file_dir.replace('\\', '/')


        info = {}
        info['size'] = os.path.getsize(file_path)
        mime_type = mimetypes.guess_type(file_path, strict=True)[0]

        info['mimetype'] = mime_type if mime_type is not None else 'application/octet-stream'
        info['name'] = file_name
        info['mtime'] = DT.datetime.utcfromtimestamp(int(os.path.getmtime(file_path))).isoformat()
        info['ctime'] = DT.datetime.utcfromtimestamp(int(os.path.getctime(file_path))).isoformat()
        info['destinationTable'] = 'Files'
        info['subdir'] = file_dir
        info['hashsum'] = file_hash
        info['hashtype'] = 'sha1'

        # todo make sure errors bubble up without crashing
        if file_arcname in self.file_meta:
            print file_arcname
            task_error(
                "Different file with the same arcname is already in the bundle")
            return

        return info

    def report_percent_complete(self):
        """
        update the task state with the progress of the bundle
        """
        meta_str = 'Bundling percent complete: ' + \
            str(int(self.percent_complete))
        print meta_str

        TaskComm.set_state('PROGRESS', meta_str)


class TarBundler(FileBundler):
    """
    A Derived Class that bundles files in a tarfile format
    """

    def __init__(self, bundle_path):
        """
        Initializes a Tar_Bundler

        :Parameters:
            bundle_path
                The path to the target bundle file
        """

        if bundle_path == '' or bundle_path is None:
            task_error('no bundle path')

        # Initialize the Base Bundler Class
        FileBundler.__init__(self, bundle_path)

        tarball = tarfile.TarFile(name=self.bundle_path, mode='w')
        tarball.close()

        self.empty_tar = True

        print >> sys.stderr, "Successfully created tarfile bundle %s" % self.bundle_path

    def bundle_file(self, file_paths, bundle_size=0, meta_list=None):
        """
        Bundles files into a tarfile formatted bundle

        :Parameters:
            file_name
                The name of the file to bundle
            file_arcname
                An alternative name to use for the file inside of the bundle
        """

        if self.empty_tar:
            tarball = tarfile.TarFile(name=self.bundle_path, mode='w')
            self.empty_tar = False
        else:
            tarball = tarfile.TarFile(name=self.bundle_path, mode='a')

        self.running_size = 0
        self.last_percent = 0
        self.percent_complete = 0
        self.bundle_size = bundle_size

        self.report_percent_complete()

        for (file_path, file_arcname) in file_paths:
            # hash the file and store in hash_dict
            # percent complete is reported only as read and hashed
            # hopefully that being the slowest part and all we have
            # access to for completion statistics
            # file metadata is also built at this time
            meta = self.hash_file(file_path, file_arcname)
            meta_list.append(meta)

            # for version 1.2, push files to a data/ directory
            # to avoid collisions with metadata.txt in the root
            modified_arc_name = os.path.join('data', file_arcname)
            tarball.add(file_path, arcname=modified_arc_name,
                        recursive=False)

        tarball.close()

    def bundle_metadata(self, metadata):
        """
        Bundles the metadata into a tarfile formatted bundle

        @param metadata: The metadata string to bundle
        """

        metadata_file = None
        try:
            metadata_file = tempfile.NamedTemporaryFile(delete=False)
        except IOError:
            task_error('Cannot create metadata file in working directory')

        metadata_file.write(metadata)
        fname = metadata_file.name
        metadata_file.close()

        metadata_file = open(fname, mode='rb')

        # metadata_file.seek(0)

        if self.empty_tar:
            tarball = tarfile.TarFile(name=self.bundle_path, mode='w')
            self.empty_tar = False
        else:
            tarball = tarfile.TarFile(name=self.bundle_path, mode='a')

        try:
            tar_info = tarfile.TarInfo('metadata.txt')
            tar_info.size = len(metadata)
            tar_info.mtime = time.time()
            tarball.addfile(tar_info, metadata_file)
            metadata_file.close()
            tarball.close()
            os.remove(fname)
        except Exception, ex:
            print ex
            traceback.print_exc(file=sys.stdout)
            raise ex


def bundle(bundle_name='', file_list=None, bundle_size=0, meta_list=None):
    """
    Bundles a list of files into a single aggregated bundle file

    :Parameters:
        bundle_name
            The target bundle file in which to aggregate the file list
        file_list
            The list of files to bundle
        bundle_size
            total size of the files to be bundled
        meta_list
            list of metadata items.  File metadata will be added to this list
    """

    # validate parameters
    if bundle_name is None or bundle_name == '':
        task_error("Missing bundle name")

    if file_list is None or len(file_list) == 0:
        task_error("Missing file list")

    # Set up the bundle file
    bundle_path = os.path.abspath(bundle_name)

    # Set up the bundler object
    bundler = None

    bundler = TarBundler(bundle_path)

    bundler.bundle_file(file_list, bundle_size, meta_list)

    meta_str = json.dumps(meta_list)
    bundler.bundle_metadata(meta_str)

    #print >> sys.stderr, "Finished bundling"
    TaskComm.set_state('PROGRESS', "Bundling complete")


def main():
    """
    placeholder
    """

    print 'empty'

if __name__ == '__main__':
    main()
