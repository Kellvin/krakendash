from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.conf import settings
from django.core.files.temp import NamedTemporaryFile
from cephclient import wrapper

import requests
import re
import json
import subprocess

URLS = settings.CEPH_URLS
get_data = wrapper.CephWrapper(endpoint = 'http://localhost:5000/api/v0.1/')

''' the main request builder '''
def req(url):
  headers = {'Accept': 'application/json' }
  timeout = 10
  r = requests.get(url, headers=headers, timeout=timeout)
  response_json = r.text
  return response_json

''' Cluster collection methods '''

def newmain(request):

  ''' overall cluster health '''
  cresp, cluster_health = get_data.get_health(body = 'json')

  ''' mons '''
  mresp, mon_status = get_data.mon_status(body = 'json')
  mon_count = len(mon_status['output']['monmap']['mons'])

  ''' get a rough estimate of cluster free space. this is not accurate '''
  presp, pg_stat = get_data.pg_stat(body = 'json')
  kb_used = pg_stat['output']['osd_stats_sum']['kb_used'] / 1024 / 1024
  kb_avail = pg_stat['output']['osd_stats_sum']['kb_avail'] / 1024 / 1024
  gb_used = kb_used / kb_avail

  ''' pgs '''
  pg_resp, pg_status = get_data.get_status( body = 'json')
  pg_statuses = pg_status['output']['pgmap']

  pg_ok = 0
  pg_warn = 0
  pg_crit = 0

  ''' pg states '''
  pg_warn_status = re.compile("(creating|degraded|replay|splitting|scrubbing|peering|repair|recovering|backfill|wait-backfill|remapped)")
  pg_crit_status = re.compile("(down|inconsistent|incomplete|stale)")

  for state in pg_statuses['pgs_by_state']:

    if state['state_name'] == "active+clean":
      pg_ok = pg_ok + state['count']

    elif pg_warn_status.search(state['state_name']):
      pg_warn = pg_warn + state['count']

    elif pg_crit_status.search(state['state_name']):
      pg_crit = pg_crit + state['count']



  ''' osds '''
  oresp, osd_status = get_data.osd_stat(body = 'json')
  dresp, osd_dump = get_data.osd_dump(body = 'json')
  osd_state = osd_dump['output']['osds']

  return render_to_response('newmain.html', locals())


def cluster_health(request):

  disk_free = json.loads(req(URLS['disk_free']))
  cluster_health = json.loads(req(URLS['cluster_health']))
  return render_to_response('cluster_health.html', locals())

def monitor_status(request):

  response, body = get_data.mon_status(body = 'json')
  monitor_status =body
  return render_to_response('monitor_status.html', locals())

def osd_list(request):

  osd_list = json.loads(req(URLS['osd_listids']))
  return render_to_response('osd_list.html', locals())

def osd_details(request, osd_num):

  osd_num = int(osd_num)
  osd_details = json.loads(req(URLS['osd_details']))
  osd_disk_details = osd_details['output']['osds'][osd_num]
  osd_perf = json.loads(req(URLS['osd_perf']))
  osd_disk_perf = osd_perf['output']['osd_perf_infos'][osd_num]
  return render_to_response('osd_details.html', locals())

def osd_map_summary(request):

  return HttpResponse(req(URLS['osd_map_summary']))

def osd_listids(request):

  return HttpResponse(req(URLS['osd_listids']))

def pools(request):

  pools = json.loads(req(URLS['pools']))
  return render_to_response('pools.html', locals())

def pool_detail(request, pool):

  pool = pool
  pg_details = json.loads(req(URLS['pool_details'] + pool))
  pool_id = pg_details['output']['pool_id']
  pool_details_dump = json.loads(req(URLS['pool_details_dump']))
  return render_to_response('pool_detail.html', locals())

def osd_tree(request):

  return HttpResponse(req(URLS['osd_tree']))

def pg_status(request):

  pg_status = json.loads(req(URLS['pg_status']))
  return render_to_response('pg_status.html', locals())

def pg_osd_map(request, pgid):

  pg_url = "http://localhost:5000/api/v0.1/pg/dump?dumpcontents=pgs_brief"
  pg_osd_map = json.loads(req(pg_url))
  return render_to_response('pg_osd_map.html', locals())

def crush_rules(request):

  crush_rules = json.loads(req(URLS['crush_rule_dump']))
  return render_to_response('crush_rules.html', locals())

def crushmap(request):

  r = requests.get('http://localhost:5000/api/v0.1/osd/getcrushmap')
  myfile = NamedTemporaryFile(delete=False)
  myfile.write(r.content)
  map = subprocess.call(['/usr/bin/crushtool -d', '%s']) % (myfile.name)
  return render_to_response('crushmap.html', locals())
