*** Settings ***
Library          vol_replication.py
Resource         ${resource_dir}/robin_base.robot

Suite Setup        Open Connection and Log In      ${master-node-ip}


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

Copy chart tar file to masternode
    Copy File On Remote With Password    ${master-node-ip}    ${CURDIR}/${volumeReplicationChartName}.tgz    /root/

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

Helm App Cleanup
    [Documentation]    Delete the helm app and its resources
    ${response}=    Helm App Cleanup   
    Log  ${response}    console=yes


Namespace Cleanup
    Delete Robin Namespace    ${ns}