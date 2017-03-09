#Program to select best Router for new nodes joining the OLSR network
#Author: Bidur Devkota

# /usr/bin/python


import socket, sys, time, datetime , os, copy,random,urllib2 , commands, math, datetime
#from geopy import distance

import networkTopologyModule as ntm


class NetworkTopology:
    
    def __init__(self):
        
        self.hostName = ntm.getHostIPAddress()# works if the host have only one IP other than localhost
        self.hostNodePosition = "100.012796667,14.1085683333,0"         #Assign host node position, if no GPS
        self.olsrIP = '127.0.0.1'
        self.txtInfoPort = 2006
        self.ignoreGenerations = 5 # When this program starts then for generation < = ignoreGenerations, the router selection program will not be active. During these initial generations then nodes will initialise their neighbors
        self.dataInterval = 5   # 5 seconds
        self.activeRouterInterval = 10 # 60 seconds
        self.listSelectedNCRouter = [] # initialize selected routers to None
        self.listRouterParameters = [] # initialize selected routers to None
        self.newNodeDiscoveryInterval = 60 # 60 seconds => A node is taken as a NEW NODE, If the node is seen in the nw after the interval of newNodeDiscoveryInterval  
        self.transientInterval = 10
        #url = 'http://'+nodeIP+'/dtnFile/'+nodeIP # getRemoteFile() uses this url

        self.targetDir = '/var/www/dtnFile' # target directory to dump the neighbor file
  
        # distance scale value is the rough estimate of 1 hop distance
        self.distanceScaleValue = 0.01 #0.001 = 100 meters approx . In assignNodePosition(), distanceScaleValue is multiplied with constant to get 1 hop distance.
                                                        #CHECK Resultant Distance


    def getSelectedRouters(): # returns the list of selected routers within activeRouterInterval else return empty list
        return self.listSelectedNCRouter


    def isNCRouter(): # returns the list of selected routers within activeRouterInterval else return empty list
        if self.hostName in self.listSelectedNCRouter:
            return True
        else:
            return False


    def getSelectedRouterParameters(): #returns the link quality parameters of selected Router Link
        return self.listRouterParameters
        
       
    def topologyMain(self):
    
      print "Reading txtinfo at an interval of "+str(self.dataInterval)+" seconds"
      generation = 0

      ntm.dumpNwDataToFile([self.hostName],self.hostName)# initialize by sending own hostName
      


      listAllNwInfo = list() # data of dictNwInfo for each generation is maintained
      listAllNewNode = list()
     # listSelectedNCRouter = list()
      dictPos = dict()
      dictNeigh = dict()# neighbor in Current Generation
      dictLQ = dict()
      dictNLQ = dict()
      dictCost = dict()
      dictDist = dict()
      dictAllNodes = dict() # nodes seen till now with their lastet known position
      dictPrevNeigh = dict() # neighbor in previous Generation
      dictPrevNeigh[self.hostName] = self.hostName #initialization
      dictNCRouterSelected = dict() # key value pair of generation -> listSelectedNCRouter
      dictKnownPos = dict()
      dictLostNodes = dict() # key value pair of NODE -> disconnection time

      isBlankRouter = False
      
      #initilaise so that new node discovery is possible
      lastLiveTimeOfNetwork = time.time() - (2 * self.newNodeDiscoveryInterval) # last time when this hostName had seen at least 1 neighbor
      
      

      
      while True:
        #print current Datetime to logFile.
        now1 = datetime.datetime.now()
        now_text = now1.strftime("%Y-%m-%d %H:%M")
        ntm.printLog(now_text)

        ntm.printLog(  str(generation)+ "> new generation")
        


        #print "lastLiveTimeOfNetwork: "+ str(lastLiveTimeOfNetwork)

        ntm.printLog( "<< START WHILE >>")

        txtInfo = ntm.GetOLSRtxtInfo(self.olsrIP, self.txtInfoPort,generation)#returns a list of list
       # txtInfo is returned such that the link parameters have same value both way (i.e. 192.168.8.2 -> 192.168.8.9 = 192.168.8.9 -> 192.168.8.2)

        if txtInfo is None: #Handled the case when txtInfo is 'none' < TypeError: object of type 'NonType' has no len()>if txtInfo is None:
          ntm.dumpNwDataToFile([self.hostName],self.hostName)# initialize by sending own self.hostName
          print "No TOPOLOGY INFORMATION REVEICED"
         # dictPrevNeigh = {} # clear dictPrevNeigh if disconnection time is long enough
          
          if(ntm.isNewNodeDiscoveryIntervalExpired(self.newNodeDiscoveryInterval, lastLiveTimeOfNetwork)):
              dictPrevNeigh = {} # clear dictPrevNeigh if disconnection time is long enough
          continue
          

        #  handle transiant condition: check if any new nodes ? if yes, pause for some time and get txtinfo again
        if (generation >0):
            txtInfo,listAllNewNode = ntm.checkAndHandleTransiantCondition(txtInfo,self.transientInterval,self.hostName, dictPrevNeigh.keys(),self.olsrIP, self.txtInfoPort,generation, dictLostNodes, self.newNodeDiscoveryInterval,lastLiveTimeOfNetwork)
            
        if txtInfo is not None:
          print str(generation)+ "> Start"
          #print txtInfo
          
          #0 make the dict empty
          dictPos = {}
          dictNeigh = {}
          dictLQ =  {}
          dictNLQ =  {}
          dictCost = {}
          dictDist =  {}
          dictKnownPos = {}

          self.listSelectedNCRouter =[]
          self.listRouterParameters =[]
          

          
          #1. extract network data
          dictAllNodes, dictNeigh, dictLQ, dictNLQ, dictCost = ntm.extractNetworkData(txtInfo, dictAllNodes)


          listLostNodes = list(set(dictAllNodes.keys()) - set(dictNeigh.keys()))
         # print 'listLostNodes' + str(listLostNodes)
          
          if((len(dictNeigh.keys()) == 0 )or( self.hostName in  listLostNodes)):
              print "NEIGHBOR List empty"
              #dictPrevNeigh = {} # clear dictPrevNeigh if disconnection time is long enough
             
              if(ntm.isNewNodeDiscoveryIntervalExpired(self.newNodeDiscoveryInterval, lastLiveTimeOfNetwork)):
                  dictPrevNeigh = {} # clear dictPrevNeigh if disconnection time is long enough

              #print dictAllNodes without links
              ntm.generateKML(self.hostName, dictAllNodes, dictNeigh, dictLQ, dictNLQ, dictCost,dictPos, self.listSelectedNCRouter, listAllNewNode)

              continue
                
          # check if nodes disconnected in this generation, if disconnected then save the time of disconnection   
          if(listLostNodes):
              print "Connection lost with: "+ str(listLostNodes)
              for  lostNode in listLostNodes:
                  if ((lostNode in dictPrevNeigh.keys()) & (lostNode not in dictNeigh.keys() )):
                      dictLostNodes [lostNode] = time.time() # disconnection time of lostNode saved

          
          #1.1 assign the node position
          # update GPS position of known nodes
          dictKnownPos[self.hostName] = self.hostNodePosition
          #dictKnownPos['192.168.8.3'] = '100.022796667,14.1085683333,0'

          #print dictKnownPos
          
          if(len(dictKnownPos.keys())>1):# if position of more than 1 node is known then calculate hop distance
              estimatedDist4oneHop = ntm.estimateHopDistance(dictKnownPos,dictNeigh)
              distanceScaleValue = estimatedDist4oneHop/100000
              #print 'estimatedDist4oneHop'+ str(estimatedDist4oneHop)


          #print dictNeigh
          #print '*********************************************'
          dictPos = ntm.assignNodePosition(dictNeigh,dictKnownPos,self.hostNodePosition,self.hostName,self.distanceScaleValue)

          
          
          # update the node position of the currently got nodes in dictAllNodes from dictPos
          for node in dictPos:
              dictAllNodes[node] = dictPos[node]


        
          #2. calculate distance between conneted nodes
          dictDist = ntm.calcNodeDistance(dictDist, dictNeigh,dictPos)


          ntm.printLog( "dictNeigh.keys(): " + str(dictNeigh.keys()))
          ntm.printLog( "dictPrevNeigh.keys(): " + str(dictPrevNeigh.keys()))
          print  "Current Neighbors : " + str(dictNeigh.keys())
          print  "Previous Neighbors: "+  str(dictPrevNeigh.keys())
          

          
         # checkDirectConnnection(): if the hostName is Directly connected (i.e. 1 hop) with NEW node  AND hostNode is disconnected for long time THEN router selection is done        
         #len(listAllNewNode)>0 : TRUE when the hostNode have NEW neighbor
         #(len(dictPrevNeigh.keys())>0): TRUE when the hostNode had non-empty neighbor list in previous generation
         #(len(dictPrevNeigh.keys())==0): TRUE when hostNode was alone (empty-neighbor) in previous generation
          if (( ntm.checkDirectConnnection(dictNeigh, listAllNewNode, self.hostName)) and ( (len(listAllNewNode)>0) and ( ( (len(dictPrevNeigh.keys())>0))
                        or ((len(dictPrevNeigh.keys())==0) and  ntm.isNewNodeDiscoveryIntervalExpired(self.newNodeDiscoveryInterval, lastLiveTimeOfNetwork)) ) )):

         # if ( ntm.checkDirectConnnection(dictNeigh, listAllNewNode, self.hostName)):
             # If only ONE NEW node is seen to by the host. Then check the neighbor list of the new node and make sure about it.
             # This MUST be done Because sometimes there may be more than ONE node
              if(len(listAllNewNode) ==1 ):
                  
                  if(ntm.getRemoteFile(listAllNewNode[0])==0):
                      continue # restart the operation
                  
                  f = open(listAllNewNode[0],"r")
                  dataLine= f.readline()
                  f.close()
                  listNewNodes = (dataLine[2:-2].replace("'","")).split(', ')

                  ntm.printLog( 'listNewNodes FILE: '+ str(listNewNodes))

                  if self.hostName in  listNewNodes:
                      listNewNodes.remove(self.hostName)
                  ntm.printLog( 'listNewNodes - HOST: '+ str(listNewNodes))

                  if(len(dictPrevNeigh.keys())==0):
                      ntm.printLog( 'if(len(dictPrevNeigh.keys())==0):')
                      listAllNewNode = copy.deepcopy(listNewNodes)
                      ntm.printLog( 'listNewNodes:: '+ str(listNewNodes))
                      
                  
                  elif(len(set(listNewNodes)- set(dictPrevNeigh.keys()))>1):
                      ntm.printLog( "HANDLE THIS CASE AS NEW NETWORK NOT NODE=1")
                      #listAllNewNode = copy.deepcopy(listNewIPs)
                      ntm.printLog( "listNewNodes::: "+str(listNewNodes))

                      ntm.printLog( "Now restart the algorithm since there are more NEW nodes to be seen by this host")

                      continue # Now restart the algorithm since there are more NEW nodes to be seen by this host,



                  
            #'''
             #   1 NEW NODE JOINS THE NETWORK
            #'''
              #if only one node joned the network then get the best node as NC router for the new node
              if((len(listAllNewNode) ==1 ) & (generation > self.ignoreGenerations)):
                  
                print '1. New Node = 1'

            
                
                
                dictBestCandidate = ntm.getBestRouter(dictNeigh,dictLQ, dictNLQ, dictCost,listAllNewNode)
                #print 'best: '+ dictBestCandidate[listAllNewNode[0]]

                if (len(dictBestCandidate.keys())==0):# sometime router cant be selected since the hostName does not have new node information in topology table data (Happens sometimes after Transient Time wait)
                    continue # so restart the process again
              

                self.listSelectedNCRouter.append(dictBestCandidate[listAllNewNode[0]])# select best Router for the new node 
                self.listSelectedNCRouter.append(listAllNewNode[0]) # select the new node as router itself

                #GET THE PARAMETER BETWEEN THE newNode and dictBestCandidate[listAllNewNode[0]] -> needed for election            
                self.listRouterParameters.append(str(ntm.getRouterLinkParameters(dictBestCandidate[listAllNewNode[0]],listAllNewNode[0],dictNeigh ,dictLQ,dictNLQ, dictCost)))

            #'''
               # MANY NEW NODES JOINS THE NETWORK
            #'''
              elif ((len(listAllNewNode) > 1) & (generation > self.ignoreGenerations)):
                
                print '2. New Node > 1 (may be one or more network)'
                #print 'dictPrevNeigh '+  str(dictPrevNeigh)

                if (len(dictPrevNeigh.keys())==0):
                    
                    ntm.printLog("(len(dictPrevNeigh.keys())==0): \n call getBestRouter() \n")
                    
                    dictBestCandidate = ntm.getBestRouter(dictNeigh,dictLQ, dictNLQ, dictCost,[self.hostName])
                    if (len(dictBestCandidate.keys())==0):# sometime router cant be selected since the hostName does not have new node information in topology table data (Happens sometimes after Transient Time wait)
                        continue # so restart the process again

                    selectedNewNode = dictBestCandidate[self.hostName]
                    ncRouterNode = self.hostName
                
                    self.listSelectedNCRouter.append(dictBestCandidate[self.hostName])# select best Router for the new node 
                    self.listSelectedNCRouter.append(self.hostName) # select the new node as router itself

                    #GET THE PARAMETER BETWEEN THE newNode and dictBestCandidate[listAllNewNode[0]] -> needed for election            
                    self.listRouterParameters.append(str(ntm.getRouterLinkParameters(dictBestCandidate[self.hostName],self.hostName,dictNeigh ,dictLQ,dictNLQ, dictCost)))

                else:
                #Need to iterate this until  listAllNewNode becomes empty
                    for remoteNodeIP in listAllNewNode:  
                  #remoteNodeIP= '192.168.8.9'
                  #get all the IPs from the file                 

                   # if all the new nodes are in same nw then getNCRouter4NewNw is called only once
                  #get the best NC Router node from the current nw to new nw (the link selectedNewNode to ncRouterNode is the best link)
                      selectedNewNode, ncRouterNode,listAllNewNode,operationStatus = ntm.getNCRouter4NewNw(self.hostName,remoteNodeIP,listAllNewNode,dictNeigh, dictPrevNeigh,dictLQ,dictNLQ, dictCost)
                      if (operationStatus==0):# remote file cannot be downloaded # need to continue
                          ntm.printLog( " operationStatus==0 \n ncRouterNode BLANK ")
                      
                  # if the getNCRouter4NewNw cant find any router then set this computer as router since it is connected

                  #BUT this should not happen : SOMETIMES ncRouterNode IS BLANK => THEN RESTART THE PROCESS AGAIN
                      isBlankRouter = False
                      if ncRouterNode=='': 
                        #ncRouterNode = self.hostName
                        ntm.printLog( "____________________________ \n ncRouterNode BLANK \n BLANK\n")
                        isBlankRouter = True
                    
                        break #########THIS GOES TO FOR LOOP, BUT I WANT IT to refer to WHILE loop. So isBlankRouter is checked for handling with the WHILE loop
         

                      if ncRouterNode not in self.listSelectedNCRouter:# checking here since if this node is already selected dont add
                        self.listSelectedNCRouter.append(ncRouterNode)
                      if selectedNewNode not in self.listSelectedNCRouter:# checking here since if this node is already selected dont add
                        self.listSelectedNCRouter.append(selectedNewNode)

                      ntm.printLog( ntm.getRouterLinkParameters(ncRouterNode,selectedNewNode,dictNeigh ,dictLQ,dictNLQ, dictCost))
                      #GET THE PARAMETER BETWEEN THE newNode and dictBestCandidate[listAllNewNode[0]] -> needed for election
                      if str(ntm.getRouterLinkParameters(ncRouterNode,selectedNewNode,dictNeigh ,dictLQ,dictNLQ, dictCost) ) not in self.listRouterParameters:
                          self.listRouterParameters.append(str(ntm.getRouterLinkParameters(ncRouterNode,selectedNewNode,dictNeigh ,dictLQ,dictNLQ, dictCost)))


                if (isBlankRouter):
                    
                    ntm.printLog("continue AT isBlankRouter")
                    continue #### continue to WHILE LOOP since isBlankRouter = Trtue inside the FOR loop above 



              
              #4. if this host is a selected NC router then Run a NC agent
          if self.hostName in  self.listSelectedNCRouter:
             print" ********************************* "
             print" RUN THE NETWORK CODING AGENT HERE "
             print self.hostName
             print" ********************************* "
               
                  
                            

              #5. generate KML file
          ntm.generateKML( self.hostName, dictAllNodes, dictNeigh, dictLQ, dictNLQ, dictCost,dictPos,self.listSelectedNCRouter, listAllNewNode)
              
          if (len(listAllNewNode)>0):
              print 'listAllNewNode:'+ str(listAllNewNode)

              print 'Preiv Nodes: '+ str(dictPrevNeigh.keys())

          if(len(self.listSelectedNCRouter)>0):
              print '---------------'
              print 'listSelectedNCRouter: '+ str(self.listSelectedNCRouter)
              print '---------------'
              print 'listRouterParameters: '+ str(self.listRouterParameters)
             
              


                  
              #6. push all data for this generation into listAllNwInfo       
          listAllNwInfo.append('Generation# '+ str(generation) +' Position: '+str(dictPos)+' neighborSet: '+ str(dictNeigh)+' LQ: '+ str(dictLQ)+
                                   ' NLQ: '+ str(dictNLQ)+' Cost: '+ str(dictCost)+' Distance: '+ str(dictDist) +' NCRouterSelected: '
                                   +str(self.listSelectedNCRouter))
              #print listAllNwInfo

                               
          #7. dump Nw Data To File
          ntm.dumpNwDataToFile(dictNeigh.keys(),self.hostName)
          ntm.dumpNwDataToFile(listAllNwInfo,self.hostName+'.History')
          
          dictPrevNeigh = copy.deepcopy(dictNeigh)
          if(len(self.listSelectedNCRouter)>0):
            dictNCRouterSelected[generation] = self.listSelectedNCRouter
            time.sleep( self.activeRouterInterval )# if a router is selected then PAUSE the system for routerActiveTime so that data sync can be done              

                       
          lastLiveTimeOfNetwork = time.time() # update the last seen time 
          time.sleep( self.dataInterval )
          print str(generation)+ "> Done \n ____________________________"
          generation += 1
      


def main():

    topology = NetworkTopology()
    topology.topologyMain()


    
  
if __name__ == "__main__":
  main()
