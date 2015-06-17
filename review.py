#!/usr/bin/env python

import string
import re
import subprocess
import sys
import os
import urllib

# Classes

class Path(object) :
  def __init__(self, repoPath, modifiers, path, revision, review) :
    self.path = path
    if (review == None) :
      self.min = revision
    else :
      self.min = None
    if (review == None) :
      self.max = revision
    else :
      self.max = None
    self.overallMin = revision
    self.overallMax = revision
    if (modifiers.find("D") != -1) :
      # File was deleted, look at previous revision
      self.nodeKind = getNodeKind(repoPath, path, revision - 1)
    else :
      self.nodeKind = getNodeKind(repoPath, path, revision)

  def revision(self, revision, review) :
    if (review == None and (self.min == None or revision < self.min)) :
      self.min = revision
    if (revision < self.overallMin) :
      self.overallMin = revision

    if (review == None and (self.max == None or revision > self.max)) :
      self.max = revision
    if (revision > self.overallMax) :
      self.overallMax = revision


class Review(object) :
  def __init__(self, reviewNo, start, end) :
    self.reviewNo = reviewNo
    self.start = start
    self.end = end
    if (self.start > self.end) :
      temp = self.start
      self.start = self.end
      self.end = temp

  def covers(self, revision) :
    return (revision >= self.start and revision <= self.end)

  def printArg(self) :
    return "-r '{0}:{1}-{2}'".format(self.reviewNo, self.start, self.end)

def getNodeKind(repoPath, path, revision) :
  url = repoPath + "/" + path + "@" + str(revision)
  command = ["svn", "info", url]
  process = subprocess.Popen(command, stdout=subprocess.PIPE)
  output = process.communicate()

  lines = output[0].split("\n")
  kind = None
  for line in lines :
    if (re.match("^Node Kind: ", line)) :
      parts = line.split(": ")
      kind = parts[1]
      break

  return kind


# Constants
REVIEW_DEF=1
OMITTED_REVS=2

repoPath = os.environ.get("SVNROOT")
if (repoPath == None) :
  print "A path to the SVN repository must be defined in an environment variable named \"SVNROOT\""
  sys.exit()

# Process the arguments
thisReviewNo = 1
searchStrings = []
previousReviews = []
nextArg = None
invalidArgs = True
omittedRevisions = []

for argument in sys.argv[1:] :
  # We have at least one argument, good start
  invalidArgs = False

  if (nextArg == REVIEW_DEF) :
    nextArg = None
    split = argument.split(":")
    if (len(split) != 2) :
      invalidArgs = True
      break
    reviewNo = int(split[0])
    revisions = split[1].split("-")
    if (len(revisions) != 2) :
      invalidArgs = True
      break
    previousReviews.append(Review(reviewNo, int(revisions[0]), int(revisions[1])))
    if (reviewNo >= thisReviewNo) :
      thisReviewNo = reviewNo + 1

  elif (nextArg == OMITTED_REVS) :
    nextArg = None
    omittedRevisions = re.split(' *, *', argument)

  elif (argument == '-r') :
    nextArg = REVIEW_DEF

  elif (argument == '-o') :
    nextArg = OMITTED_REVS

  else :
    searchStrings.append(argument)

if (invalidArgs or len(searchStrings) == 0) :
    print 'Usage: python review.py [-r reviewno:start-end [-r reviewno:start-end ...]] [-o <comma separated list of omitted revisions>] search_term [search_term ...]'
    sys.exit()

# Perform the query
command = "svn log -v {0}".format(repoPath)
process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
output = process.communicate()

revlist = re.split('-{72}', output[0])
revisionReviews = {}  # The review number for each revision
revisionNumbers = []  # All revision numbers
thisReviewRevisions = []  # The revisions relevant to *this* review
paths = []
for revisionText in reversed(revlist) :
  # The conditions are to be ORed so search for any match
  match = False
  for condition in searchStrings :
    if (string.find(revisionText, condition) != -1) :
      match = True
      break

  if (match) :
    revisionNumber = int(re.findall('(?<=r)[0-9]+', revisionText)[0])

    if str(revisionNumber) not in omittedRevisions :
      revisionNumbers.append(revisionNumber)
      revisionReviews[revisionNumber] = None

      for review in previousReviews :
        if (review.covers(revisionNumber)) :
          revisionReviews[revisionNumber] = review
          break

      if revisionReviews[revisionNumber] == None :
        thisReviewRevisions.append(revisionNumber)

      lines = re.split('\n', revisionText)
      i = 3

      while lines[i] != '' and i < len(lines):
        modifiers = lines[i][:6]
        path = lines[i][6:].split("(")[0].strip()
        found = False
        for nextPath in paths :
          if (nextPath.path == path) :
            found = True
            nextPath.revision(revisionNumber, revisionReviews[revisionNumber])
            break

        if (not found) :
          paths.append(Path(repoPath, modifiers, path, revisionNumber, revisionReviews[revisionNumber]))

        i = i + 1

paths = sorted(paths, key=lambda path: path.path)
projectRegex = re.compile('^(?P<project>(([^/]+/)*trunk)|(([^/]+/)*branches/[^/]+))/')

nextArgs = ''
for prevReview in previousReviews :
  nextArgs += prevReview.printArg() + ' '

if len(thisReviewRevisions) > 0 :
  nextArgs += '-r \'{0}:{1}-{2}\' '.format(thisReviewNo, min(thisReviewRevisions), max(thisReviewRevisions))

if len(omittedRevisions) > 0 :
  nextArgs += '-o \'{0}\' '.format(','.join(omittedRevisions))

nextArgs += '\'' + '\' \''.join(searchStrings) + '\''

print '== Revisions =='
print ''
for revno in revisionNumbers :
  if (revisionReviews[revno] == None) :
    print ' * [{0}]'.format(revno)
  else :
    print ' * [{0}] - Review {1}'.format(revno, revisionReviews[revno].reviewNo)
print ''
print 'Filter: `{0}`'.format(str(sys.argv[1:]))
print ''
print 'Next Args: `{0}`'.format(nextArgs)
print ''
print '== Effected Paths =='
print ''
for nextPath in paths :
  if (nextPath.nodeKind == "file") :
    filename = nextPath.path[string.rfind(nextPath.path, '/') + 1:]
    project = re.match(projectRegex, nextPath.path).group('project')
    if (nextPath.min == None) :
      print ' * `{4}/.../{0}` ([log:"{1}@{2}:{3}" Total Changes])'.format(filename, urllib.quote(nextPath.path), nextPath.overallMin, nextPath.overallMax, project)
    elif (nextPath.min == nextPath.overallMin and nextPath.max == nextPath.overallMax) :
      print ' * [log:"{1}@{2}:{3}" {4}/.../{0}]'.format(filename, nextPath.path.replace('#', '%23'), nextPath.min, nextPath.max, project)
    else :
      print ' * [log:"{1}@{2}:{3}" {6}/.../{0}] ([log:"{1}@{4}:{5}" Total Changes])'.format(filename, urllib.quote(nextPath.path), nextPath.min, nextPath.max, nextPath.overallMin, nextPath.overallMax, project)
print ''
print '== Review {0} =='.format(thisReviewNo)
print ''
for nextPath in paths :
  if (nextPath.nodeKind == "file" and nextPath.min != None) :
    filename = nextPath.path[string.rfind(nextPath.path, '/') + 1:]
    project = re.match(projectRegex, nextPath.path).group('project')
    print '=== [log:"{0}@{1}:{2}" {4}/.../{3}] ==='.format(urllib.quote(nextPath.path), nextPath.min, nextPath.max, filename, project)
    print ''
    print ' 1. '
    print ''
