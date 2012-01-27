import re
import urlparse
import sys
import publicsuffix
 
from numpy import eye
from numpy import argsort 


"""
function getRecord
parses a line from the dump file

Argument
line from dumpFile

Returns
record: length 6 vector with fields
        url, referrer, method, status,
			  request_cookie, response_cookie
"""

def getRecord(line):
	record = []
	match = re.search(r'\'(.*?)\', \'(.*?)\', \'(.*?)\', (.*?), \'(.*?)\', \'(.*?)\'', line) 
	
	if match:
		for i in range(1, 7):
			record.append(match.group(i))
	else:
		print line
		record = ['', '', '', '', '', '']
	return record

"""
function parseParsedDomain
Gets the PS+1 for the domain
"""
def parseParsedDomain(domain):
	suffix = suffixParser.get_public_suffix(domain)
	return suffix

"""
function stripPort
Strips the port from the domain name
"""
def stripPort(domain):
	domain = domain.split(':')
	return domain[0]
	

"""
function stripWWW
Strips the www from the domain name
"""
def stripWWW(domain):
	#return re.sub(r'^www.*?\.', '', domain)
	return re.sub(r'^www\.', '', domain)

"""
function isIp
checks whether domain is an IP

Return
True if is ip
False otherwise
"""
def isIp(domain):
	if re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', domain):
		return True
	return False


"""
function parseURL
Parses the given url

Argument
url: url string

Return
4 tuple: (domain, mimetype, query, params)
domain: the processed domain name
mimetype: guessed mime
query: query string
params: query parameters
"""
def parseURL(url):
	parsed = urlparse.urlparse(url)
	domain = parsed.netloc
	domain = stripWWW(domain)
	domain = stripPort(domain)
	if not isIp(domain):
		domain = parseParsedDomain(domain)

	mimetype = ''
	match = re.search(r'\.(.*?)$', parsed.path)
	if match:
		mimeType = match.group(1)
	query = parsed.query
	params = parsed.params
	return (domain, mimetype, query, params)

"""
function putEdge
Helper function to construct graph from dump data

Arguments
graph: Dict representing the graph structure
url: url string
urlDomain: domain of url
urlMime: mimeType
urlQuery: queryString of url
urlParams: parameters of url
referrer: referrer of url
referrerDomain: domain of referrer
referrerMime: mime type of referrer
referrerQuery: queryString of referrer url
referrerParams: parameters of referrer url
method: request method (GET/POST)
request_cookie: cookies sent during the request for the url
response_cookie: cookies returned by the request
"""
def putEdge(graph, url, urlDomain, urlMime, urlQuery, urlParams, \
						referrer, referrerDomain, referrerMime, referrerQuery, referrerParams, \
						method, request_cookie, response_cookie):

	inList = graph.get(urlDomain, False)
	if not inList:
		inList = {}
		graph[urlDomain] = inList
	
	record = (url, urlMime, urlQuery, urlParams, \
						method, request_cookie, response_cookie)
	recordList = inList.get(referrerDomain, False)
	if not recordList:	
		recordList = []
		inList[referrerDomain] = recordList

	recordList.append(record)

def printGraph(graph):
	for key in graph.keys():
		print ''
		print '>>>' + key
		inList = graph[key]
		for inNode in inList.keys():
				print ''
				print '>>' + inNode
				for record in inList[inNode]:
					print '>' + str(record)
			

if __name__ == '__main__':	
  suffixParser = publicsuffix.PublicSuffixList()
  graph = {}
	dumpFile = open(sys.argv[1], 'rU')

	falserec = 0
	for line in dumpFile:
		record = getRecord(line)	
		url, referrer, method, status, \
			request_cookie, response_cookie = record
		
		urlDomain, urlMime, urlQuery, urlParams = parseURL(url)
		referrerDomain, referrerMime, \
			referrerQuery, referrerParams = parseURL(referrer)

		if urlDomain == referrerDomain or referrerDomain == '':
			continue
		
		putEdge(graph, url, urlDomain, urlMime, urlQuery, urlParams,  \
						referrer, referrerDomain, referrerMime, referrerQuery, referrerParams, \
						method, request_cookie, response_cookie)	

	"""
	(lookupTable, reverseLookupTable, currentId) = simrank3.makeLookupTable(graph)
	print currentId
	print 'starting simrank'
	simRankMatrix = eye(currentId, dtype=float)
	simrank3.main(graph, simRankMatrix, lookupTable, reverseLookupTable, currentId)
	outputfile = open('simout', 'w')
	simrank3.serialize(outputfile, simRankMatrix, graph, currentId)
	"""
