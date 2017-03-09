#Module with methods used by Program to select best Router for new nodes joining the OLSR network
#Author: Bidur Devkota
# /usr/bin/python

import socket, sys, time, datetime , os, copy,random,urllib2 , commands, math, operator, random
from geopy import distance

class GPSPosition:
    def __init__(self, lat0, lon0, alt0):
        self.lat = lat0
        self.lon = lon0
        self.alt = alt0
#end of class


        

def getNewNodes4Generation(hostName, listCurrentNodes,listPrevNodes ):
    
    listNewNodes = list(set(listCurrentNodes) - set([hostName]) - set(listPrevNodes))# remove duplicate nodes

    return listNewNodes

def isNewNodeDiscoveryIntervalExpired(newNodeDiscoveryInterval, lastLiveTimeOfNetwork):
    
    if ( newNodeDiscoveryInterval > (time.time() - lastLiveTimeOfNetwork) ):
        # if disconnection interval is not long enough then no need to select new router
        #print 'In-partition Network re-connected after '+ str(time.time() - lastLiveTimeOfNetwork)+' seconds of disconnection'
        return False

    return True # new router selection is required since the hostName did not see any neighbor for more than newNodeDiscoveryInterval

def printLog(printStr):# just to print logs to file
    if(os.path.exists("printLog.txt")):
        f= open("printLog.txt",'a')
    else:
        f= open("printLog.txt",'w')
    f.write(str(printStr) )
    f.write("\n")
    f.close()
    
    

def checkAndHandleTransiantCondition(listTxtInfoInitial,transientInterval, hostName, listPrevNodes,olsrIP, txtInfoPort,generation, dictLostNodes,newNodeDiscoveryInterval,lastLiveTimeOfNetwork):

    listCurrentNodes = []
    listNewNodes = []

        
    for i in range (0,len(listTxtInfoInitial)):
        listCurrentNodes.append(listTxtInfoInitial[i][0])
        listCurrentNodes.append(listTxtInfoInitial[i][1])
    
    listNewNodes = list(set(listCurrentNodes) - set([hostName]) - set(listPrevNodes))# remove duplicate nodes

    printLog( 'listNewNodes: '+ str(listNewNodes))
    printLog(  'listPrevNodes: '+str(listPrevNodes))
        

    if( (len(listNewNodes)>0) and ( ( (len(listPrevNodes)>0)) or ((len(listPrevNodes)==0) and
                                                                  isNewNodeDiscoveryIntervalExpired(newNodeDiscoveryInterval, lastLiveTimeOfNetwork)) ) ):

            # now check if the nodes in listNewNodes have disconnected long enough( interval > newNodeDiscoveryInterval)
            # if NOT long enough, then no need to select a NC router for it, since it is considered as in-partition node.
        for eachNode in listNewNodes:
            if eachNode in dictLostNodes.keys():
                printLog( 'eachNode: '+ eachNode)
                if ( newNodeDiscoveryInterval > (time.time() - dictLostNodes[eachNode]) ):
                    # if disconnection interval is not long enough then remove from the list of new node
                    listNewNodes.remove(eachNode)
                    print 'In-partition node '+eachNode+ ' re-connected after '+ str(time.time() - dictLostNodes[eachNode])+' seconds of disconnection'


            
    #pause for some time  <transientInterval>
    if( (len(listNewNodes)>0) and ( ( (len(listPrevNodes)>0)) or ((len(listPrevNodes)==0) and
                                                                  isNewNodeDiscoveryIntervalExpired(newNodeDiscoveryInterval, lastLiveTimeOfNetwork)) ) ):
            
        print str(listNewNodes)+' joined the network. \n Sleep '+ str(transientInterval) +' s for avoiding transient condition'
        time.sleep(transientInterval)

        listTxtInfoInitial = GetOLSRtxtInfo(olsrIP, txtInfoPort,generation)#returns a list of list


    return listTxtInfoInitial,listNewNodes


    

def sortTable(table, cols):
    """ sort a table by multiple columns
        table: a list of lists (or tuple of tuples) where each inner list 
               represents a row
        cols:  a list (or tuple) specifying the column numbers to sort by
               e.g. (1,0) would sort by column 1, then by column 0
    """
    for col in reversed(cols):
        table = sorted(table, key=operator.itemgetter(col))
    return table


def prepareTxtInfo(txtInfo):
   # print txtInfo
    listLines = txtInfo.split('\n')
    listTxtinfo = []
    
   
    for i in range(5, len (listLines)):
        
        if(listLines[i]==''):   continue
        
        listTemp = listLines[i].split('\t')
        listTxtinfo.append(listTemp)

    listSortedInfo = []
  
    #sort as per two columns in a list
    for row in sortTable(listTxtinfo, (0,1)): 
        listSortedInfo.append(row)


    #print '------------SORTED INFO---------------------------'
    #for i in range (0, len (listSortedInfo)):
       # print listSortedInfo[i]

    '''
    Now check each line, and remove the duplicate link information (OR make it symmetric??)
    '''
    listLinksGot = []
    listSortedInfoFinal =[]


    for i in range (0,len(listSortedInfo)):

        #print listSortedInfo[i]

        if(listSortedInfo[i][0]+'-'+listSortedInfo[i][1] in listLinksGot):
            continue
        
        listLinksGot.append( listSortedInfo[i][0]+'-'+listSortedInfo[i][1])
        listLinksGot.append( listSortedInfo[i][1]+'-'+listSortedInfo[i][0])
        listSortedInfoFinal.append(listSortedInfo[i])
        # append the values of this link (ip0 -> ip1) to (ip1 -> ip0) to make the link value symmetric (HERE we replace the actual value of (ip1 -> ip0) by the values of (ip0 -> ip1))
        tempList = [ listSortedInfo[i][1],listSortedInfo[i][0], listSortedInfo[i][2] ,listSortedInfo[i][3], listSortedInfo[i][4] ]
        listSortedInfoFinal.append(tempList)

        
    #print listSortedInfo
    #print listSortedInfoFinal
    return listSortedInfoFinal






# this function returns the IP address of the host(the localhost i.e. 127.0.0.1 is ignored)
# It assumes that the host have only one IP address other than 'localhost'
def getHostIPAddress():
    f=os.popen("/sbin/ifconfig | grep -i \"inet\" | grep -iv \"inet6\" | " + "awk {'print $2'} | sed -ne 's/addr\:/ /p'") 
    for i in f.readlines():
        ip = " ".join((i.rstrip('\n')).split())
        if ((ip != 'localhost')&(ip != '127.0.0.1')&(ip != '127.1.1.1')&(ip != '127.1.0.1')&(ip != '127.0.1.1')):
            return ip
    
def GetOLSRtxtInfo(olsrIP,txtInfoPort,generation):
  try:
    s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
    s.connect( (olsrIP,txtInfoPort) ) 
    s.send( "/topology")  # /all, /neigh,  /link, /route, /topology
    txtInfo = s.recv( 16777216 ) 
    s.close()
  except socket.error, msg:
    print "GetOLSRtxtInfo() : socket error. Please check the status of OLSRD " + str( msg )
    return None
  
  if (generation == 0):
      f= open("txtinfo.txt",'w')
  else:
      f= open("txtinfo.txt",'a')
      
  f.write("\n"+str(generation)+ " " +str(time.time())+ "\n")
  f.write(txtInfo)
  f.close()
  

  txtInfoFinal = prepareTxtInfo(txtInfo)

  #print txtInfo  
  return txtInfoFinal





#push values as a list for the given key
def pushValue2Dict(dictName, key, value):

  # check if the key is set
  if key not in dictName.keys():# if not set then define a list for it
    dictName[key] = list()
    
  dictName[key].append(value) # add the value as a list item for that key
  
  return dictName



def pushAllNodeIPs( dictAllNodes, node, position):

  dictAllNodes[node] = position  #dictAllNodes gives last known position of node

  return dictAllNodes

   


#def extractNetworkData(txtInfo, dictAllNodes):
def extractNetworkData(lstInfo, dictAllNodes):    

 # print "\n", datetime.datetime.now(), "\n", txtInfo
    
 # lstInfo = txtInfo.split("\n")
  dictNeigh = dict()
  dictNLQ = dict()
  dictLQ = dict()
  dictCost = dict()
            
  for i in range (0,len(lstInfo)):
        #if empty string got then ignore that line
    if (lstInfo[i]==''):
       continue
        
    #lstNodes =  lstInfo[i].split("\t")
        #print lstNodes
    node1 = lstInfo[i][0].replace(" ","") #node1 and neighbor1 have the ipaddress eg 192.168.8.8        
    neighbor1 = lstInfo[i][1].replace(" ","")
    lq = lstInfo[i][2].replace(" ","") # LQ
    nlq = lstInfo[i][3].replace(" ","") # NLQ
    cost = lstInfo[i][4].replace(" ","") # cost

        #push node1 and node2 to dictNwInfo. The GPS position are randomly given for now
    #random.shuffle(list_GPS_pos) # select a GPS position randomly -> NEED TO UPDATE with exact position later
    #dictPos[node1] = list_GPS_pos[0]
    
    dictNeigh = pushValue2Dict(dictNeigh, node1, neighbor1)
    dictLQ = pushValue2Dict(dictLQ, node1, lq)
    dictNLQ = pushValue2Dict(dictNLQ, node1, nlq)
    dictCost = pushValue2Dict(dictCost, node1, cost)
    #dictAllNodes = pushAllNodeIPs( dictAllNodes, node1, '') # since no position data available , send blank for now.
  #print 'dictAllNodes,dictNeigh, dictLQ, dictNLQ, dictCost'
 # print str(dictAllNodes) #+' \n'+str(dictNeigh)+' \n'+ str(dictLQ)+' \n'+ str(dictNLQ)+' \n'+ str(dictCost)

  return dictAllNodes, dictNeigh, dictLQ, dictNLQ, dictCost





def calcNodeDistance(dictDist, dictNeigh, dictPos):


  dictTemp = dict()
  
  for node in dictNeigh.keys():
    listNeigh = dictNeigh[node]
    
    for i in range (0,len(listNeigh)):

      #check if distance is already calculated for these nodes
      checkNode = str(listNeigh[i])+','+str(node)
      if checkNode in dictTemp.keys():
        nodeDist = dictTemp[checkNode]

      else:

        pos1 = dictPos[node]
        posInfo = pos1.split(',')      
        latitude1 = float(posInfo[0])
        longitude1 = float(posInfo[1])
        alt1 = float(posInfo[2])
        
        pos2 = dictPos[listNeigh[i]]
        posInfo = pos2.split(',')      
        latitude2 = float(posInfo[0])
        longitude2 = float(posInfo[1])
        alt2 = float(posInfo[2])

        nodeDist = distance.distance((latitude1,longitude1,alt1),(latitude2,longitude2,alt2)).meters

        dictTemp[str(node)+','+str(listNeigh[i])] = nodeDist #put into dictTemp so that it can be checked to avoid redundant calculation

      # update dictDist with distance
      dictCost = pushValue2Dict( dictDist, node, nodeDist)

  return dictDist


def kmlLineStyles():# define red blue and green line style
  return '\n<Style id="redLineStyle">  <LineStyle> <color>501400FF</color> <width>5</width> <gx:labelVisibility>1</gx:labelVisibility></LineStyle></Style><Style id="blueLineStyle"><LineStyle> <color>50F00014</color> <width>5</width><gx:labelVisibility>1</gx:labelVisibility> </LineStyle></Style> <Style id="greenLineStyle"> <LineStyle>  <color>5014F000</color> <width>5</width><gx:labelVisibility>1</gx:labelVisibility> </LineStyle></Style>'


def kmlIconStyles():# defines router.png, connected.png,newNode.png and disconnected.png icons
  strIconStyle  = '\n<Style id="router"><IconStyle><color>ff00ff00</color><scale>2</scale><Icon><href>router.png</href></Icon> </IconStyle>'
  strIconStyle += '\n</Style><Style id="connected"><IconStyle><color>ff00ff00</color><scale>1</scale><Icon><href>connected.png</href></Icon> </IconStyle>'
  strIconStyle += '\n</Style><Style id="disConnected"> <IconStyle> <color>ff00ff00</color>  <scale>1</scale><Icon><href>disconnected.png</href></Icon>  </IconStyle> </Style>'
  #strIconStyle += '\n</Style><Style id="justSeen"> <IconStyle> <color>ff00ff00</color>  <scale>1</scale><Icon><href>justSeen.png</href></Icon>  </IconStyle> </Style>'

  return strIconStyle

def definePlacemarkIcon(name,iconStyle,position):
  #iconStyle=[#router,#connected,#disConnected,#justSeen]
  nodeStr = '\n<Placemark><name>'+ name +'</name>'
  nodeStr += '<styleUrl>'+ iconStyle +'</styleUrl>'
  nodeStr += '<Point> <coordinates>'+ position +'</coordinates></Point></Placemark>\n '

  return nodeStr
  
  
def defineLink(description,lineStyle,position1,position2):
  #lineStyle=[#greenLineStyle,#blueLineStyle,#redLineStyle]
  linkStr = '\n<Placemark><description><![CDATA['+ description +']]></description>'
  linkStr += '<styleUrl>'+ lineStyle +'</styleUrl>'
  linkStr += '<LineString><extrude>1</extrude><tessellate>1</tessellate><coordinates>'
  linkStr +=  position1 +' '+ position2
  linkStr += '</coordinates>  </LineString> </Placemark>'
  return linkStr


    
#For each node get the node with best criteria    
def getBestRouter(dictNeigh1,dictLQ1, dictNLQ1, dictCost1,listAllNewNode):
#### deepcopy done  to scope the changes in a variabe as LOCAL
  dictNeigh= copy.deepcopy(dictNeigh1)
  dictLQ = copy.deepcopy(dictLQ1)
  dictNLQ = copy.deepcopy(dictNLQ1)
  dictCost = copy.deepcopy(dictCost1)
  #dictDist = copy.deepcopy(dictDist1)

  printLog(  '-----------------------\n getBestRouter START')

  printLog(  'dictNeigh '+ str(dictNeigh))
  printLog(  'dictLQ '+ str(dictLQ))
  printLog(  'dictNLQ '+ str(dictNLQ))
  printLog(  'dictCost '+str(dictCost))
  
  
  dictBestRouter = dict()
  
  listNeigh = list()
  listNLQ = dict()
  listLQ = dict()
  listCost = dict()
 # listDist = dict()

  for node in listAllNewNode:# for all the nodes in the current nw

    if node not in dictNeigh.keys(): #sometimes dictNeigh may not have node so new router cannot be selected
        return {} # return empty dict
        
 # dictNeigh : add each  new node one by one
   
    listNeigh = dictNeigh[node]
    listNLQ = dictNLQ[node]
    listLQ = dictLQ[node]
    listCost = dictCost[node]
    #listDist = dictDist[node]

    #1. First Check for NLQ criteria -> get the neighbor of node with best NLQ as Best Router
    maxNLQ = max(listNLQ)
   
    
    listMaxIndex = [i for i,v in enumerate(listNLQ) if v == maxNLQ]
    
    
    if len(listMaxIndex)==1: # if only 1 node have maxNLQ select it as NC router
      nodeIndex=listNLQ.index(maxNLQ)
      dictBestRouter[node] = listNeigh[nodeIndex]

      
    else: # remove the data which is not associated with the nodes that have maxNLQ

      neighborCount = len(listNeigh)
      for i in range (0,neighborCount):
        if i not in listMaxIndex:
          listNeigh.pop(i)
          listNLQ.pop(i)
          listLQ.pop(i)
          listCost.pop(i)
          #listDist.pop(i)

      #2. if >1 node have same NLQ then check for best LQ
      maxLQ = max(listLQ)
      listMaxIndex = [i for i,v in enumerate(listLQ) if v == maxLQ]

      if len(listMaxIndex)==1: # if only 1 node have maxLQ select it as NC router
        dictBestRouter[node] = listNeigh[listMaxIndex[0]]
        nodeIndex=listLQ.index(maxLQ)
        dictBestRouter[node] = listNeigh[nodeIndex]
        

      else: # remove the data which is not associated with the nodes that have maxLQ
        neighborCount = len(listNeigh)
        for i in range (0,neighborCount):
          if i not in listMaxIndex:
            listNeigh.pop(i)
            listNLQ.pop(i)
            listLQ.pop(i)
            listCost.pop(i)
            #listDist.pop(i)

        #3. if >1 node have same LQ then check for least cost
        minCost = min(listCost)
        listMinIndex = [i for i,v in enumerate(listCost) if v == minCost]

        if len(listMinIndex)==1: # if only 1 node have minCost select it as NC router
          nodeIndex=listCost.index(minCost)
          dictBestRouter[node] = listNeigh[nodeIndex]


        else: # remove the data which is not associated with the nodes that have minCost
          neighborCount = len(listNeigh)
          for i in range (0,neighborCount):
            if i not in listMinIndex:
              listNeigh.pop(i)
              listNLQ.pop(i)
              listLQ.pop(i)
              listCost.pop(i)
              #listDist.pop(i)

            #4. we dont have any other criteria so select one node randomly
          dictBestRouter[node] = listNeigh[0]
                
  printLog(  'dictBestRouter')
  printLog(  dictBestRouter)

  printLog(  '-----------------------\n getBestRouter END')

  return dictBestRouter
  
  
  
# listSingleReachable and listRouterNode are to be made NC Router
def printNode(dictAllNodes1,dictNeigh1,dictLQ1, dictNLQ1, dictCost1,listSelectedNCRouter,listAllNewNode):
#### deepcopy done  to scope the changes in a variabe as LOCAL
  dictNeigh= copy.deepcopy(dictNeigh1)
  dictLQ = copy.deepcopy(dictLQ1)
  dictNLQ = copy.deepcopy(dictNLQ1)
  dictCost = copy.deepcopy(dictCost1)
  dictAllNodes = copy.deepcopy(dictAllNodes1)
  
  opStr = ''
  listTemp = list()
  iconStyle = '#connected'
  
  #print nodes seen in current network
  for node in dictNeigh.keys():
    iconStyle = '#connected'
    if node in listAllNewNode:
      iconStyle = '#justSeen'
    if node in listSelectedNCRouter:
      iconStyle = '#router'

    if node not in dictAllNodes:# enter blank lat/lon values if node's lat/lon not available
      dictAllNodes[node] = ''
        
    opStr += definePlacemarkIcon(node,iconStyle,dictAllNodes[node])
    listTemp.append(node)

  #print nodes seen befre but not seen in current network
 # Also, if no topology information is received then dislay nodes without links
  for node in dictAllNodes.keys():
    if node not in listTemp:
      opStr += definePlacemarkIcon(node,'#disConnected',dictAllNodes[node])

  return opStr



def printLink(dictAllNodes,dictNeigh,dictLQ, dictNLQ, dictCost):
  opStr = ''
  description = ''
  lineStyle = ''

  for node in dictNeigh.keys():
    listNeigh = dictNeigh[node]
    
    for i in range(0,len(listNeigh)):
      description = ''
      #description for this link
      description += 'From '+ node + ' to '+listNeigh[i]
      description += '\nLQ: '+dictLQ[node][i]
      description += '\nNLQ: '+dictNLQ[node][i]
      description += '\nCost: '+dictCost[node][i]
      #description += '\nDistance: '+str(dictDist[node][i])
      #color for this link
      if(float(dictNLQ[node][i]) > 0.9):
        lineStyle = '#greenLineStyle'
      elif(float(dictNLQ[node][i]) > 0.5):
        lineStyle = '#blueLineStyle'
      else:
        lineStyle = '#redLineStyle'
      if node not in dictAllNodes:# enter blank lat/lon values if node's lat/lon not available
          dictAllNodes[node] = ''
      if listNeigh[i] not in dictAllNodes:
          dictAllNodes[listNeigh[i]] = ''
      opStr += defineLink(description,lineStyle,dictAllNodes[node],dictAllNodes[listNeigh[i]])

  return opStr    
  
        
  
    

def generateKML( hostName, dictAllNodes, dictNeigh, dictLQ, dictNLQ, dictCost,dictPos,listSelectedNCRouter, listAllNewNode):
  print "generateKML()"
  printStr = '<?xml version="1.0" ?> \n <kml xmlns="http://earth.google.com/kml/2.2"> \n <Document>'
  printStr += kmlIconStyles()
  printStr += kmlLineStyles()     
          
  printStr += printNode(dictAllNodes,dictNeigh,dictLQ, dictNLQ, dictCost,listSelectedNCRouter, listAllNewNode)
  printStr += printLink(dictAllNodes,dictNeigh,dictLQ, dictNLQ, dictCost)
  
  printStr += '</Document> \n </kml>'

  #print printStr
  # create a .kml file with the nw information
  kmlFileName = "nw_"+hostName+".kml"
  fo = open(kmlFileName,"w")
  fo.write(printStr)
  fo.close()
    #open the file with dot program
   # os.system("dot -o spaceTimeGraph.ps -T ps "+dotFileName)


def dumpNwDataToFile(listNeigh,hostname):
  
  targetDir = '/var/www/dtnFile'
  if not os.path.exists(targetDir):
    os.makedirs(targetDir)
  
  fo = open(targetDir+"/"+str(hostname),"w")
  fo.write(str(listNeigh))
  fo.close()
  return


#check if the url contains a file. If not then waits until the file exists in  the url
def checkFileExists(url):

  fileExist = False
  #while flag:
  #check for 5 time
  for i in range(0,5):      
  
    try:
      ret = urllib2.urlopen(url)
      #print 'got'
      fileExist = True
    except:
      print 'File Not Found: '+url
      fileExist = False
      time.sleep(1)#wait for 1 seconds

    if fileExist:
        return 1 # File exists

  return 0 # File does NOT exists


def getRemoteFile(nodeIP):

    url = 'http://'+str(nodeIP)+'/dtnFile/'+str(nodeIP) # str() function is applied since sometimes (NOT ALWAYS) it gives error
    #url = 'http://192.168.8.9/dtnFile/192.168.8.9'



    # check if the file exists in the url.
    # if not exist then, go on checking until file exists
    if(checkFileExists(url)==0):
        return 0 # cannot download the file
    
    try:
        file_name = url.split('/')[-1]
        u = urllib2.urlopen(url)
        f1 = open(file_name, 'wb')
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        print "Downloading: %s Bytes: %s" % (file_name, file_size)

        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break

            file_size_dl += len(buffer)
            f1.write(buffer)
            #status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            #status = status + chr(8)*(len(status)+1)
            #print status,

        f1.close()
    except:
        print "Error in file Neighbor downlaod: " +url
        return 0 # some error in file download

    print url +"Downloading Complete"
    return 1 # donwload comptle

#compare criteria of two nodes and returns the best
#link between selectedNewNode and selectedRouter is the best link
def updateSelectedRouter(selectedNewNode, selectedRouter, selectedNLQ, selectedLQ, selectedCost,newNode,valTempNeigh ,valTempNLQ,valTempLQ,valTempCost):
  if(selectedNLQ < valTempNLQ ):
    selectedRouter = valTempNeigh
  elif(selectedNLQ == valTempNLQ):
    if(selectedLQ < valTempLQ ):
      selectedRouter = valTempNeigh
    elif(selectedLQ == valTempLQ):
      if(selectedCost > valTempCost ):
        selectedRouter = valTempNeigh

  # if valTempNeigh is seleected then update other values
  if(selectedRouter == valTempNeigh):
    selectedNLQ = valTempNLQ
    selectedLQ = valTempLQ
    selectedCost = valTempCost
    selectedNewNode = newNode

  return selectedNewNode,selectedRouter,selectedNLQ,selectedLQ,selectedCost

 

#get all the IPs from the file
#get the best NC Router node from the current nw to new nw
# this function procsses all the IPs which are in the nw of remoteNodeIP
def getNCRouter4NewNw(hostName, remoteNodeIP,listAllNewNode,dictNeigh1, dictPrevNeigh1,dictLQ1,dictNLQ1, dictCost1):
# listAllNewNode contains all nodes from one or more nw

  printLog(  '------------------------\n START getNCRouter4NewNw')
  printLog(  'remoteNodeIP: '+str(remoteNodeIP))
  printLog(  'listAllNewNode: '+str(listAllNewNode))
  printLog(  'dictNeigh1: '+ str(dictNeigh1))
  printLog(  'dictPrevNeigh1: '+ str(dictPrevNeigh1))
  printLog(  'dictLQ1: '+str(dictLQ1))
  printLog(  'dictNLQ1: '+str(dictNLQ1))
  printLog(  'dictCost1: '+ str(dictCost1))
  #print 'dictDist1: '+ str(dictDist1)
  

#### deepcopy done  to scope the changes in a variabe as LOCAL
  dictNeigh= copy.deepcopy(dictNeigh1)
  dictPrevNeigh= copy.deepcopy(dictPrevNeigh1)
  dictLQ = copy.deepcopy(dictLQ1)
  dictNLQ = copy.deepcopy(dictNLQ1)
  dictCost = copy.deepcopy(dictCost1)
#  dictDist = copy.deepcopy(dictDist1)
  
#declaration
  listTempNeigh  = list()
  listTempNLQ = list()
  listTempLQ = list()
  listTempCost = list()
  

#initialization
  selectedNLQ = 0 # set to minimum  value
  selectedLQ = 0 # set to minimum  value
  selectedCost = 999999 # set to maximum  value
  #selectedDist = 999999 # set to maximum  value
  #selectedNeighCount = 0 # set to minimum  value
  selectedRouter = '' #leave blank or INITIALIZE to any node of prev nw which is neigh of node
  selectedNewNode = hostName # initialize selectedNewNode, if not initialized as hostName then sometimes selectedNewNode is returned null

  if( getRemoteFile(remoteNodeIP)==0):
      return '','',[], 0 #cannot download the fileSo return everything empty
      ## the last value =0 means operation  NOT successful
  f = open(remoteNodeIP,"r")
  dataLine= f.readline()
  f.close()

  
# listNewIPs(all new nodes from only ONE of the new nw) is subset of listAllNewNode.
# listAllNewNode contains all nodes from one or more nw
  listNewIPs = (dataLine[2:-2].replace("'","")).split(', ')# need to take care of space also while splitting
 # print 'dictPrevNeigh.keys():'+str(dictPrevNeigh.keys())
  printLog(  'listNewIPs downloaded: '+ str(listNewIPs))
  #dictBestCandidate = getBestRouter(dictNeigh,dictLQ, dictNLQ, dictCost,dictDist)

  listNewIPs = list(set(listNewIPs) - set(dictPrevNeigh.keys())) # remove nodes from the host node network
  if hostName in listNewIPs:
      listNewIPs.remove(hostName)
  printLog(  "listNewIPs filtered: "+str(listNewIPs))
  printLog(  "FOR LOOP START: ")

  # get the best Router, from the current nw, for each of the nodes in listNewIPs
  for node in listNewIPs:

    printLog(  "FOr node: "+ str(node))
    
    if node not in dictNeigh.keys():
      break
    
    # get list of neigh of node-> listTempNeigh, also get NLQ, LQ, Cost
    #print 'dictNeigh '+ str(dictNeigh)
    listTempNeigh = dictNeigh[node]
    listTempNLQ = dictNLQ[node]
    listTempLQ = dictLQ[node]
    listTempCost = dictCost[node]
    
   # print 'for node in listNewIPs: \n node ' + node


    if (len(set(listTempNeigh) - set(listNewIPs))!=0):    
        #remove from listTempNeigh,  all other ip present in listNewIPs (also from NLQ, LQ, Cost)
        #listTempNeigh = list( set(listTempNeigh) - set(listNewIPs) )# may not preserve order so do by finding index
        #get the index of element to be removed
        listRemoveIndex =list()
        for i in range (0,len( listTempNeigh)):
          for j in range (0,len(listNewIPs)):
            if (listTempNeigh[i] == listNewIPs[j]):
              listRemoveIndex.append(i)
        printLog(  'listRemoveIndex:'+str(listRemoveIndex))
        printLog(  'listTempNeigh' +str(listTempNeigh))
        
        for i in range (len(listRemoveIndex)-1,-1,-1):# the loop is done in a reverse way since we are poping item from the list, If loop is parsed in forward manner then pop(0 will get problem
          listTempNeigh.pop(listRemoveIndex[i])
          listTempNLQ.pop(listRemoveIndex[i])
          listTempLQ.pop(listRemoveIndex[i])
          listTempCost.pop(listRemoveIndex[i])
      
  #  print 'listTempNeigh after' +str(listTempNeigh)

    # if the new node does not have any neighbor from the host network then break
    if(len(listTempNeigh)==0):
      printLog(  '(len(listTempNeigh)==0)')

      dictBestCandidate = getBestRouter(dictNeigh,dictLQ, dictNLQ, dictCost,[hostName])

      return dictBestCandidate[hostName],hostName,[]
          
      #DO SOMETHING to handle this case############################
      break

    
    for i in range(0,len(listTempNeigh)):
            # save selectedNLQ....... of the selectedRouter
      if listTempNeigh[i] in listNewIPs: # if <node> and listTempNeigh[i] not from different network then skip it
          continue
      selectedNewNode,selectedRouter,selectedNLQ, selectedLQ, selectedCost = updateSelectedRouter(selectedNewNode,selectedRouter,selectedNLQ, selectedLQ, selectedCost,node,listTempNeigh[i],listTempNLQ[i],listTempLQ[i],listTempCost[i])
      
      printLog(  '[selectedRouter <IN FOR> selectedNewNode]')
      printLog(  selectedRouter +' ---  '+ selectedNewNode)

  printLog(  '[selectedRouter <OUTSIDE FOR> selectedNewNode]')
  printLog(  selectedRouter +' ---  '+ selectedNewNode)
  
  #now remove the node ip that are processed above
  
  listAllNewNode = list(set(listAllNewNode) - set(listNewIPs) ) ## test the data in 3 by skipping this line when router is blank



  printLog(  ' END getNCRouter4NewNw \n------------------------')

  return selectedNewNode,selectedRouter,listAllNewNode,1 # the last value =1 means operation successful


#1. compare the two lists and get the lat,lon which is common in both of the list
#2. if no common lat,lon in both then gets a lat,lon from listPoints1 which is nearest to listPoints2
def selectCandidateCoordinate(listPoints1,listPoints2):
    #listPoints1 : list of lat,lon,altitude
    #listPoints2 : list of lat,lon,altitude     
    
    pointDist = 10000 # initialize to a large value
    shortestDist = 10000 # initialize to a large value
    selectedLat = None
    selectedLon = None 
    for i in range(0, len( listPoints1)):        
        for j in range(0, len( listPoints2 )):            
            
            pointDist = distance.distance((listPoints1[i].lat,listPoints1[i].lon),(listPoints2[j].lat,listPoints2[j].lon)).meters
            
            if (pointDist==0):
               # print  str(i)+'.'+str(j)+' ZERO'
                selectedLat = listPoints1[i].lat
                selectedLon = listPoints1[i].lon
                return selectedLat,selectedLon # if two list have the same lat, lon then return that point
            
            elif(pointDist < shortestDist):
                #print  str(i)+'.'+str(j)+' SHORTEST'
                shortestDist = pointDist
                selectedLat = listPoints1[i].lat
                selectedLon = listPoints1[i].lon
                
    return selectedLat,selectedLon # if two list have the same lat, lon then return a  point in  listPoints1 which is nearest to a point in listPoints2
        


def findCircleCoordinates(lat, lon, radius):
    
    placemarkStr = ''
    # How many points do we want? (should probably be function param..)
    numberOfPoints = 100
    anglePerPoint = (2 * math.pi )/ numberOfPoints
    
    # Keep track of the angle from centre to radius
    currentAngle = 0

    # The points on the radius will be lat+x2, lon+y2
    x2 = 0
    y2 = 0
    # Track the points we generate to return at the end
    listPoints = list()

    for i in range(0,numberOfPoints):
            
        # X2 point will be cosine of angle * radius (radius)
        x2 = math.cos(currentAngle) * radius
        # Y2 point will be sin * radius
        y2 = math.sin(currentAngle) * radius

        newLat = lat+x2
        newLon = lon+y2
        pos = GPSPosition(newLat,newLon,0)
        # save to our results array
        listPoints.append(pos)
        # Shift our angle around for the next point
        currentAngle += anglePerPoint
    
    # Return the points we've generated
    return listPoints

def getHopCount(dictNeigh, node1, node2):
    
    hopCount = 0
    #if node1 not in dictNeigh.keys():
       # return 0
    if node1 not in dictNeigh.keys():
        return 0
    
    listNodes = copy.deepcopy(dictNeigh[node1])
   # print 'listNodes ' + str(listNodes)
    listNodeParsed = copy.deepcopy(dictNeigh[node1])
    listNodeParsed.append(node1) # put self node as parsed
    
    listPrevNodes = copy.deepcopy(dictNeigh[node1])

    for i in range (0, len(dictNeigh.keys())):

        if node2 in listNodes:
            hopCount = i +1
            #print 'hopCount'+str(hopCount)
            return hopCount

        else:            
            for node in listPrevNodes: # copy all 1 hop neighbor of immediate neighbor             
                listNodes = copy.deepcopy(list( set(listNodes) | set(dictNeigh[node]) ))

            listNodes = copy.deepcopy(list(set(listNodes) - set(listNodeParsed))) # remove the nodes already seen
            listNodeParsed = copy.deepcopy(list(set(listNodeParsed) | set(listNodes))) # | is union operator
            listPrevNodes = copy.deepcopy(listNodes)
            
        
    return 0  #if node1 not in dictNeigh.keys():

       
def checkDirectConnnection(dictNeigh, listAllNewNode, hostName):
    for newNode in listAllNewNode:
        if (getHopCount(dictNeigh, newNode, hostName)==1):
            return True # direct connection between new node with hostName
                
    return False # no direct connection of the new node with hostName
                      

def updateCommonPoints(listCommonPoints,listPoints, distanceApproximation=0):
    #listCommonPoints and listPoints: list of lat,lon,altitude
    #distanceApproximation: consider the points within a range of distanceApproximation meters
    
    # at first, listCommonPoints is empty , so return all listPoints
    if(len(listCommonPoints)==0):
        return listPoints

    listSelectedPoints = list()    
    pointDist = 10000 # initialize to a large value
    shortestDist = 10000 # initialize to a large value

    for i in range(0, len( listCommonPoints)):        
        for j in range(0, len( listPoints )):            
            
            pointDist = distance.distance((listCommonPoints[i].lat,listCommonPoints[i].lon),(listPoints[j].lat,listPoints[j].lon)).meters
            
            if (pointDist==0):
                #print  str(i)+'.'+str(j)+' ZERO'
                selectedLat = listCommonPoints[i].lat
                selectedLon = listCommonPoints[i].lon
                pos = GPSPosition(selectedLat,selectedLon,0)
                listSelectedPoints.append(pos)
                #return selectedLat,selectedLon # if two list have the same lat, lon then return that point
                
            elif(pointDist <= distanceApproximation ):
                selectedLat = listCommonPoints[i].lat
                selectedLon = listCommonPoints[i].lon
                pos = GPSPosition(selectedLat,selectedLon,0)
                listSelectedPoints.append(pos)
            
            elif(pointDist < shortestDist):
                #print  str(i)+'.'+str(j)+' SHORTEST'
                shortestDist = pointDist
                selectedLat = listCommonPoints[i].lat
                selectedLon = listCommonPoints[i].lon
                pos = GPSPosition(selectedLat,selectedLon,0)
                listSelectedPoints.append(pos)
       
    return listSelectedPoints


def getNodeForGivenHop(node,hopCount,dictNeigh):

    listNodes = list()

    if (hopCount==1):
        return dictNeigh[node]
    else:
        for node1 in dictNeigh.keys():
            if(getHopCount(dictNeigh, node, node1)== hopCount):
               listNodes.append(node1)
               
    return listNodes


def arrangeUnknownList(listParsed,listUnknown, dictNeigh):
    listOrdered =  list()

    for node in listParsed:
        if node in dictNeigh.keys():
            for node1 in dictNeigh[node]:
                if node1 in listUnknown:
                    listOrdered.append(node1)
                    listParsed.append(node1)
                    del listUnknown[listUnknown.index(node1)]
                if(len(listUnknown) ==0):
                    return listOrdered
        

#1. get the point from a list of listCommonPoints by comparing the hop distance between the known nodes
#2. if no point got from (1) then return listCommonPoints[0]
def estimateNodePositions(node,listCommonPoints,dictKnownPos,dictNeigh,hopDistance):
    
    pos = listCommonPoints[0] # initialize
    selectedPoints = list()

    for pos in listCommonPoints:
        for node1 in dictKnownPos.keys():
            hopCount = getHopCount(dictNeigh, node, node1)
            
            pos1 = dictKnownPos[node1]
            posInfo = pos1.split(',')      
            latitude1 = float(posInfo[0])
            longitude1 = float(posInfo[1])
            alt1 = float(posInfo[2])                
                
            nodeDist = distance.distance((latitude1,longitude1,alt1),(pos.lat,pos.lon,pos.alt)).meters

            if ( nodeDist>= (hopCount * hopDistance)):
                selectedPoints.append(pos)

    if(len(selectedPoints)>0):
        #select a randdom point
        pos = selectedPoints[random.randrange(len(selectedPoints))]
        
    return pos



def assignRandomNodePosition(listAllNodes):
    # no need of the geopy module in this case
    #print 'assignRandomNodePosition'
    
    dictRandomPos= dict()
    list_GPS_pos=["100.012796667,14.0085683333,0","100.112796667,14.0085683333,0","100.05128,14.018545,0","100.15128,14.118545,0","100.1129,14.02849,0","100.2129,14.22849,0","100.1525,14.0385693333,0","100.21244,14.048545,0","100.25233,14.07849,0","100.012,14.008,0","100.112,14.008,0","100.051,14.018,0","100.151,14.118,0","100.11,14.02,0","100.21,14.22,0","100.152,14.033,0","100.21,14.048545,0","100.25,14.07849,0"]

    #The GPS position are randomly given 
    random.shuffle(list_GPS_pos) # select a GPS position randomly 
    for i in range(0, len(listAllNodes)):
        #print dictNeigh[i]
        dictRandomPos[listAllNodes[i]] = list_GPS_pos[i]    

    return dictRandomPos


# dictKnownPos: contains position of known nodes, dictKnownPos is similar to dictPos and dictAllNodes
# hostNodePosition: this node position, hostName:this node ip(e.g.: 192.168.8.6)
# distanceScaleValue
def assignNodePosition(dictNeigh,dictKnownPos,hostNodePosition,hostName,distanceScaleValue):    

    listPoints = list()
    listCommonPoints1 = list()
    listCommonPoints2 = list()
    listOneHopNodes = list()
    listTwoHopNodes = list()
    '''
    print "\n"
    print 'dictNeigh',
    print dictNeigh
    print 'dictKnownPos',
    print dictKnownPos
    print "\n"
    '''
    
    #1. Fix known nodes to their position <dictKnownPos>
    if (len(dictKnownPos.keys())==0): # if position of NONE of the nodes is not known , assign some position to this host node
        dictKnownPos[hostName] = hostNodePosition #"100.012796667,14.1085683333,0"
    

    #2. get list of nodes whose position is not known <listUnknownPos = dictNeigh.keys() - dictKnownPos.keys()>
    listUnknownPos = list(set(dictNeigh.keys()) - set(dictKnownPos.keys()))
    #listUnknownPos= []

    if ((listUnknownPos == None) or (listUnknownPos==[])): # handle NoneType error: if listUnknownPos is empty error is got <TypeError: 'NoneType' object is not iterable>
        #check if all nodes have got position, if not assign DUMMY values hostNodePosition to all nodes<THIS shud not happen>
        if(len(dictKnownPos.keys()) < len(dictNeigh.keys())):
            for echNode in dictNeigh.keys():
                dictKnownPos[echNode] = hostNodePosition # just DUMMY value (may be unrealistic value which makes the program run for current Generation only. In next generation the program gets NORMAL)
        return dictKnownPos
    
    #3. calculate positions
    # first order listUnknownPos so that the nodes nearest to dictKnownPos will be parsed before the node farther
    listUnknownPos = arrangeUnknownList(dictKnownPos.keys(),listUnknownPos, dictNeigh)
    
    try:
        for node in listUnknownPos:
            
            listCommonPoints1 = []
            listCommonPoints2 = []
            listOneHopNodes = getNodeForGivenHop(node,1,dictNeigh)
            listTwoHopNodes = getNodeForGivenHop(node,2,dictNeigh)
            oneHopNodeCnt = 0
            twoHopNodeCnt = 0

            #check for all node position in 1 hop
            for knownNode in dictKnownPos.keys():
                if knownNode in listOneHopNodes:
                    hopCount = 1
                #3.1 get hopCount of reference known node and unknown node.
                #hopCount = getHopCount(dictNeigh, node, knownNode)
                    circleRadius = hopCount * distanceScaleValue #0.001 #0.001 = 100 meters approx
                #3.2 listPoints = findCircleCoordinates(known node's lat/lon, hopCount)
                    knownPos = dictKnownPos[knownNode]
                    posInfo=knownPos.split(',')
                
                    listPoints = findCircleCoordinates(float(posInfo[0]), float(posInfo[1]), circleRadius)

                #3.3 update the listCommonPoints
                    listCommonPoints1 = updateCommonPoints(listCommonPoints1,listPoints)

                    oneHopNodeCnt += 1

                    if (oneHopNodeCnt==3): # return any point in listCommonPoints1 as position of node

                        pos = estimateNodePositions(node,listCommonPoints1,dictKnownPos,dictNeigh, distanceScaleValue*100000) #estimation is (distanceScaleValue*100000) =  1 hop distance 
                        dictKnownPos[node] = str(pos.lat) +','+ str(pos.lon) +',0'
                        break
                    
            if(oneHopNodeCnt < 3):
            #check for all node position in 2 hop
                
                for knownNode in dictKnownPos.keys():
                    #print 'dictKnownPos: '+ str(dictKnownPos)
                    if knownNode in listTwoHopNodes:
                        hopCount = 2
                        circleRadius = hopCount * distanceScaleValue#0.001 #0.001 = 100 meters approx
                        knownPos = dictKnownPos[knownNode]
                        posInfo=knownPos.split(',')
                       # print 'node knownnode posInfo'
                        #print node+' '+ knownNode +' '+ str(posInfo)
                    
                        listPoints = findCircleCoordinates(float(posInfo[0]), float(posInfo[1]), circleRadius)
                        listCommonPoints2 = updateCommonPoints(listCommonPoints2,listPoints)
                        twoHopNodeCnt += 1

                        if (twoHopNodeCnt==2): # return any point in listCommonPoints1 as position of node
                            selectedLat,selectedLon = selectCandidateCoordinate(listCommonPoints1,listCommonPoints2)
                            dictKnownPos[node] = str(selectedLat) +','+ str(selectedLon) +',0'
                            break

                if (twoHopNodeCnt==0):# return any point in listCommonPoints1 as position of node             
                    pos = estimateNodePositions(node,listCommonPoints1,dictKnownPos,dictNeigh, distanceScaleValue*100000) #estimation is (distanceScaleValue*100000) =  1 hop distance 
                    dictKnownPos[node] = str(pos.lat) +','+ str(pos.lon) +',0'
                else: # case of twoHopNodeCnt==1
                    selectedLat,selectedLon = selectCandidateCoordinate(listCommonPoints1,listCommonPoints2)# check hop distance between the known nodes 
                    dictKnownPos[node] = str(selectedLat) +','+ str(selectedLon) +',0'
    except:
        printLog(  "%%%%%%%%%%%%%%%% \n expection in assignNodePosition")
        # handle NoneType error: if listUnknownPos is empty error is got <TypeError: 'NoneType' object is not iterable>
        #check if all nodes have got position, if not assign DUMMY values hostNodePosition to all nodes<THIS shud not happen>
        if(len(dictKnownPos.keys()) < len(dictNeigh.keys())):
            for echNode in dictNeigh.keys():
                dictKnownPos[echNode] = hostNodePosition # just DUMMY value (may be unrealistic value which makes the program run for current Generation only. In next generation the program gets NORMAL)
        return dictKnownPos

    return dictKnownPos
                

# get the average of all the nodes distance with respect to their hop count
def estimateHopDistance(dictKnownPos,dictNeigh):

    totalDist = 0
    totalHop = 0

    for node in dictKnownPos.keys():
        for node1 in dictKnownPos.keys():
            if (node != node1):                
                hopCount = getHopCount(dictNeigh, node, node1)             

                pos1 = dictKnownPos[node]
                posInfo = pos1.split(',')      
                latitude1 = float(posInfo[0])
                longitude1 = float(posInfo[1])
                alt1 = float(posInfo[2])
        
                pos2 = dictKnownPos[node1]
                posInfo = pos2.split(',')      
                latitude2 = float(posInfo[0])
                longitude2 = float(posInfo[1])
                alt2 = float(posInfo[2])
                
                nodeDist = distance.distance((latitude1,longitude1,alt1),(latitude2,longitude2,alt2)).meters                
                totalDist += nodeDist
                totalHop += hopCount

    estimatedDist = totalDist/totalHop
    return estimatedDist



# get the LINK parameters between  ncRouterNode and selectedNewNode
def getRouterLinkParameters(ncRouterNode,selectedNewNode,dictNeigh ,dictLQ,dictNLQ, dictCost):
    
    if (ncRouterNode == selectedNewNode): # this shud not occur, but anyway checking
        return dict()
    
    dictLinkParameters = dict()
    nbrIndex = (dictNeigh[ncRouterNode]).index(selectedNewNode)
    linkKey = ''# order the link key in ascending order (from smaller node to bigger node. FOr eg: 192.168.8.2 -> 192.168.8.9 . Not192.168.8.9 -> 192.168.8.2
    #
    if(ncRouterNode < selectedNewNode):
        linkKey = ncRouterNode+'->'+selectedNewNode
    else:
        linkKey = selectedNewNode+'->'+ncRouterNode
    #if linkKey not in dictLinkParameters.keys():
    dictLinkParameters[linkKey] = dictLQ[ncRouterNode][nbrIndex]+','+dictNLQ[ncRouterNode][nbrIndex]+','+dictCost[ncRouterNode][nbrIndex]

    return dictLinkParameters    
    
    
    
    

    






    
