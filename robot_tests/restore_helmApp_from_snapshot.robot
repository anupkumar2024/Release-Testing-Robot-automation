*** Settings ***
Library            ${resource_dir}/tests/restore_helmApp_from_snapshot.py
Resource           ${resource_dir}/robin_base.robot

Suite Setup        Open Connection and Log In      ${master-node-ip}


*** Test Cases ***
Robin Login
    [Documentation]    Create Robin login and fetch auth token
    ${response}=    Robin Login
    Log  ${response}
    Set Suite Variable   ${auth_token}   ${response[1]}
    Should Be Equal As Numbers  ${response[2]}  200

Create Nampespace
    [Documentation]    Create Robin namespace
    ${response}=    Robin Namespace    ${auth_token}
    Should Be Equal As Numbers  ${response}  200

Copy chart tar file to masternode
    Copy File On Remote With Password    ${master-node-ip}    ${CURDIR}/${chartName}.tgz    /root/


Create Helm app from Chart
    [Documentation]    Create Helm App from Chart
    ${response}=    Create Helm App    
    Log  ${response}

Register Helm App
     [Documentation]   Register helm app created with Robin
     ${response}=    Register Helm App  ${auth_token}
     Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Copy File from Remote to Local
    Copy File On Local With Password    ${master-node-ip}    /root/.kube/config   ${CURDIR}/kubeconfig

Fetch Pod Name
    [Documentation]    Fetch Pod Name
    ${response}=    Get Pod Name    ${kubeconfig_path}
    Log  ${response}

Upload Data
    [Documentation]   Upload file to pod
    ${response}=    Upload File To Pod    ${kubeconfig_path}
    Log  ${response}

Create Snapshot
    [Documentation]    Create snapshot of Helm App
    ${response}=    Create Snapshot  ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Delete Data
    [Documentation]   Delete data from pod
    ${response}=    Delete Data from Pod    ${kubeconfig_path}

Fetch Snapshot
    [Documentation]   Fetch Snapshot Id from which data will be restored
    ${response}=   Fetch Snapshot Id  ${auth_token}
    Log  ${response}
    Set suite Variable    ${snapid}    ${response[0]}    
    Should Be Equal As Numbers    ${response[1]}    200

Restore Data
    [Documentation]   Restore Helm app from snapshot
    ${response}=    Restore App From Snapshot  ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Verify Data Restore
    [Documentation]   Verify if data is restored successfully
    ${response}=    Verify Data Restore    ${kubeconfig_path}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

App Cleanup
    [Documentation]   Delete Helm App and snapshots
    ${response}=    Delete App  ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

    
Namespace Cleanup
    Delete Robin Namespace    ${ns}