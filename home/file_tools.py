"""
tools to bundle, parse file structures, etc.
"""

import os

# pylint: disable=too-few-public-methods
# justification: perfect amount of methods, possibly look at using "collection"

class FolderMeta(object):
    """
    meta data about a folder, including filecount, directory count, and the total bytes.
    """

    fileCount = 0
    dir_count = 0
    totalBytes = 0

    def __init__(self):
        pass


class FileManager(object):
    """description of class"""

    data_dir = ''
    bundle_filepath = ''
    bundle_size = 0
    bundle_size_str = ''

    common_path = ''
    archive_path = ''

    error_string = ''

    def cleanup_files(self):
        """
        resets a class to a clean state
        """

        self.bundle_filepath = ''
        self.bundle_size = 0
        self.bundle_size_str = ''
        self.common_path = ''

    def calculate_bundle_size(self, selected_paths):
        """
        totals up total size of the files in the bundle
        """
        total_size = 0

        self.error_string = ''

        for path in selected_paths:
            if self.accessible(path):
                if os.path.isfile(path):
                    total_size += os.path.getsize(path)
                if os.path.isdir(path):
                    total_size += self.folder_size(path)

        self.bundle_size = total_size
        self.bundle_size_str = size_string(total_size)

        return total_size

    def folder_size(self, folder):
        """
        recursively totals up total size of the files in the folder and sub folders
        """

        total_size = os.path.getsize(folder)
        for item in os.listdir(folder):
            itempath = os.path.join(folder, item)
            if self.accessible(itempath):
                if os.path.isfile(itempath):
                    total_size += os.path.getsize(itempath)
                elif os.path.isdir(itempath):
                    total_size += self.folder_size(itempath)

        return total_size

    def folder_meta(self, folder, meta):
        """
        gets the meta data for a folder
        number of folders
        number of files
        total size
        """

        meta.dir_count += 1

        for item in os.listdir(folder):
            itempath = os.path.join(folder, item)
            if self.accessible(itempath):
                if os.path.isfile(itempath):
                    meta.totalBytes += os.path.getsize(itempath)
                    meta.fileCount += 1
                elif os.path.isdir(itempath):
                    self.folder_meta(itempath, meta)

    def folder_meta_string(self, folder):
        """
        returns the meta data for a folder as a string to be displayed to the user
        """
        meta = FolderMeta()
        self.folder_meta(folder, meta)

        print '{0}|{1}'.format(str(meta.fileCount), str(meta.totalBytes))

        meta.dir_count -= 1
        meta_str = 'folders {0} | files {1} | {2}'.\
            format(str(meta.dir_count), str(meta.fileCount),
                   size_string(meta.totalBytes))

        return meta_str

    def get_archive_path(self, path):
        """
        build the archive path from the real path modified to conform to the archive structure
        """
        # remove the common root
        arc_path = os.path.relpath(path, self.common_path)
        # prepend the archive nodes
        arc_path = os.path.join(self.archive_path, arc_path)
        return arc_path

    def file_tuples_recursively(self, folder, tuple_list):
        """
        recursively gets file tuples for a folder
        """

        for item in os.listdir(folder):
            path = os.path.join(folder, item)
            if self.accessible(path):
                if os.path.isfile(path):
                    tuple_list.append((path, self.get_archive_path(path)))
                elif os.path.isdir(path):
                    self.file_tuples_recursively(path, tuple_list)

    def file_tuples(self, selected_list, tuple_list):
        """
        gets all the file tuples for a list of either folders or files
        tuples consist of the absolute path where the local file can be found
        and the relative path used to store the file in the archive
        """
        for path in selected_list:
            if self.accessible(path):
                if os.path.isfile(path):
                    tuple_list.append((path, self.get_archive_path(path)))
                elif os.path.isdir(path):
                    self.file_tuples_recursively(path, tuple_list)

    def upload_meta_string(self, folder):
        """
        returns the meta data for a folder as a string to be displayed to the user
        """
        meta = FolderMeta()
        self.folder_meta(folder, meta)

        print '{0}|{1}'.format(str(meta.fileCount), str(meta.totalBytes))

        meta.dir_count -= 1
        meta_str = 'folders {0} | files {1} | {2}'.\
            format(str(meta.dir_count), str(meta.fileCount),
                   size_string(meta.totalBytes))

        return meta_str

    def get_bundle_files(self, files):
        '''
        the common path will be clipped from the file archive structure,
        the archive structure will be added
        '''
        filtered = self.filter_selected_list(files)

        # create a list of tuples (filepath, arcpath)
        tuples = []
        self.file_tuples(filtered, tuples)

        self.calculate_bundle_size(files)

        return tuples

    def accessible(self, path):
        """
        os.access fails under certain situations so we wrote this POS
        """
        retval = True

        if os.path.islink(path):
            retval = False
        elif os.path.isfile(path):
            try:
                # this doesn't work, at least in windows.  A file may be readable
                # by _someone_ and this will return true, but fail on reading
                # if os.access(path, os.R_OK):
                #    size = os.path.getsize(path)
                # else:
                #    return false;
                with open(path) as temp_file:
                    temp_file.close()
            except Exception as ex:
                print ex
                retval = False

        elif os.path.isdir(path):
            try:
                os.listdir(path)
            except OSError:
                retval = False
        # we only support files and directories
        else:
            retval = False

        if not retval:
            self.error_string = 'Unaccessible files were skipped'

        return retval

    def get_size(self, start_path):
        """
        recursively add up the sizes of all files under a root dir
        """
        total_size = 0
        for parts in os.walk(start_path):
            dirpath = parts[0]
            filenames = parts[2]
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if self.accessible(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size

    def filter_selected_list(self, files):
        """
        remove filepaths that are contained in other filepaths
        to preclude redundant files when bundling
        """
        filtered = list(files)

        for test_path in files:
            if os.path.isdir(test_path):
                for i in xrange(len(filtered) - 1, -1, -1):
                    fpath = filtered[i]
                    if self.accessible(fpath):
                        if test_path in fpath and test_path != fpath:
                            filtered.remove(fpath)
                    else:
                        filtered.remove(fpath)
        return filtered


def size_string(total_size):
    """
    returns the upload size as a string with the appropriate units
    """

    # less than a Kb show b
    if total_size < 1024:
        return str(total_size) + " b"
    # less than an Mb show Kb
    if total_size < 1048576:
        kilobytes = float(total_size) / 1024.0
        return str(round(kilobytes, 2)) + " Kb"
    # less than a Gb show Mb
    elif total_size < 1073741824:
        megabytes = float(total_size) / 1048576.0
        return str(round(megabytes, 2)) + " Mb"
    # else show in Gb
    else:
        gigabytes = float(total_size) / 1073741824.0
        return str(round(gigabytes, 2)) + " Gb"
