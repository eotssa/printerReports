Generate printer status reports as a non-admin user. 


Supported Printers:
DCP-L2540DW series
HL-L2350DW series

Within the config file, change the IP address to whatever static IP address is assigned to your printer.

This script is exclusively for Brother printers at the moment. I plan on expanding this to Ricoh and HP printers. 

Instead of using SNMP, it simply pings the IP address, accesses the web GUI, and parses the relevant information, then generates a report. 

