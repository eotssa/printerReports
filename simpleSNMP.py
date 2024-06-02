from pysnmp.hlapi import *

def get_snmp_data(ip, community, oid):
    error_indication, error_status, error_index, var_binds = next(
        getCmd(SnmpEngine(),
               CommunityData(community, mpModel=0),
               UdpTransportTarget((ip, 161)),
               ContextData(),
               ObjectType(ObjectIdentity(oid)))
    )
    
    if error_indication:
        print(f"Error: {error_indication}")
        return None
    elif error_status:
        print(f"Error Status: {error_status.prettyPrint()}")
        return None
    else:
        for var_bind in var_binds:
            return var_bind.prettyPrint().split('=')[1].strip()

def main():
    printer_ip = '192.168.0.202'  # Replace with your printer's IP
    community_string = 'public'   # Replace with your SNMP community string

    # OIDs for printer status and error status
    printer_status_oid = '1.3.6.1.2.1.25.3.5.1.1.1'
    error_status_oid = '1.3.6.1.2.1.25.3.5.1.2.1'

    # Get printer status
    printer_status = get_snmp_data(printer_ip, community_string, printer_status_oid)
    print(f"Printer Status: {printer_status}")

    # Get error status
    error_status = get_snmp_data(printer_ip, community_string, error_status_oid)
    print(f"Error Status: {error_status}")

if __name__ == '__main__':
    main()
