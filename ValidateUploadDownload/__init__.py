
"""
A test module that compares original data to bundled and tarred data to downloaded data
testing to make sure that the hash for individual files all hash to the same value
"""
from __future__ import division

import sys
import stat
import time
import os.path
import hashlib


def hash_file(file_path):
    """
    Bundle in a file or directory

    :Parameters:
        file_path
            The path to the file to bundle
    """

    file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        return ("error %s doesn't exist" % file_path)

    file_in = None
    try:
        # open to read binary.  This is important.
        file_in = open(file_path, 'rb')
    except IOError:
        return ("error Couldn't read from file: %s" % file_path)

    # hash file 1Mb at a time
    hashval = hashlib.sha1()
    while True:
        data = file_in.read(1024 * 1024)
        if not data:
            break
        hashval.update(data)

    file_hash = hashval.hexdigest()

    print 'hash:  ' + file_hash
    file_in.close()

    return file_hash


def accessible(path):
    retval = True

    if "PaxHeader" in path:
        return False

    if os.path.islink(path):
        retval = False
    elif os.path.isfile(path):
        try:
            with open(path) as tempFile:
                tempFile.close()
        except Exception as e:
            retval = False
    elif os.path.isdir(path):
        try:
            os.listdir(path)
        except OSError:
            retval = False
    else:
        retval = False

    return retval


def file_list(start_path):
    """
    get all valid files in a directory
    """
    filelist = []
    for dirpath, dirnames, filenames in os.walk(start_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if (accessible(filepath)):
                filelist.append(filepath)
    return filelist


def main():
    updir = "E:\\InstrumentData\\test1"
    downdir = "E:\\InstrumentData\\download"
    tarfile = ""

    # load the file lists for upload and download directories
    upfiles = file_list(updir)
    downfiles = file_list(downdir)

    # if we have the same directory structure and files then
    # we should get the same relative file lists
    for i in range(len(upfiles)):
        if hash_file(upfiles[i]) == hash_file(downfiles[i]):
            print "matched:  " + upfiles[i]
        else:
            print "unmatched hash"
            print upfiles[i]
            print downfiles[i]
            break

    print "Complete"

if __name__ == '__main__':
    main()
