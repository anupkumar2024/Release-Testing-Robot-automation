*** Settings ***
Library  restore_bundleApp_from_snapshot.py


*** Test Cases ***
Robin Login
    [Documentation]    Create Robin login and fetch auth token
    ${response}=    Robin Login
    Log  ${response}
    Set Suite Variable   ${auth_token}   ${response[1]}
    Should Be Equal As Numbers  ${response[2]}  200

Create Nampespace
    [Documentation]    Create Robin namespace
    ${response}=    Robin Namespace  ${auth_token}
    Should Be Equal As Numbers  ${response}  200

Create app from Bundle
    [Documentation]    Create app from bundle
    ${response}=    Create App From Bundle  ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Fetch Pod Name
    [Documentation]    Fetch Pod Name
    ${response}=    Get Pod Name
    Log  ${response}

Upload Data
    [Documentation]   Upload file to pod
    ${response}=    Upload File To Pod
    Log  ${response}

Create Snapshot
    [Documentation]    Create snapshot of Bundle App
    ${response}=    Create Snapshot  ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Delete Data
    [Documentation]   Delete data from pod
    ${response}=    Delete Data from Pod

Fetch Snapshot
    [Documentation]   Fetch Snapshot Id from which data will be restored
    ${response}=   Fetch Snapshot Id  ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    200

Restore Data
    [Documentation]   Restore bundle app from snapshot
    ${response}=    Restore App From Snapshot  ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Verify Data Restore
    [Documentation]   Verify if data is restored successfully
    ${response}=    Verify Data Restore
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

App Cleanup
    [Documentation]   Delete Bundle app and snapshots
    ${response}=    Delete App  ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202






