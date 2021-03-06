#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The downloader code downloads MODIS datasets from NASA's website.
"""

import ftplib
import time
import os
import logging

class InvalidPlatform(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr (self.value)
            


class InvalidProduct(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr (self.value)

log = logging.getLogger('main-log')

class downloader:
    """
    A downloader class
    """
    def __init__ ( self, tile, output_dir="/data/geospatial_12/users/", \
                    collection="005" ):
        """
        For some reason, I put something about the collection there, which is not
        yeat in the database.
        """

        self.ftp_host = "e4ftl01u.ecs.nasa.gov"
        self.collection = collection
        self.tile = tile
        self.output_dir = os.path.join ( output_dir, os.environ['USER'], "MODIS" )
        if not os.path.exists ( self.output_dir ):
            try:
                log.info ( "Making output dir in %s" % self.output_dir )
                os.mkdir ( self.output_dir )
            except IOError:
                log.info ( "Can't write to %s" % self.output_dir )
                log.info ( "Will attempt /home/%s/Data/MODIS/" % \
                            os.environ ['USER']  )
                self.output_dir = "/home/%s/Data/MODIS/" % os.environ['USER']
                os.makedirs ( self.output_dir )
        

    def __ftp_connect ( self ):
        log.info ( "Connecting to remote FTP server..." )
        try:
            self.ftp = ftplib.FTP ( self.ftp_host )
            #self.ftp.set_debuglevel(2)
            self.ftp.login ( )
        except:
            log.exception ( "Cannot connect to FTP host %s" % self.ftp_host )
    def __del__ ( self ):
        #close FtP connection and be nice.
        
        try:
            self.ftp.close()
            log.info ( "Shutting down and closing down FTP session" )
        except AttributeError:
            pass
            
    def get_list ( self, product_name, start_date, platform, end_date=None ):
        """
        Getting a listing of the available products.
        """
        self.platform = platform
        self.product = product_name

        log.info ( "Getting list of available products on remote server" )
        (ftp_dir, get_dates ) = self.__navigate_ftp ( \
                            product_name, start_date, platform, \
                            end_date=end_date )
        return ( ftp_dir, get_dates )
        
    def __navigate_ftp ( self, product_name, start_date, platform, \
                        end_date=None ):
        """
        This is the method traverses NASA's FTP directory, selecting what
        files to download, in terms of tile, start and end date.

        :parameter product_name: The product shortname, for example MOD09GA.
        :parameter start_date: The starting date (2001.05.18, for example).
        :parameter platform: Not really needed, but one of "TERRA", "AQUA"
                             or "COMBINED".
        :parameter end_date: Optional end date. Otherwise, all data older than
                             start_date is returned.
        """
        platform_dir = {"TERRA":"/MOLT/", "AQUA":"/MOLA/", \
                        "COMBINED":"/MOTA/"}

        if not platform_dir.has_key(platform):
            raise InvalidPlatform, "Your platform was %s" % platform
        # Parse the start date to match FTP dir structure
        parsed_start_date = time.strptime(start_date, "%Y.%m.%d" )
        if end_date != None:
            parsed_end_date = time.strptime( end_date, "%Y.%m.%d" )
        # Change dir to product directory
        try:
            self.ftp.cwd ("/%s/%s.%s/" % ( platform_dir[platform], \
                            product_name, self.collection ))
        except ftplib.error_perm:
            raise InvalidProduct, "This product doesn't seem to exist?"
        except AttributeError:
            # Not connected to the ftp server
            self.__ftp_connect ()
            self.ftp.cwd ("/%s/%s.%s/" % ( platform_dir[platform], \
                product_name, self.collection ))
        ftp_dir = "/%s/%s.%s/" % ( platform_dir[platform], \
                                product_name, self.collection )
        # Now, get all the available dates (they are subdirs, so need
        # to parse return string).
        dates = []
        def parse(line):
            if line[0] == 'd':
                dates.append(line.rpartition(' ')[2])

        self.ftp.dir( parse )
        dates.sort()
        # Dates are here now.
        # Discard dates prior to start_date parameter...
        Dates = [ time.strptime(d, "%Y.%m.%d") for d in dates ]

        dstart = -399.
        for i in xrange(len(Dates)):
            if Dates[i][0] == parsed_start_date[0]: # Same year!
                d = Dates[i][7] - parsed_start_date[7] # DoY difference
                if d < 0 and d > dstart:
                    dstart = d
                    istart = i
                elif d == 0:
                    istart = i
                    break
        
            
        # Do the same if we have an end date
        
        if end_date != None:
            dstart = 300.
            for i in xrange(len(Dates)):
                if Dates[i][0] == parsed_end_date[0]:
                    d = Dates[i][7] - parsed_end_date[7]
                    if d > 0 and d < dstart:
                        dstart = d
                        iend = i
                    elif d == 0:
                        iend = i
                        break
            get_dates = dates[istart:(iend+1)]
        else:
            get_dates = list ( dates[istart] )
        #print get_dates, parsed_start_date, parsed_end_date
        return ( ftp_dir, get_dates )

    def get_product ( self, product_name, start_date, platform, \
                        end_date=None):
        """
        This is the method that does the downloading of a prdouct
        """

        # First, navigate FTP tree and get products
        log.info ( "Start downloading products %s(%s) from %s to %s" % \
            ( product_name, platform, start_date, end_date ) )
        ( ftp_dir, get_dates ) = self.__navigate_ftp ( \
                            product_name, start_date, platform, \
                            end_date=end_date )
        #except:
            #raise ValueError, "Some error occurred in __navigate_ftp!"
        
        out_dir = os.path.join ( self.output_dir, platform, product_name, \
                                self.tile )
        if not os.path.exists ( out_dir ):
            os.makedirs ( out_dir )
        output_files = []
        
        for fecha in get_dates:
            # For each date, cd into that dir, and grab all files.
            try:
                self.ftp.cwd ( "%s/%s"%(ftp_dir, fecha) )
            except ftplib.error_perm:
                continue
            except AttributeError:
                # Not connected to the ftp server
                self.__ftp_connect ()
                self.ftp.cwd ( "%s/%s"%(ftp_dir, fecha) )
            fichs = []
            self.ftp.dir ( fichs.append )
            # Now, only consider the ones for the tile we want.
            grab0 = [ f for f in fichs if f.find( self.tile ) >= 0 ]
            for grab_file in grab0:
                fname = grab_file.split()[7]
                f_out = open( os.path.join ( out_dir, fname), 'w')
                output_files.append ( os.path.join ( out_dir, fname) )

                # Download the file a chunk at a time
                # Each chunk is sent to handleDownload
                # RETR is an FTP command

                #
                def handle_download(block):
                    f_out.write(block)
                    f_out.flush()
                log.info ( "Starting download of %s" % fname )
                log.info (  "\tSaving to %s" % os.path.join ( out_dir, fname) )
                self.ftp.retrbinary('RETR ' + fname, handle_download )

                f_out.close()
                log.info ( "\tDone!" )
        return output_files

    def download_product ( self, ftp_dir, get_date):
        """
        This is the method that does the downloading of a prdouct
        """
        log.info ( "Downloading product %s(%s) for tile %s, %s" % ( self.product, \
            self.platform, self.tile, get_date ) )
        out_dir = os.path.join ( self.output_dir,self.platform, self.product, \
                                self.tile )
        
        if not os.path.exists ( out_dir ):
            os.makedirs ( out_dir )
        output_files = []
        
        # For each date, cd into that dir, and grab all files.
        try:
            self.ftp.cwd ( "%s/%s"%(ftp_dir, get_date) )
        except ftplib.error_perm:
            raise ValueError, "Can't change dir to %s/%s"%(ftp_dir, get_date)
        except AttributeError:
            # Not connected to the ftp server
            self.__ftp_connect ()
            self.ftp.cwd ( "%s/%s"%(ftp_dir, get_date) )
        except ftplib.error_temp:
            # Time out?
            # Not connected to the ftp server
            log.info("Reconnecting....")
            self.__ftp_connect ()
            self.ftp.cwd ( "%s/%s"%(ftp_dir, get_date) )
        fichs = []
        self.ftp.dir ( fichs.append )
        # Now, only consider the ones for the tile we want.
        grab0 = [ f for f in fichs if f.find( self.tile ) >= 0 ]
        
        for grab_file in grab0:
            fname = grab_file.split()[7]
            f_out = open( os.path.join ( out_dir, fname), 'w')
            output_files.append ( os.path.join ( out_dir, fname) )

            # Download the file a chunk at a time
            # Each chunk is sent to handleDownload
            # RETR is an FTP command

            #
            def handle_download(block):
                f_out.write(block)
                f_out.flush()
            log.info ( "Starting download of %s" % fname )
            log.info ( "\tSaving to %s" % os.path.join ( out_dir, fname) )
            try:
                self.ftp.retrbinary('RETR ' + fname, handle_download )
            except ftplib.error_perm:
                # File doesn't exist. Return a None
                return None

            f_out.close()
            log.info ( "\tDone!" )
        return output_files