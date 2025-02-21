*** Settings ***
Library  vol_replication.py


*** Test Cases ***
Robin Login
    [Documentation]    Create Robin login and fetch auth token
    ${response}=    Robin Login
    Log  ${response[0]}
    Set Suite Variable   ${auth_token}   ${response[1]}
    Should Be Equal As Numbers  ${response[2]}  200

Create Nampespace
    [Documentation]    Create Robin namespace
    ${response}=    Robin Namespace  ${auth_token}
    Should Be Equal As Numbers  ${response}  200

Create Helm Stateful App
    [Documentation]    Create Helm stateful app
    ${response}=    Create Helm Stateful App
    Log  ${response}

Fetch PV Name
    [Documentation]    Fetch Physical Volume name
    ${response}=    Fetch PVC
    Log  ${response}

Verify Volume Replication
    [Documentation]    Verify If Volume is Replicated
    ${response}=    Verify Vol Replication  ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers  ${response[0]}  200

