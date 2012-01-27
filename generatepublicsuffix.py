import re
import processDump
import urlparse
import publicsuffix
import sys

"""
This progam will generate a new public suffix list
iteratively.


Utility Methods
"""

"""
function getDomain 
Gets the domain of the url passed in

Arguments
url: URL to be 'domainfied'

Returns
domain: domain name
"""
def getDomain(url):
  urlObj = urlparse.urlparse(url)
  domain = urlObj.netloc
  domain = processDump.stripPort(domain) 
  domain = processDump.stripWWW(domain)
  return domain

"""
function printPrefix
Prints a fixed number of outputs in sorted order
from the prefix list passed in

"""

def printPrefix(prefixNumber, sortedPrefixNumber, number):
	i = 0
	for key in sortedPrefixNumber:	
		print key + ':' + str(prefixNumber[key])
		i += 1
		if i > number: break

"""
Filter that uses a threshold
"""

class ThresholdFilter:
  def __init__(self, threshold):
    self.threshold = threshold
  def __call__(self, prefixCounter, suffix):
    if prefixCounter[suffix] > self.threshold:
       return True
    return False

"""
def getPublicSuffixFromPSList
given a PSList, returns the longest possible suffix + 1. 
If it cannot, returns PS + 1.

Arguments
domain: domain name. Assumes 'domainified' url
PSList: The set PSList which represents the suffix list

Returns
either string in PSList + 1 or PS + 1
"""

def getPublicSuffixFromPSList(domain, PSList, suffixParser):	
	currentDotIndex = domain.find('.') 
	previousDotIndex = -1
	while currentDotIndex != -1:
		suffix = domain[currentDotIndex + 1:]
		if suffix in PSList:
			prefix = domain[previousDotIndex + 1:currentDotIndex]	
			return '.'.join([prefix, suffix])
		previousDotIndex = currentDotIndex
		currentDotIndex = domain.find('.', currentDotIndex + 1)
	return suffixParser.get_public_suffix(domain)


"""
Dump File Methods

function getFrequenciesOfPrefixesForSuffixes
Returns a map with the frequncies of the prefix
for each suffix in the given prefixCounter

Argument
prefixCounter: map with suffix => set of prefixes

Returns
Tuple (prefixNumber, sortedPrefixList)
prefixNumber: map of suffix => number of prefixes
sortedPrefixNumber: sorted list of suffixes in highest to
                    lowest number of prefixes
"""

def getFrequenciesOfPrefixesForSuffixes(prefixCounter):
	prefixNumber = {}
	for key in prefixCounter.keys():
		prefixNumber[key] = len(prefixCounter[key])

	sortedPrefixNumber = sorted(prefixNumber, \
	                            key = prefixNumber.get, \
									            reverse = True)
	return prefixNumber, sortedPrefixNumber



"""
function buildPrefixCounter
Builds the prefix counter for a single domain
in the dump

"""
def buildPrefixCounter(domain, PSList, prefixCounter):
	currentDotIndex = domain.find('.') 
	while currentDotIndex != -1:
		suffix = domain[currentDotIndex + 1:]
		if suffix in PSList:
			prefix = domain[:currentDotIndex]	
			prefixMap = prefixCounter.get(suffix, False)
			if not prefixMap:
				prefixMap = set()
				prefixCounter[suffix] = prefixMap
			# only adding unique prefixes
			prefixMap.add(prefix)
			# only add largest suffix
			break
		# continue till suffix found or no more suffixes
		currentDotIndex = domain.find('.', currentDotIndex + 1)

"""
function getPrefixesOfSuffixList
Given a prefix list, this generates a new list
of frequencies of prefixes in dump for the given suffixes in
PSList

Arguments
PSList: A Set of suffixes
dumpFile: A file object to the dump file

Returns
prefixCounter: Map from suffix => prefixes of suffix
"""

def getPrefixesOfSuffixList(PSList, dumpFile):
  # map  suffix => prefixes of suffix
	prefixCounter = {}
	for line in dumpFile:
		record = processDump.getRecord(line)
		url, referrer, method, status, \
			request_cookie, response_cookie = record
    
		domain = getDomain(url)
    # dont process IPs
		if processDump.isIp(domain):
			continue
		buildPrefixCounter(domain, PSList, prefixCounter)
	return prefixCounter


"""
function getPrefixesOfAlexaSuffixList
Given an alexa prefix list, this generates a new list
of frequencies of prefixes in dump for the given suffixes in
PSList

Arguments
PSList: A Set of suffixes
dumpFile: A file object to the dump file

Returns
prefixCounter: Map from suffix => prefixes of suffix
"""
def getPrefixesOfAlexaSuffixList(PSList, dumpFile):
	prefixCounter = {}
	for line in dumpFile:
		match = re.match(r'\d+,(.*?)$', line)
		if match:
			domain = match.group(1)
		else:
			continue
		if processDump.isIp(domain):
			continue
		buildPrefixCounter(domain, PSList, prefixCounter)
	return prefixCounter

"""
function doPSListFromDump
runs the PSList generation Algorithm for one iteration and returns a 
set of suffixes in PSList which satisfy the filter function

Argument
PSList: the PSList with candidate suffixes
dumpFile: file object to dump file
filterFunction: filters on the basis of frequency of the suffix
                e.g. ThresholdFilter

Returns
finalPSList: Set of suffixes that are > threshold
"""

def doPSListFromDump(dumpFile, PSList, filterFunction):
  print('getting prefix frequencies')
  prefixCounter = getPrefixesOfSuffixList(PSList, dumpFile)
  (prefixNumber, sortedPrefixNumber) = getFrequenciesOfPrefixesForSuffixes(prefixCounter)
  print('done')
  finalPSList = set()
  print('augment list')
  augmentPSList(finalPSList, prefixNumber, filterFunction)
  print('done augmenting')
  return finalPSList


"""
function doPSListFromAlexa
runs the PSList generation Algorithm for one iteration and returns a new 
set of suffixes in PSList which satisfy filter

Argument
PSList: the PSList with candidate suffixes
dumpFile: file object to alexa dump file
filterFunction: filters on the basis of frequency of the suffix
                e.g. ThresholdFilter

Returns
finalPSList: Set of suffixes that are > threshold
"""

def doPSListFromAlexa(dumpFile, PSList, filterFunction):
  prefixCounter = getPrefixesOfAlexaSuffixList(PSList, dumpFile)
  (prefixNumber, sortedPrefixNumber) = getFrequenciesOfPrefixesForSuffixes(prefixCounter) 
  finalPSList = set()
  augmentPSList(finalPSList, prefixNumber, filterFunction)
  return finalPSList


"""
function doCombinedDumpAlexaList
runs the PSList generation Algorithm for one iteration and returns a new 
set of suffixes in PSList which satify the filters

Argument
PSList: the PSList with candidate suffixes
alexaPSList: PSList with alexa candidate suffixes
mergeDump: file object to data dump file
alexaDump: file object to alexa dump file

alexaFilterFunction: filters on the basis of frequency of the suffix
                e.g. ThresholdFilter
dumpFilterFunction: filters on the basis of frequency of the suffix
                e.g. ThresholdFilter

Returns
finalPSList: Set of suffixes that are > threshold
"""

def doCombinedDumpAlexaList(alexaDump, mergeDump, \
                            alexaPSList, PSList, \
                            alexaFilterFunction, dumpFilterFunction):
  alexaPrefixCounter = getAlexaPrefixCounter(alexaPSList, alexaDump)
  (alexaPrefixNumber, alexaSortedPrefixNumber) = \
                 getFrequenciesOfPrefixesForSuffixes(alexaPrefixCounter)

  prefixCounter = getPrefixCounter(PSList, mergeDump)
  (prefixNumber, sortedPrefixNumber) = \
                 getFrequenciesOfPrefixesForSuffixes(alexaPrefixCounter)
  finalPSList = set()
  augmentPSList(finalPSList, alexaPrefixNumber, alexaFilterFunction)
  augmentPSList(finalPSList, prefixNumber, dumpFilterFunction)
  return finalPSList

"""
function augmentPSList
This function merges two suffix lists together subject to 
a filter function. When the filter function returns true
it merges, and ignores otherwise. 
The filter function takes prefixNumber and suffix as arguments
The merged result is stored in the first suffix list

Arguments
PSList: a Set of suffixes
prefixNumber: a map of suffix => frequency
filterFunction: if filter function returns True
                added to prefixNumber

Result
Merged List is in PSList
"""

def augmentPSList(PSList, prefixNumber, filterFunction):
	for suffix in prefixNumber.keys():
		if filterFunction(prefixNumber, suffix):
			PSList.add(suffix)

"""
function getInitialPSListFromAlexa
This function reads the dump file from alexa of the top
domains and returns the list of PS + 1 from the alexa
file.

Arguments
dumpFile: file Object to dump file

Returns
PSList: set of PS + 1
"""

def getInitialPSListFromAlexa(dumpFile):
	PSList = set()
	currentLength = 1
	suffixParser = publicsuffix.PublicSuffixList()
	for line in dumpFile:	
		match = re.match(r'\d+,(.*?)$', line)
		if match:
			urlDomain = match.group(1)
		else:
			continue
		if processDump.isIp(urlDomain):
			continue
	
		urlDomain = suffixParser.get_public_suffix(urlDomain)
		if len(urlDomain.split('.')) > currentLength:
			PSList.add(urlDomain)
	return PSList

"""
function getInitialPSList 
This function reads the dumpFile and then gets the set
of the suffixes + 1 of the entries in the public suffix list
This returns a PS + 1 set

Arguments
dumpFileName: path to dump file

Returns
PSList: Set of suffixes in the public suffix list which
        are present in the dump file. This is PS + 1
"""

def getInitialPSList(dumpFile):	
	PSList = set()
	currentLength = 1
	for line in dumpFile:	
		record = processDump.getRecord(line)
		url, referrer, method, status, \
			request_cookie, response_cookie = record

		urlDomain, urlMime, urlQuery, urlParams = \
		    processDump.parseURL(url)
	  # dont process IP addresses	
		if processDump.isIp(urlDomain):
			continue
		if len(urlDomain.split('.')) > currentLength:
			PSList.add(urlDomain)
	return PSList


"""
function getNextLevelAlexa 
This function reads the alexa dumpFile and then gets the set
of the suffixes + 1 of the entries in the suffixes in PSList

Arguments
dumpFile: file object to alexa file

Returns
PSList: Candidate set of suffixes of length PSList + 1
"""
def getNextLevelAlexa(dumpFile, PSList):
  candidatePSList = set()
	for line in dumpFile:	
		match = re.match(r'\d+,(.*?)$', line)
		if match:
			urlDomain = match.group(1)
		else:
			continue
		if processDump.isIp(urlDomain):
			continue

		currentDotIndex = urlDomain.find('.') 
		previousDotIndex = -1
		while currentDotIndex != -1:
			suffix = urlDomain[currentDotIndex + 1:]
			if suffix in PSList:
				prefix = urlDomain[previousDotIndex + 1:currentDotIndex]	
				candidatePSList.add('.'.join([prefix, suffix]))
			previousDotIndex = currentDotIndex
			currentDotIndex = urlDomain.find('.', currentDotIndex + 1)
  return candidatePSList

"""
function getNextLevel 
This function reads the dumpFile and then gets the set
of the suffixes + 1 of the entries in the suffixes in PSList

Arguments
dumpFile: file object to dump file

Returns
PSList: Candidate set of suffixes of length PSList + 1
"""
def getNextLevel(dumpFile, PSList):
  candidatePSList = set()
  for line in dumpFile:
		record = processDump.getRecord(line)
		url, referrer, method, status, \
			request_cookie, response_cookie = record

		urlDomain, urlMime, urlQuery, urlParams = \
		    processDump.parseURL(url)
	  # dont process IP addresses	
		if processDump.isIp(urlDomain):
			continue

		currentDotIndex = urlDomain.find('.') 
		previousDotIndex = -1
		while currentDotIndex != -1:
			suffix = urlDomain[currentDotIndex + 1:]
			if suffix in PSList:
				prefix = urlDomain[previousDotIndex + 1:currentDotIndex]	
				candidatePSList.add('.'.join([prefix, suffix]))
			previousDotIndex = currentDotIndex
			currentDotIndex = urlDomain.find('.', currentDotIndex + 1)
  return candidatePSList

"""
Algorithm
(1) We generate PS + 1 first. This acts as a seed PS List (initialpslist)
(2) We find the number of prefixes for the PS + 1 list
(3) Select the PS + 1 suffixes that have the properties
(4) Augment the original list with this new list
(5) Use the list obtained in (3) to get the next level of list
(6) use the list obtained in (5) as input to (2)


This program assumes that your dump file is too large to fit
in memory.
The main function is an example of using this program.
"""
def main(dumpFile):
	# curretn prefix List
	# example implementation
  print('getting initial list') 
  global PSList
  PSList = getInitialPSList(dumpFile)
  print('got initial list')
  dumpFile.seek(0) 
  filterFunction = ThresholdFilter(10)
  finalList = doPSListFromDump(dumpFile, PSList, filterFunction)
  dumpFile.seek(0)
  nextLevel = getNextLevel(dumpFile, finalList)


if __name__ == '__main__':
# usage: python generatepublicsuffixlist.py <dumpfile>
	# gets the dump file from the argument
  if len(sys.argv) > 1:
    try:
      dumpFile = open(sys.argv[1], 'rU')
    except:  
      print('File does not exist')
      sys.exit(-1)

    main(dumpFile)
  else:
    print('Usage: python generatepublicsuffix.py <dumpFile>')
    sys.exit(-1)
  
