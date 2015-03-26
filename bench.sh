#!/bin/bash

ERR='\033[31m[ERROR]\033[0m'
WRN='\033[33m[WARNING]\033[0m'
INF='\033[34m[INFO]\033[0m'

set -ex

echo -e "${WRN} Have you properly set all the required information such as IPs, MACs, and ports?"

# install weighttp

if [ "$#" -lt 3 ]; then
   echo -e "${ERR} syntax: bench <XenServer password> <traffgen password> <A's IP> <B's IP> <C's IP>"
   exit
fi

XS1="128.243.27.99"
XS2="128.243.27.93"

# for both the servers
PASSWORD=$1

# auto-extract some of the info by xapi
BPORT="6"

# A = 128.243.27.24
AMAC="aa:aa:aa:aa:aa:aa"
# B = 128.243.27.95
BMAC="c6:b3:c9:60:42:c8"
# C = 128.243.20.86
CMAC="cc:cc:cc:cc:cc:cc"

TGENIP="128.243.20.67"
TGENUSER="m"
TGENPASS=$2

A=$3 && B=$4 && C=$5


# performance test time in seconds
TIME=120

XENSERVER="sshpass -p $PASSWORD ssh -oStrictHostKeyChecking=no -l root $XS1"
XENSERVER2="sshpass -p $PASSWORD ssh -oStrictHostKeyChecking=no -l root $XS2"
TGEN="sshpass -p $TGENPASS ssh -oStrictHostKeyChecking=no -l $TGENUSER $TGENIP"

rm -rf result
rm -rf graphs-A
rm -rf graphs-A-B
rm -rf graphs-A-C

echo -e "${INF} regression test on host A"

#:<<'END'
source ./traffic.sh 3
bash ./graph.sh "A"
#END

if [ -z "$B" ]; then
  echo -e "${WRN} No backup server B is provided."
  exit
fi

sleep 10

rm -rf result

# add flows
$XENSERVER "ovs-ofctl add-flow xenbr0 dl_type=0x0800,nw_src=${TGENIP},actions=mod_dl_dst:${BMAC},mod_nw_dst:${B},output:${BPORT}"
$XENSERVER "ovs-ofctl add-flow xenbr0 dl_type=0x0800,nw_src=${B},actions=mod_dl_src:${AMAC},mod_nw_src:${A},output:1"

echo -e "${INF} regression test with load balancing on hosts A and B"

#:<<'END'
source ./traffic.sh 3
bash ./graph.sh "A-B"
#END

# remove added flows
$XENSERVER "ovs-ofctl del-flows xenbr0 dl_type=0x0800,nw_src=${TGENIP}"
$XENSERVER "ovs-ofctl del-flows xenbr0 dl_type=0x0800,nw_src=${B}"

if [ -z "$C" ]; then
  echo -e "${WRN} No external backup server C is provided."
  exit
fi

sleep 10

rm -rf result

# add flows
$XENSERVER "ovs-ofctl add-flow xenbr0 dl_type=0x0800,nw_src=${TGENIP},nw_dst=${A},actions=mod_dl_dst:${CMAC},mod_nw_dst:${C},mod_dl_src:${AMAC},in_port"
$XENSERVER2 "ovs-ofctl add-flow xenbr0 dl_type=0x0800,nw_dst=${TGENIP},nw_src=${C},actions=mod_nw_src:${A},output:1"

echo -e "${INF} regression test with load balancing on hosts A and C"

#:<<'END'
source ./traffic.sh 3
bash ./graph.sh "A-C"
#END

sleep 10

# remove added flows
$XENSERVER "ovs-ofctl del-flows xenbr0 dl_type=0x0800,nw_src=${TGENIP},nw_dst=${A}"
$XENSERVER2 "ovs-ofctl del-flows xenbr0 dl_type=0x0800,nw_dst=${TGENIP},nw_src=${C}"


