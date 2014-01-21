#!python

import string
import re
import subprocess
import sys
import os

# Classes

class Path(object) :
  def __init__(self, path, revision, review) :
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

# Constants
REVIEW_DEF=1

revisionPath = os.environ.get("SVNROOT")
if (revisionPath == None) :
  print "A path to the SVN repository must be defined in an environment variable named \"SVNROOT\""
  sys.exit()

# Process the arguments
thisReviewNo = 1
searchStrings = []
previousReviews = []
nextArg = None
invalidArgs = True

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

  elif (argument == '-r') :
    nextArg = REVIEW_DEF

  else :
    searchStrings.append(argument)

if (invalidArgs) :
    print 'Usage: python review.py [-r reviewno:start-end [-r reviewno:start-end ...]] [search_term [search_term ...]]'
    sys.exit()

# Perform the query
command = "svn log -v {0}".format(revisionPath)
process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
output = process.communicate()

revlist = re.split('-{72}', output[0])
revnumbers = {}
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
    revnumbers[revisionNumber] = None

    for review in previousReviews :
      if (review.covers(revisionNumber)) :
        revnumbers[revisionNumber] = review
        break

    lines = re.split('\n', revisionText)
    i = 3

    while lines[i] != '' and i < len(lines):
      path = lines[i][6:]
      found = False
      for nextPath in paths :
        if (nextPath.path == path) :
          found = True
          nextPath.revision(revisionNumber, revnumbers[revisionNumber])
          break

      if (not found) :
        paths.append(Path(path, revisionNumber, revnumbers[revisionNumber]))

      i = i + 1

paths = sorted(paths, key=lambda path: path.path)

print '== Revisions =='
print ''
for revno in revnumbers.keys() :
  if (revnumbers[revno] == None) :
    print ' * [{0}]'.format(revno)
  else :
    print ' * [{0}] - Review {1}'.format(revno, revnumbers[revno].reviewNo)
print ''
print 'Filter: `{0}`'.format(str(sys.argv[1:]))
print ''
print '== Effected Paths =='
print ''
for nextPath in paths :
  filename = nextPath.path[string.rfind(nextPath.path, '/') + 1:]
  if (nextPath.min == None) :
    print ' * {0} ([log:{1}@{2}:{3} Total Changes])'.format(filename, nextPath.path, nextPath.overallMin, nextPath.overallMax)
  elif (nextPath.min == nextPath.overallMin and nextPath.max == nextPath.overallMax) :
    print ' * [log:{1}@{2}:{3} {0}]'.format(filename, nextPath.path, nextPath.min, nextPath.max)
  else :
    print ' * [log:{1}@{2}:{3} {0}] ([log:{1}@{4}:{5} Total Changes])'.format(filename, nextPath.path, nextPath.min, nextPath.max, nextPath.overallMin, nextPath.overallMax)
print ''
print '== Review {0} =='.format(thisReviewNo)
print ''
for nextPath in paths :
  if (nextPath.min != None) :
    filename = nextPath.path[string.rfind(nextPath.path, '/') + 1:]
    print '=== [log:{0}@{1}:{2} {3}] ==='.format(nextPath.path, nextPath.min, nextPath.max, filename)
    print ''
    print ' 1. '
    print ''