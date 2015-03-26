#!/usr/bin/python
#
# Example code for reading RRDs
# Contact: Jon Ludlam (jonathan.ludlam@eu.citrix.com)
#
# Mostly this script is taken from perfmon, by Alex Zeffert
#
import XenAPI, urllib, sys, os, shutil
from xml.dom import minidom
from xml.parsers.expat import ExpatError
import time
# Per VM dictionary (used by RRDUpdates to look up column numbers by variable names)
class VMReport(dict):
    """Used internally by RRDUpdates"""
    def __init__(self, uuid):
        self.uuid = uuid
# Per Host dictionary (used by RRDUpdates to look up column numbers by variable names)
class HostReport(dict):
    """Used internally by RRDUpdates"""
    def __init__(self, uuid):
        self.uuid = uuid
class RRDUpdates:
    """ Object used to get and parse the output the http://localhost/rrd_udpates?...
    """
    def __init__(self, sample_secs, sample_ints):
        # params are what get passed to the CGI executable in the URL
        self.params = dict()
        self.params['start'] = int(time.time()) - sample_secs # For demo purposes!
        self.params['host'] = 'true'   # include data for host (as well as for VMs)
        self.params['cf'] = 'AVERAGE'  # consolidation function, each sample averages 12 from the 5 second RRD
        self.params['interval'] = sample_ints
    def get_nrows(self):
        return self.rows
    def get_vm_list(self):
        return self.vm_reports.keys()
    def get_vm_param_list(self, uuid):
        report = self.vm_reports[uuid]
        if not report:
            return []
        return report.keys()
    def get_vm_data(self, uuid, param, row):
        report = self.vm_reports[uuid]
        col = report[param]
        return self.__lookup_data(col, row)
    def get_host_uuid(self):
        report = self.host_report
        if not report:
            return None
        return report.uuid
    def get_host_param_list(self):
        report = self.host_report
        if not report:
            return []
        return report.keys()
    def get_host_data(self, param, row):
        report = self.host_report
        col = report[param]
        return self.__lookup_data(col, row)
    def get_row_time(self,row):
        return self.__lookup_timestamp(row)
    # extract float from value (<v>) node by col,row
    def __lookup_data(self, col, row):
        # Note: the <rows> nodes are in reverse chronological order, and comprise
        # a timestamp <t> node, followed by self.columns data <v> nodes
        node = self.data_node.childNodes[self.rows - 1 - row].childNodes[col+1]
        return float(node.firstChild.toxml()) # node.firstChild should have nodeType TEXT_NODE
    # extract int from value (<t>) node by row
    def __lookup_timestamp(self, row):
        # Note: the <rows> nodes are in reverse chronological order, and comprise
        # a timestamp <t> node, followed by self.columns data <v> nodes
        node = self.data_node.childNodes[self.rows - 1 - row].childNodes[0]
        return int(node.firstChild.toxml()) # node.firstChild should have nodeType TEXT_NODE
    def refresh(self, session, url, override_params = {}):
        params = override_params
        params['session_id'] = session.handle
        params.update(self.params)
        paramstr = "&".join(["%s=%s"  % (k,params[k]) for k in params])
        # this is better than urllib.urlopen() as it raises an Exception on http 401 'Unauthorised' error
        # rather than drop into interactive mode
        print url + "/rrd_updates?%s" % paramstr
        sock = urllib.URLopener().open(url + "/rrd_updates?%s" % paramstr)
        xmlsource = sock.read()
        sock.close()
        xmldoc = minidom.parseString(xmlsource)
        self.__parse_xmldoc(xmldoc)
        # Update the time used on the next run
        self.params['start'] = self.end_time + 1 # avoid retrieving same data twice
    def __parse_xmldoc(self, xmldoc):
        # The 1st node contains meta data (description of the data)
        # The 2nd node contains the data
        self.meta_node = xmldoc.firstChild.childNodes[0]
        self.data_node = xmldoc.firstChild.childNodes[1]
        def lookup_metadata_bytag(name):
            return int (self.meta_node.getElementsByTagName(name)[0].firstChild.toxml())
        # rows = number of samples per variable
        # columns = number of variables
        self.rows = lookup_metadata_bytag('rows')
        self.columns = lookup_metadata_bytag('columns')
        # These indicate the period covered by the data
        self.start_time = lookup_metadata_bytag('start')
        self.step_time  = lookup_metadata_bytag('step')
        self.end_time   = lookup_metadata_bytag('end')
        # the <legend> Node describes the variables
        self.legend = self.meta_node.getElementsByTagName('legend')[0]
        # vm_reports matches uuid to per VM report
        self.vm_reports = {}
        # There is just one host_report and its uuid should not change!
        self.host_report = None
        # Handle each column.  (I.e. each variable)
        for col in range(self.columns):
            self.__handle_col(col)
    def __handle_col(self, col):
        # work out how to interpret col from the legend
        col_meta_data = self.legend.childNodes[col].firstChild.toxml()
        # vm_or_host will be 'vm' or 'host'.  Note that the Control domain counts as a VM!
        (cf, vm_or_host, uuid, param) = col_meta_data.split(':')
        if vm_or_host == 'vm':
            # Create a report for this VM if it doesn't exist
            if not self.vm_reports.has_key(uuid):
                self.vm_reports[uuid] = VMReport(uuid)
            # Update the VMReport with the col data and meta data
            vm_report = self.vm_reports[uuid]
            vm_report[param] = col
        elif vm_or_host == 'host':
            # Create a report for the host if it doesn't exist
            if not self.host_report:
                self.host_report = HostReport(uuid)
            elif self.host_report.uuid != uuid:
                raise PerfMonException, "Host UUID changed: (was %s, is %s)" % (self.host_report.uuid, uuid)
            # Update the HostReport with the col data and meta data
            self.host_report[param] = col
        else:
            raise PerfMonException, "Invalid string in <legend>: %s" % col_meta_data
            
def main(url, username, password, smpl_time, smpl_intv):
    session = XenAPI.Session(url)
    session.xenapi.login_with_password(username, password)
    rrd_updates = RRDUpdates(smpl_time, smpl_intv)
    rrd_updates.refresh(session, url, {})

    if not os.path.exists('result'):
        os.makedirs('result')

    for uuid in rrd_updates.get_vm_list():
        print "Got values for VM: "+uuid
          
        if not os.path.exists('result/' + uuid):
            os.makedirs(os.path.join("result", uuid))
        for param in rrd_updates.get_vm_param_list(uuid):
            print param
            if not (("cpu" in param) or ("rx" in param) or ("tx" in param) or ("eth0" in param)):
                continue
            path = 'result/' + uuid
            filename = param + ".data"

            # if data file for the parameter doesn't exist
            if not os.path.isfile(path + "/" + filename):
                f = open(os.path.join(path, filename),'w')
                print "param: "+param
                data=""
                for row in range(rrd_updates.get_nrows()):
                    data=data+"%d %.2f\n" % (rrd_updates.get_row_time(row) - rrd_updates.get_row_time(0),
                                            rrd_updates.get_vm_data(uuid,param,row))
                #f.write('# param: time(s) ' + param + '\n' + data)
                f.write(data)

            # if data file exists
            else:
                f = open(os.path.join(path, filename),'r')
                fdata = f.readlines()
                f.close()
                
                f = open(os.path.join(path, filename),'w')
                for row in range(rrd_updates.get_nrows()):
                    if row == 0:
                        data = "" #fdata[0]
                    else:
                        try:
                            data = data + fdata[row].rstrip() + " %.2f\n" % rrd_updates.get_vm_data(uuid,param,row)
                        except IndexError:
                            data = data
                f.write(data)

            f.close()
            
if __name__ == "__main__":
    if len(sys.argv) < 6:
        print "Usage:"
        print sys.argv[0], "<url> <username> <password> <sample time> <sample interval> <run number>"
        sys.exit(1)
    url = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    smpl_time = sys.argv[4]
    smpl_intv = sys.argv[5]

    main(url, username, password, int(smpl_time), int(smpl_intv))
