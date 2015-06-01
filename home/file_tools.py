import os

class FolderMeta(object):
    """
    meta data about a folder, including filecount, directory count, and the total bytes.
    """

    fileCount = 0
    dir_count = 0
    totalBytes = 0

    def __init__(self):
        pass

class file_manager(object):
    """description of class"""

    selected_dirs = []
    selected_files = []
    dir_sizes = []
    file_sizes = []
    directory_history = []

    bundle_filepath = ''
    bundle_size = 0
    bundle_size_str = ''

    def cleanup_files(self):
        """
        resets a class to a clean state
        """
        self.dir_sizes = []
        self.file_sizes = []
        self.selected_dirs = []
        self.selected_files = []

        self.bundle_filepath = ''
        self.bundle_size = 0
        self.bundle_size_str = ''

    def current_directory(self):
        """
        builds the current directory based on the navigation history
        """
        directory = ''
        for path in self.directory_history:
            directory = os.path.join(directory, path)

        return directory

    def undo_directory(self):
        index = len(self.directory_history) - 1
        del self.directory_history[index:]

    def calculate_bundle_size(self):
        """
        totals up total size of the files in the bundle
        """
        total_size = 0

        for file_path in self.selected_files:
            total_size += os.path.getsize(file_path)

        for folder in self.selected_dirs:
            total_size += self.folder_size(folder)

        self.bundle_size = total_size
        self.bundle_size_str = self.size_string(total_size)

        return total_size

    def folder_size(self, folder):
        """
        recursively totals up total size of the files in the folder and sub folders
        """

        total_size = os.path.getsize(folder)
        for item in os.listdir(folder):
            itempath = os.path.join(folder, item)
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
            format(str(meta.dir_count), str(meta.fileCount), self.size_string(meta.totalBytes))

        return meta_str

    def file_tuples_recursively(self, folder, tuple_list, root_dir):
        """
        recursively gets file tuples for a folder
        """

        #if we don't have access to this folder, bail
        if not os.access(folder, os.R_OK & os.X_OK):
            return

        for item in os.listdir(folder):
            path = os.path.join(folder, item)
            if os.path.isfile(path):
                if os.access(path, os.R_OK):
                    relative_path = os.path.relpath(path, root_dir)
                    tuple_list.append((path, relative_path))
            elif os.path.isdir(path):
                self.file_tuples_recursively(path, tuple_list, root_dir)

    def file_tuples(self, selected_list, tuple_list, root_dir):
        """
        gets all the file tuples for a list of either folders or files
        tuples consist of the absolute path where the local file can be found
        and the relative path used to store the file in the archive
        """
        for path in selected_list:
            if os.path.isfile(path):
                if os.access(path, os.R_OK):
                    # the relative path is the path without the root directory
                    relative_path = os.path.relpath(path, root_dir)
                    tuple_list.append((path, relative_path))
            elif os.path.isdir(path):
                self.file_tuples_recursively(path, tuple_list, root_dir)

    def size_string(self, total_size):
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

    def upload_meta_string(self, folder):
        """
        returns the meta data for a folder as a string to be displayed to the user
        """
        meta = FolderMeta()
        self.folder_meta(folder, meta)

        print '{0}|{1}'.format(str(meta.fileCount), str(meta.totalBytes))

        meta.dir_count -= 1
        meta_str = 'folders {0} | files {1} | {2}'.\
            format(str(meta.dir_count), str(meta.fileCount), size_string(meta.totalBytes))

        return meta_str

    def file_size_string(self, filename):
        """
        returns a string with the file size in appropriate units
        """

        total_size = os.path.getsize(filename)

        return self.size_string(total_size)

    def get_display_values(self):
        """
        sorts the contents of the current directory into checked
        or unchecked lists for display
        """

        checked_dirs = []
        unchecked_dirs = []
        checked_files = []
        unchecked_files = []
    
        root_dir = self.current_directory()
        contents = os.listdir(root_dir)

        # test the selected paths and directories to see if they will be shown 
        # checked or unchecked
        for path in contents:
            full_path = os.path.join(root_dir, path)

            if os.path.isdir(full_path):
                if full_path in self.selected_dirs:
                    checked_dirs.append(path)
                else:
                    unchecked_dirs.append(path)
            else:
                if full_path in self.selected_files:
                    checked_files.append(path)
                else:
                    unchecked_files.append(path)
        return (checked_dirs, unchecked_dirs, checked_files, unchecked_files)

    def get_bundle_files(self):
        # get the root directory
        root = self.directory_history[0]

        #create a list of tuples (filepath, arcpath)
        tuples = []
        self.file_tuples(self.selected_files, tuples, root)
        self.file_tuples(self.selected_dirs, tuples, root)
        return tuples

    def toggle_dir(self, fullpath):
        if fullpath not in self.selected_dirs:
            # test to see if we can get access
            try:
                files = os.listdir(fullpath)
                self.selected_dirs.append(fullpath)
                self.dir_sizes.append(self.folder_meta_string(fullpath))
            except Exception:
                return False
        else:
            index = self.selected_dirs.index(fullpath)
            self.selected_dirs.remove(fullpath)
            del self.dir_sizes[index]

        return True

    def toggle_file(self, fullpath):
        if fullpath not in self.selected_files:
            self.selected_files.append(fullpath)
            self.file_sizes.append(self.file_size_string(fullpath))
        else:
            index = self.selected_files.index(fullpath)
            self.selected_files.remove(fullpath)
            self.file_sizes[index]
