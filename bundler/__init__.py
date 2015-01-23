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
import zipfile
import tempfile
from glob import glob
from optparse import OptionParser

from celery import current_task


class Bundler_Error( Exception ):
    """
    A special exception class especially for the uploader module
    """

    def __init__( self, msg ):
        """
        Initializes a Bundler_error
        
        @param msg: A custom message packaged with the exception
        """
        self.msg = msg

    def __str__( self ):
        """
        Produces a string representation of an Bundler_Error
        """
        return "Bundler failed: %s" % self.msg



class File_Bundler:
    """
    An 'Abstract' Base Class that provide a template by which bundlers using
    specific formats/libraries shall be defined
    """

    def __init__( self, bundle_path, proposal_ID='', instrument_name='', instrument_ID='',
                  recursive=True, verbose=False, groups=None ):
        """
        Initializes a Bundler
        
        :Parameters:
            bundle_path
                The path to the target bundle file
            proposal_ID
                An optional string describing the proposal associated with this bundle
            instrument_name
                The name of the instrument that produced the data packaged in the bundle
            groups
                The type:name groups
            recursive
                If true, directories named in the file list will have their contents recursively added
            verbose
                Print out lots of status messages about the bundling process
        """
        if groups == None:
            groups = {}
        self.groups = groups
        self.bundle_path = os.path.abspath( bundle_path )
        ( self.bundle_dir, self.bundle_name ) = os.path.split( self.bundle_path )

        self.proposal_ID = proposal_ID
        self.instrument_name = instrument_name
        self.instrument_ID = instrument_ID
        self.hash_dict = {}

        self.recursive = recursive
        self.verbose = verbose



    def bundle_metadata( self ):
#FIXME handling of metadata file and 0 entry bundles"
        """
        Bundle in the metadata for the bundled files
        
        @note: This should be called after all of the files have been added (it will replace)
        """

        metadata = '{"version":"1.0.0","eusInfo":{'

        need_comma = False
        if self.proposal_ID != '':
            metadata += '"proposalID":"%s"' % self.proposal_ID
            need_comma = True

        if self.instrument_name != '':
            if self.proposal_ID != '':
                metadata += ', '
            metadata += '"instrumentName":"%s"' % self.instrument_name
            need_comma = True
            if self.instrument_ID != '':
                metadata += ', "instrumentId":"%s"' % self.instrument_ID
        if len(self.groups) > 0:
            if need_comma:
                metadata += ', '
            metadata += '"groups":['
            another_need_comma = False
            for (type, name) in self.groups.iteritems():
                if another_need_comma:
                    metadata += ', '
                metadata += "{\"name\":\"%s\", \"type\":\"%s\"}" %(name, type)
                another_need_comma = True
            metadata += ']'
            need_comma = True
        metadata += '},"file":[\n'

        # Add metadata for each file
        for ( file_arcname, file_hash ) in self.hash_dict.items():
            ( file_dir, file_name ) = os.path.split( file_arcname )
            metadata += '{"sha1Hash":"%s","fileName":"%s","destinationDirectory":"%s"},\n' % ( file_hash, file_name, file_dir )

        # Strip the trailing comma off of the end and close the string
        metadata = metadata[:-2] + "]}"

        if self.verbose:
            print >> sys.stderr, "Preparing Metadata:\n%s" % metadata

        self._bundle_metadata( metadata )



    def bundle_file( self, file_path, file_arcname ):
        """
        Bundle in a file or directory
        
        :Parameters:
            file_path
                The path to the file to bundle
            file_arcname
                An alternative name to use for the file inside of the bundle
        """

        file_path = os.path.abspath( file_path )

        if self.verbose:
            print >> sys.stderr, "Preparing to bundle %s" % file_path

        if file_path == self.bundle_path:
            if self.verbose:
                print >> sys.stderr, "Skipping bundle file %s" % file_path
            return
            
        # If the file_arcname argument is None use the base file name as the arc name
        if file_arcname == None:
            file_arcname = os.path.basename( file_path )

        if not os.path.exists( file_path ):
            raise Bundler_Error( "%s doesn't exist" % file_path )
        if not os.access( file_path, os.R_OK ):
            raise Bundler_Error( "Can't read from %s" % file_path )
        if 'metadata' in os.path.basename( file_path ):
            raise Bundler_Error( "A metadata file may not be explicitly added to the bundle" )

        file_mode = os.stat( file_path )[ stat.ST_MODE ]
        if not stat.S_ISDIR( file_mode ) and not stat.S_ISREG( file_mode ):
            raise Bundler_Error( "Unknown file type for %s" % file_path )

        # If the file is a directory and recursing is enabled, recursively add its children
        if stat.S_ISDIR( file_mode ):
            if self.recursive:
                if self.verbose:
                    print >> sys.stderr, "Recursing into subdirectory %s" % file_path
                for child in os.listdir( file_path ):
                    child_path = os.path.join( file_path, child )
                    child_arcname = os.path.join( file_arcname, child )
                    self.bundle_file( child_path, child_arcname )
            elif self.verbose:
                print >> sys.stderr, "Skipping subdirectory %s" % file_path
            return

        if self.verbose:
            print >> sys.stderr, "Generating hash %s" % file_path

        file_in = None
        try:
            file_in = open( file_path, 'r' )
        except IOError, err:
            raise Bundler_Error( "Couldn't read from file: %s" % file_path )

        h = hashlib.sha1()
        while True:
            data = file_in.read(1024 * 1024)
            if not data:
                break
            h.update( data )
        file_hash = h.hexdigest()
        file_in.close()

        if file_arcname in self.hash_dict:
            if hash != self.hash_dict[ file_arcname ]:
                raise Bundler_Error( "Different file with the same arcname is already in the bundle" )
            if self.verbose:
                print >> sys.stderr, "File already in bundle: %s.  Skipping" % file_path
            return
        self.hash_dict[ file_arcname ] = file_hash

        if self.verbose:
            print >> sys.stderr, "Bundling %s" % file_path
        self._bundle_file( file_path, file_arcname )



    def _bundle_metadata( self, metadata ):
        """
        A 'Pure Virtual' function that will perform the class specific metadata bundling in a child class
        
        @param metadata: The metadata string to bundle
        """
        raise Bundler_Error( "Can't bundle metadata with the base class" )



    def _bundle_file( self, file_name, file_arcname=None ):
        """
        A 'Pure Virtual' function that will perform the class specificg file bundling in a child class
        
        :Parameters:
            file_name
                The name of the file to bundle
            file_arcname
                An alternative name to use for the file inside of the bundle
        """
        raise Bundler_Error( "Can't bundle a file with the base class" )



class Tar_Bundler( File_Bundler ):
    """
    A Derived Class that bundles files in a tarfile format
    """

    def __init__( self, bundle_path, proposal_ID='', instrument_name='', instrument_ID='',
                  recursive=True, verbose=False, groups=None ):
        """
        Initializes a Tar_Bundler
        
        :Parameters:
            bundle_path
                The path to the target bundle file
            proposal_ID
                An optional string describing the proposal associated with this bundle
            instrument_name
                The name of the instrument that produced the data packaged in the bundle
            recursive
                If true, directories named in the file list will have their contents recursively added
            verbose
                Print out lots of status messages about the bundling process
        """


        if bundle_path == '' or bundle_path == None:
            bundle_path = 'bundle.tar'

        # Initialize the Base Bundler Class
        File_Bundler.__init__( self, bundle_path,
                               proposal_ID=proposal_ID, instrument_name=instrument_name, instrument_ID=instrument_ID,
                               recursive=recursive, verbose=verbose, groups=groups )

        try:
            tarball = tarfile.TarFile( name=self.bundle_path, mode='w' )
            tarball.close()
        except:
            raise Bundler_Error( "Couldn't create bundle tarball: %s" % self.bundle_path )

        self.empty_tar = True

        if self.verbose:
            print >> sys.stderr, "Successfully created tarfile bundle %s" % self.bundle_path

    def _bundle_file( self, file_path, file_arcname=None ):
        """
        Bundles files into a tarfile formatted bundle
        
        :Parameters:
            file_name
                The name of the file to bundle
            file_arcname
                An alternative name to use for the file inside of the bundle
        """

        if self.empty_tar:
            tarball = tarfile.TarFile( name=self.bundle_path, mode='w' )
            self.empty_tar = False
        else:
            tarball = tarfile.TarFile( name=self.bundle_path, mode='a' )

        tarball.add( file_path, arcname=file_arcname, recursive=False )
        tarball.close()

    def _bundle_metadata( self, metadata ):
        """
        Bundles the metadata into a tarfile formatted bundle
        
        @param metadata: The metadata string to bundle
        """
        
        print "Bundle meta!"
        print metadata

        metadata_file = None
        try:
            metadata_file = tempfile.TemporaryFile()
        except IOError:
            raise Bundler_Error( "Can't create metadata file in working directory" )

        metadata_file.write( metadata )
        metadata_file.seek( 0 )

        if self.empty_tar:
            tarball = tarfile.TarFile( name=self.bundle_path, mode='w' )
            self.empty_tar = False
        else:
            tarball = tarfile.TarFile( name=self.bundle_path, mode='a' )
        ti = tarfile.TarInfo( "metadata.txt" )
        ti.size = len( metadata )
        ti.mtime = time.time()
        tarball.addfile( ti, metadata_file )
        metadata_file.close()
        tarball.close()



class Zip_Bundler( File_Bundler ):
    """
    A Derived Class that bundles files in a zipfile format
    """

    def __init__( self, bundle_path, proposal_ID='', instrument_name='', instrument_ID='',
                  recursive=True, verbose=False, groups=None ):
        """
        Initializes a Zip_Bundler
        
        :Parameters:
            bundle_path
                The path to the target bundle file
            proposal_ID
                An optional string describing the proposal associated with this bundle
            instrument_name
                The name of the instrument that produced the data packaged in the bundle
            recursive
                If true, directories named in the file list will have their contents recursively added
            verbose
                Print out lots of status messages about the bundling process
        """

        if bundle_path == '' or bundle_path == None:
            bundle_path = 'bundle.zip'

        File_Bundler.__init__( self, bundle_path,
                               proposal_ID=proposal_ID, instrument_name=instrument_name, instrument_ID=instrument_ID,
                               recursive=recursive, verbose=verbose, groups=groups )

        zipper = zipfile.ZipFile( self.bundle_path, mode='w' )
        zipper.close()

        if self.verbose:
            print >> sys.stderr, "Successfully created zipfile bundle %s" % self.bundle_path



    def _bundle_file( self, file_path, file_arcname=None ):
        """
        Bundles files into a zipfile formatted bundle
        
        :Parameters:
            file_name
                The name of the file to bundle
            file_arcname
                An alternative name to use for the file inside of the bundle
        """

        zipper = zipfile.ZipFile( self.bundle_path, mode='a' )
        zipper.write( file_path, file_arcname )
        zipper.close()



    def _bundle_metadata( self, metadata ):
        """
        Bundles the metadata into a tarfile formatted bundle
        
        @param metadata: The metadata string to bundle
        """

        zipper = zipfile.ZipFile( self.bundle_path, mode='a' )
        zipper.writestr( "metadata.txt", metadata )
        zipper.close()

def _add_file_cb( option, opt, value, parser ):
    """
    A Callback function for an OptionParser that adds a file into the file list
    
    :Parameters:
        option
        opt
        value
            The filename that was passed to this callback
        parser
            The OptionParser that calls the callback
            
    @note: The file_list is a list of tuples formatted as [ (file_path, file_arcname) ... ]
    """

    # Try to expand the value argument using wildcards.
    if value[:1] != '/':
        value = os.path.abspath( os.path.join( parser.values.work_dir, value ) )
    file_glob = glob( value )
    
    # If the file doesn't exist, or the wildcards don't match any files, the glob will be empty
    if len( file_glob ) == 0:
        parser.error( "File argument resolved to 0 existing files: %s" % value )
                
    # Each entry in the file list is a tuple of the file's absolute path and the relative file name
    file_tuples = []
    abspath = os.path.abspath( parser.values.work_dir )
    for file_name in file_glob:
        if file_name[:1] != '/':
            file_name = os.path.abspath( os.path.join( parser.values.work_dir, file_name ) )
        altname = None
        lap = len( abspath )
        if file_name == abspath:
            altname = ""
        elif file_name[:lap+1] == "%s/" %(abspath):
            altname = file_name[lap+1:]
        file_tuples.append( ( file_name, altname ) )
        #logger.debug( "Abspath = %s" %( abspath ) )
        #logger.debug( "Adding file %s as %s" %( file_name, altname ) )
                       
    # If the glob has only one entry and an arcname argument was supplied, use it
    if len( file_glob ) == 1 and parser.values.alt_name != None:
        file_tuples[0] = ( file_tuples[0][0], parser.values.alt_name )
        
    # No matter what happens, the alt name is cleared
    parser.values.alt_name = None
    
    # Add the new file names to the parser's file name list
    parser.values.file_list.extend( file_tuples )
    
    

def add_usage( parser ):
    """
    Adds a custom usage description string for this module to an OptionParser
    """
    parser.set_usage( "usage: %prog [options] [-c DIR1 -f FILE1 -f FILE2 -c DIR2 -f FILE3]..." )

def _parser_add_group(option, opt, value, parser):
    (type, name) = value.split('=',1)
    parser.groups[type] = name

def add_options( parser ):
    """
    Adds custom command line options for this module to an OptionParser
    """
    parser.groups = {}

    # Set the directory in which to work
    parser.add_option( '-c', '--cwd', type='string', action='store', dest='work_dir', default=os.getcwd(),
                       help="Change the bundler's working directory to DIR", metavar='DIR' )

    # Set the file name for the bundle
    parser.add_option( '-b', '--bundle', type='string', action='store', dest='bundle_name', default='',
                       help="Set the name for the target bundle to NAME", metavar='NAME' )

    # Set the instrument to use
    parser.add_option( '-i', '--instrument', type='string', action='store', dest='instrument', default='',
                       help="Set used instrument to INST", metavar='INST' )

    # Set the name of the proposal
    parser.add_option( '-p', '--proposal', type='string', action='store', dest='proposal', default='',
                       help="Set the Proposal number number to PNUM", metavar='PNUM' )

    # Set the group-type/names
    parser.add_option( '-g', '--group', type='string', action='callback', callback=_parser_add_group,
                       help="Make files a member of the specified type=name group", metavar='T=N' )

    # Enable verbose output
    parser.add_option( '-v', '--verbose', dest='verbose', default=False, action='store_true',
                       help="Print detailed information for this run" )

    # Enable zipfile bundling
    parser.add_option( '-z', '--zip', dest='zip', default=False, action='store_true',
                       help="Bundle files in zip format ( tar is the default )" )

    # Set an alternative name for the file in the bundle
    parser.add_option( '-a', '--altname', type='string', action='store', dest='alt_name', default=None,
                       help="Use the alternative name NAME for the next file", metavar='NAME' )

    # Add a file to the list to be bundled
    parser.add_option( '-f', '--file', type='string', action='callback', callback=_add_file_cb,
                       dest='file_list', default=[],
                       help="Add the file or directory FILE to the list to be bundled", metavar='FILE' )
                       
    # Disable recursive directory bundling
    parser.add_option( '--nonrecursive', dest='recursive', default=True, action='store_false',
                       help="Disable recursive directory bundling" )

def check_options( parser, bundle_name_optional=False ):
    """
    Performs custom option checks for this module given an OptionParser
    """
    bundle_handle = None
    if bundle_name_optional:
        if parser.values.bundle_name == '':
            bundle_handle = tempfile.NamedTemporaryFile(mode='w+b')
            parser.values.bundle_name = bundle_handle.name
    else:
        if parser.values.bundle_name == '':
            print >> sys.stderr, "Failed to specify bundle name"
            sys.exit(0)
    return bundle_handle


def bundle( bundle_name='', instrument_name='chinook', tarfile=True, proposal='',
            file_list=[], recursive=True, verbose=False, groups=None ):
    """
    Bundles a list of files into a single aggregated bundle file
    
    :Parameters:
        bundle_name
            The target bundle file in which to aggregate the file list
        instrument_name
            The name of the instrument that produced the data files that will be bundled
        groups
            The a hash of type/name groups to attach to
        tarfile
            If true, tarfile format is used to bundle.  Otherwise zipfile format is used
        proposal
            An optional proposal ID to attach to the bundle
        file_list
            The list of files to bundle
        recursive
            If true, directories will be added to the bundle recursively
        verbose
            If true, lots of status messages about the bundling process will be printed to stderr
    """
    if bundle_name == None or bundle_name == '':
        if tarfile:
            bundle_name = 'bundle.tar'
        else:
            bundle_name = 'bundle.zip'

    if verbose:
        print >> sys.stderr, "Start bundling %s" % bundle_name

    # Set up the bundle file
    bundle_path = os.path.abspath( bundle_name )
    if verbose:
        print >> sys.stderr, "Bundle file set to %s" % bundle_path

    # set the instrument to use 
    instruments = { "chinook": 34076 }
    instrument_ID = instruments.get( instrument_name, '' )
    if verbose:
        print >> sys.stderr, "Instrument set to %s(%s)" % ( instrument_name, instrument_ID )

    # Set up the bundler object
    bundler = None
    if tarfile:
        bundler = Tar_Bundler( bundle_path, proposal_ID=proposal,
                               instrument_name=instrument_name, instrument_ID=instrument_ID,
                               recursive=recursive, verbose=verbose, groups=groups )
    else:
        bundler = Zip_Bundler( bundle_path, proposal_ID=proposal,
                               instrument_name=instrument_name, instrument_ID=instrument_ID,
                               recursive=recursive, verbose=verbose, groups=groups )

    # @todo:  determine if this is a good default behavior
    # If the file_list is empty bundle the current working directory
    if len( file_list ) == 0:
        file_list = [ ( os.
                       getcwd(), '' ) ]
    
    bundle_size = 0
    for ( file_path, file_arcname ) in file_list:
        bundle_size += os.path.getsize(file_path)      

    
    print >> sys.stderr, "bundle size %s" % str(bundle_size)

    fCount = len(file_list)
    index = 0
    running_size=0
    for ( file_path, file_arcname ) in file_list:
        try:
            index+=1
            running_size += os.path.getsize(file_path)
            percent_complete = 100.0 * running_size / bundle_size
            print >> sys.stderr, "percent complete %s" % str(percent_complete)
            bundler.bundle_file( file_path, file_arcname )
            #current_task.update_state(state='PROGRESS', meta={'info': "Bundling " + str(index), 'percent': percent_complete})
            current_task.update_state(state=str(percent_complete), meta={'Status': "Bundling percent complete: " + str(percent_complete)})
        except Bundler_Error, err:
            print >> sys.stderr, "Failed to bundle file: %s: %s" % ( file_path, err.msg )

    bundler.bundle_metadata()

    if verbose:
        print >> sys.stderr, "Finished bundling"

def bundle_from_options( parser ):
    """
    Bundle files based upon command line options supecified in an OptionParser
    """
    bundle( bundle_name=parser.values.bundle_name,
            instrument_name=parser.values.instrument,
            tarfile=(not parser.values.zip),
            proposal=parser.values.proposal,
            file_list=parser.values.file_list,
            recursive=parser.values.recursive,
            verbose=parser.values.verbose,
            groups=parser.groups
            )


def main():
    try:
        parser = OptionParser()
        add_usage( parser )
        add_options( parser )
        parser.parse_args()
        if parser.values.verbose:
            print >> sys.stderr, "Begining Bundling process"
        check_options( parser )
        bundle_from_options( parser )
        if parser.values.verbose:
            print >> sys.stderr, "Bundled %s successfully" % parser.values.bundle_name

    
    
    
    except Bundler_Error, err:
        print >> sys.stderr, "Bundler failed: %s" % err.msg


if __name__ == '__main__':
    main()
