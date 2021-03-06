# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module containing utilities for apk packages."""

import re

from devil.android.sdk import aapt


_MANIFEST_ATTRIBUTE_RE = re.compile(
    r'\s*A: ([^\(\)= ]*)(?:\([^\(\)= ]*\))?='
    r'(?:"(.*)" \(Raw: .*\)|\(type.*?\)(.*))$')
_MANIFEST_ELEMENT_RE = re.compile(r'\s*(?:E|N): (\S*) .*$')


def GetPackageName(apk_path):
  """Returns the package name of the apk."""
  return ApkHelper(apk_path).GetPackageName()


# TODO(jbudorick): Deprecate and remove this function once callers have been
# converted to ApkHelper.GetInstrumentationName
def GetInstrumentationName(apk_path):
  """Returns the name of the Instrumentation in the apk."""
  return ApkHelper(apk_path).GetInstrumentationName()


def ToHelper(path_or_helper):
  """Creates an ApkHelper unless one is already given."""
  if isinstance(path_or_helper, basestring):
    return ApkHelper(path_or_helper)
  return path_or_helper


def _ParseManifestFromApk(apk_path):
  aapt_output = aapt.Dump('xmltree', apk_path, 'AndroidManifest.xml')

  parsed_manifest = {}
  node_stack = [parsed_manifest]
  indent = '  '

  for line in aapt_output[1:]:
    if len(line) == 0:
      continue

    indent_depth = 0
    while line[(len(indent) * indent_depth):].startswith(indent):
      indent_depth += 1

    node_stack = node_stack[:indent_depth]
    node = node_stack[-1]

    m = _MANIFEST_ELEMENT_RE.match(line[len(indent) * indent_depth:])
    if m:
      if not m.group(1) in node:
        node[m.group(1)] = {}
      node_stack += [node[m.group(1)]]
      continue

    m = _MANIFEST_ATTRIBUTE_RE.match(line[len(indent) * indent_depth:])
    if m:
      if not m.group(1) in node:
        node[m.group(1)] = []
      node[m.group(1)].append(m.group(2) or m.group(3))
      continue

  return parsed_manifest


class ApkHelper(object):
  def __init__(self, path):
    self._apk_path = path
    self._manifest = None

  @property
  def path(self):
    return self._apk_path

  def GetActivityName(self):
    """Returns the name of the Activity in the apk."""
    manifest_info = self._GetManifest()
    try:
      activity = (
          manifest_info['manifest']['application']['activity']
              ['android:name'][0])
    except KeyError:
      return None
    if '.' not in activity:
      activity = '%s.%s' % (self.GetPackageName(), activity)
    elif activity.startswith('.'):
      activity = '%s%s' % (self.GetPackageName(), activity)
    return activity

  def GetInstrumentationName(
      self, default='android.test.InstrumentationTestRunner'):
    """Returns the name of the Instrumentation in the apk."""
    manifest_info = self._GetManifest()
    try:
      return manifest_info['manifest']['instrumentation']['android:name'][0]
    except KeyError:
      return default

  def GetPackageName(self):
    """Returns the package name of the apk."""
    manifest_info = self._GetManifest()
    try:
      return manifest_info['manifest']['package'][0]
    except KeyError:
      raise Exception('Failed to determine package name of %s' % self._apk_path)

  def GetPermissions(self):
    manifest_info = self._GetManifest()
    try:
      return manifest_info['manifest']['uses-permission']['android:name']
    except KeyError:
      return []

  def GetSplitName(self):
    """Returns the name of the split of the apk."""
    manifest_info = self._GetManifest()
    try:
      return manifest_info['manifest']['split'][0]
    except KeyError:
      return None

  def HasIsolatedProcesses(self):
    """Returns whether any services exist that use isolatedProcess=true."""
    manifest_info = self._GetManifest()
    try:
      services = manifest_info['manifest']['application']['service']
      return any(int(v, 0) for v in services['android:isolatedProcess'])
    except KeyError:
      return False

  def _GetManifest(self):
    if not self._manifest:
      self._manifest = _ParseManifestFromApk(self._apk_path)
    return self._manifest

