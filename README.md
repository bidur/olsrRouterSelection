# olsrRouterSelection
This Python program runs on mobile  computer/node ( with OLSR routing protocol on ). When different  networks ( of mobile nodes) meet then a Router is selected from each network based on best connectivity parameters.
Based on the OLSR ( Optimized linked state routing protocol) neighbor link quality parameters the router selection is done. <http://www.olsr.org/docs/README-Link-Quality.html>

# run.sh
Creates a folder named dtnFile in /var/www/ 

# mainProgram.py
Program to select best Router for new nodes joining the OLSR network

#networkTopologyModule.py
Module with methods used by Program to select best Router for new nodes joining the OLSR network

# kml files
generated by the program. These can be viewed in the applications like Google Earth to see how the network topology changes

