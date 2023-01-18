'''
Various calculations done on a xarray Dataset with signature data.
'''

import numpy as np
import gsw

def dep_from_p(DX):
    '''
    Calculate depth from:
    
    - Absolute pressure (measured by instrument)
        - Using *Average_AltimeterPressure*
          (very rarely differs from *Average_Pressure* 
           by more than ±5e-3 db).
    - Atmospheric pressure (from *p_atmo* field)
    - Gravitational acceleration (calculated from latitude)
    - Ocean density (from data or default 1025 g/kg)

    Input:
    ------

    DX: xarray Dataset with Signature data.

    Returns:
    --------
    DX where the field "DEPTH" (TIME, SAMPLE) has been added.
    '''

    note_str = ('Altimeter depth calculated from pressure'
        ' (*Average_AltimeterPressure* field) as:\n\n     depth = p/(g*rho)\n')

    # CALCULATE ABSOLUTE PRESSURE
    p_abs = DX.Average_AltimeterPressure + DX.pressure_offset

    # CALCULATE OCEAN PRESSURE
    # Raising issues if we cannot find p_atmo (predefined atmospheric pressure)

    if hasattr(DX, 'p_atmo'):
        p_ocean = (p_abs - DX.p_atmo).data
        note_str += '\n- Atmospheric pressure (*p_atmo* field subtracted).'
    else:
        warn_str1 = ('WARNING!\nCould not find atmospheric pressure (*p_atmo*)'
        ' - not recommended continue if you plan to compute ice draft. '
        '\n--> (To add *p_atmo*, run sig_append.append_atm_pres()='
        '\n\nDepth calculation: Abort (A) or Continue (C): ')

        user_input_abort = input(warn_str1).upper()

        while user_input_abort not in ['A', 'C']:
            print('Input ("%s") not recognized.'%user_input_abort)
            user_input_abort = input('Enter "C" (continue) or "A" (abort): ').upper()

        if user_input_abort == 'A':
            raise Exception('ABORTED BY USER (MISSING ATMOSPHERIC PRESSURE)')
        else:
            p_ocean = DX.Average_AltimeterPressure.data
            print('Continuing without atmospheric correction (careful!)..')
            note_str += ('\n- !!! NO TIME_VARYING ATMOSPHERIC CORRECTION APPLIED !!!\n' 
                '  (using default atmospheric pressure offset %.2f db)'%DX.pressure_offset)
            
            

    # CALCULATE GRAVITATIONAL ACCELERATION
    if DX.lat==None:
        raise Exception('No "lat" field in the dataset. Add one using'
                 ' sig_append.set_lat() and try again.')

    g = gsw.grav(DX.lat.data, 0)
    DX['g'] = ((), g, {'units':'ms-2', 
        'note':'Calculated using gsw.grav() for p=0 and lat=%.2f'%DX.lat}) 
    note_str += '\n- Using g=%.4f ms-2 (calculated using gsw.grav())'%g

    # CALCULATE OCEAN WATER DENSITY
    if hasattr(DX, 'rho_ocean'):
        rho_ocean = DX.rho_ocean.data
        note_str += '\n- Using ocean density from the *rho_ocean* field.'
    else:
        print('\nNo density (*rho_ocean*) field found. ')
        user_input_abort_dense = input('Enter "A" (Abort) or "C" '
        '(Continue using fixed rho = 1027 kg m-3): ').upper()
       
        while user_input_abort_dense not in ['A', 'C']:
            print('Input ("%s") not recognized.'%user_input_abort)
            user_input_abort_dense = input(
                'Enter "C" (continue with rho=1027) or "A" (abort): ').upper()

        if user_input_abort_dense == 'A':
            raise Exception('ABORTED BY USER (MISSING OCEAN DENSITY)')
        else:
            rho_ocean = 1027
            print('Continuing with fixed rho = 1027 kg m-3')
            note_str += '\n- Using FIXED ocean density rho = 1027 kg m-3.'


    # CALCULATE DEPTH
    # Factor 1e4 is conversion db -> Pa
    depth = 1e4*p_ocean/g/rho_ocean
    DX['depth'] = (('TIME', 'SAMPLE'), depth, {'units':'m', 
        'long_name':'Transducer depth', 'note':note_str}) 

    return DX



##############################################################################

def mat_to_py_time(mattime):
    '''
    Convert matlab datenum (days) to Matplotlib dates (days).

    MATLAB base: 00-Jan-0000
    Matplotlib base: 01-Jan-1970
    '''

    mpltime = mattime - 719529.0

    return mpltime
