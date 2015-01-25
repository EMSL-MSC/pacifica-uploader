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

def bundle( bundle_name='', instrument_name='chinook', proposal='',
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
        bundle_name = 'bundle.tar'

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
    bundler = Tar_Bundler( bundle_path, proposal_ID=proposal,
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

def main():
    print 'empty'

if __name__ == '__main__':
    main()
