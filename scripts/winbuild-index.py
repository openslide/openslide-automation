#!/usr/bin/python
# Generate directory index for Windows snapshot builds

from contextlib import contextmanager
import dateutil.parser
from jinja2 import Template
import json
import os
import sys

HTML = 'index.html'
JSON = 'index.json'
RETAIN = 30
GC_FILES = (
    'openslide-win32-%(pkgver)s.zip',
    'openslide-win64-%(pkgver)s.zip',
    'openslide-winbuild-%(pkgver)s.zip',
)

template = Template('''<!doctype html>

<style type="text/css">
  table {
    margin-left: 20px;
    border-collapse: collapse;
  }
  th.repo {
    padding-right: 1em;
  }
  td {
    padding-right: 20px;
  }
  td.date {
    padding-left: 5px;
  }
  td.revision {
    font-family: monospace;
  }
  td.spacer {
    padding-right: 25px;
  }
  td.winbuild {
    padding-right: 5px;
  }
  tr {
    height: 2em;
  }
  tr:nth-child(2n) {
    background-color: #e8e8e8;
  }
</style>

<title>OpenSlide Windows development builds</title>
<h1>OpenSlide Windows development builds</h1>

{% macro revision_link(repo, prev, cur) %}
  {% if prev %}
    <a href="https://github.com/openslide/{{ repo }}/compare/{{ prev[:8] }}...{{ cur[:8] }}">
      {{ cur[:8] }}
    </a>
  {% else %}
    {{ cur }}
  {% endif %}
{% endmacro %}

<table>
  <tr>
    <th>Date</th>
    <th class="repo">openslide</th>
    <th class="repo">openslide-java</th>
    <th class="repo">openslide-winbuild</th>
    <th></th>
    <th colspan="3">Downloads</th>
  </tr>
  {% for row in rows %}
    <tr>
      <td class="date">{{ row.date }}</td>
      <td class="revision">
        {{ revision_link('openslide', row.openslide_prev, row.openslide_cur) }}
      </td>
      <td class="revision">
        {{ revision_link('openslide-java', row.java_prev, row.java_cur) }}
      </td>
      <td class="revision">
        {{ revision_link('openslide-winbuild', row.winbuild_prev, row.winbuild_cur) }}
      </td>
      <td class="spacer"></td>
      <td class="win32">
        <a href="openslide-win32-{{ row.pkgver }}.zip">
          32-bit
        </a>
      </td>
      <td class="win64">
        <a href="openslide-win64-{{ row.pkgver }}.zip">
          64-bit
        </a>
      </td>
      <td class="winbuild">
        <a href="openslide-winbuild-{{ row.pkgver }}.zip">
          Corresponding sources
        </a>
      </td>
    </tr>
  {% endfor %}
</table>
''')


def try_unlink(path):
    try:
        os.unlink(path)
    except OSError:
        pass


@contextmanager
def atomic_update(path):
    temp_path = path + '.new'
    fh = open(temp_path, 'w')
    try:
        yield fh
    except Exception, e:
        fh.close()
        try_unlink(temp_path)
        raise
    else:
        fh.close()
        os.rename(temp_path, path)


# Parse command line
if len(sys.argv) == 6:
    basedir = sys.argv[1]
    pkgver = sys.argv[2]
    new_record = {
        'pkgver': pkgver,
        'date': dateutil.parser.parse(pkgver.split('-')[0]).date().isoformat(),
        'openslide': sys.argv[3],
        'openslide-java': sys.argv[4],
        'openslide-winbuild': sys.argv[5],
    }
elif len(sys.argv) == 2:
    basedir = sys.argv[1]
    new_record = None
else:
    print ('Usage: %s <basedir> [<pkgver> <openslide-commitid> ' +
            '<java-commitid> <winbuild-commitid>]') % sys.argv[0]
    sys.exit(1)

# Load records from JSON
if not os.path.exists(basedir):
    os.makedirs(basedir)
try:
    with open(os.path.join(basedir, JSON)) as fh:
        records = json.load(fh)
except IOError:
    records = []

# Update records
if new_record:
    records.append(new_record)
for record in records[:-RETAIN]:
    for tmpl in GC_FILES:
        try_unlink(os.path.join(basedir, tmpl % {
            'pkgver': record['pkgver'],
        }))
records = records[-RETAIN:]

# Generate rows for HTML template
rows = []
prev_record = None
for record in records:
    def prev(key):
        if prev_record and record[key] != prev_record[key]:
            return prev_record[key]
        else:
            return None
    rows.append({
        'date': record['date'],
        'pkgver': record['pkgver'],
        'openslide_prev': prev('openslide'),
        'openslide_cur': record['openslide'],
        'java_prev': prev('openslide-java'),
        'java_cur': record['openslide-java'],
        'winbuild_prev': prev('openslide-winbuild'),
        'winbuild_cur': record['openslide-winbuild'],
    })
    prev_record = record

# Write HTML
with atomic_update(os.path.join(basedir, HTML)) as fh:
    template.stream({
        'rows': reversed(rows),
    }).dump(fh)

# Write records to JSON
with atomic_update(os.path.join(basedir, JSON)) as fh:
    json.dump(records, fh, indent=2, sort_keys=True)
