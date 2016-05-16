import sys
import time
import opc_helper


def main():
    opc_helper.initialize_com()

    try:
        # computer_name = 'WARMW'
        computer_name = None
        opcsrvs = opc_helper.opc_enum_query(computer_name)
        iconics_server = None
        infinity_server = None
        selected_server = None
        for opcsrv in opcsrvs:
            print(opcsrv)
            if opcsrv['progid'] == 'ICONICS.SimulatorOPCDA.2':
                iconics_server = opcsrv
            if opcsrv['progid'] == 'Infinity.OPCServer':
                infinity_server = opcsrv

        selected_server = iconics_server
        if selected_server is None:
            selected_server = infinity_server
            if selected_server is None:
                opc_helper.uninitialize_com()
                sys.exit(1)

        print('Selected:', selected_server['progid'], ', connecting...')

        server = opc_helper.opc_connect(selected_server['guid'], computer_name)
        print(server)
        print(server.guid)
        print(server.progid)

        print('status:', server.get_status())
        print('supports v3:', server.supports_v3())
        # server.add_group('PythonOPCGroup') # this should be internal func
        print(server.browse())

        print(server.get_item('Numeric._I4'))
        time.sleep(1)
        print(server.get_item('Numeric._I4'))

    except opc_helper.OPCException as opcex:
        print(opcex)

if __name__ == '__main__':
    main()
