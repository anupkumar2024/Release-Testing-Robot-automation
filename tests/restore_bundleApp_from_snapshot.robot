*** Settings ***
Library            restore_bundleApp_from_snapshot.py
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

Robin Manual Login
    Robin Login From Robot

Create Collection
    Open Connection and Log In    ${master-node-ip}
    Check file Collection
    Run Keyword If    ${filecollections} == 0     Create file collection

Check if manifest file exists
    Check Local File Exist    ${manifest-file}

Upload Bundle
    Open Connection and Log In    ${master-node-ip}
    Check bundle
    Run Keyword If    ${bundle-length} == 0    Upload Bundle to Robin    ${bundle-name} 
    Run Keyword If    ${bundle-length} > 0    Check Bundle In List    ${bundles}    ${bundle-name}


Get Bundle Info
    Run Keyword If    '${PREV TEST STATUS}'=='PASS'    Get Bundle Id  ${bundle-name}
    Run Keyword If    '${PREV TEST STATUS}'=='PASS'    Get Zone Id
    Run Keyword If    '${PREV TEST STATUS}'=='PASS'    Get Content Id
    Run Keyword If    '${PREV TEST STATUS}' == 'PASS'    Log Bundle Info    ${bundleId}    ${zoneId}    ${contentId}
    

Check bundle list
    robin bundle list

Create app from Bundle
    [Documentation]    Create app from bundle
    ${response}=    Create App From Bundle    ${auth_token}    ${bundleId}
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
    [Documentation]    Create snapshot of Bundle App
    ${response}=    Create Snapshot    ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Delete Data
    [Documentation]   Delete data from pod
    ${response}=    Delete Data from Pod    ${kubeconfig_path}

Fetch Snapshot
    [Documentation]   Fetch Snapshot Id from which data will be restored
    ${response}=   Fetch Snapshot Id    ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    200

Restore Data
    [Documentation]   Restore bundle app from snapshot
    ${response}=    Restore App From Snapshot    ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Verify Data Restore
    [Documentation]   Verify if data is restored successfully
    ${response}=    Verify Data Restore    ${kubeconfig_path}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

App Cleanup
    [Documentation]   Delete Bundle app and snapshots
    ${response}=    Delete App    ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Bundle Cleanup
    Delete Robin Bundle 

Namespace Cleanup
    Delete Robin Namespace    ${ns}




