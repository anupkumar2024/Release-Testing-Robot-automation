*** Settings ***
Library            ${resource_dir}/tests/backup_restore_bundle.py
Library            ${resource_dir}/pause.py
Resource           ${resource_dir}/robin_base.robot

Suite Setup        Open Connection and Log In      ${master-node-ip}
# variables          ${resource_dir}/setup_config.yaml

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
    ${response}=    Create App From Bundle  ${auth_token}   ${bundleId}
    Log  ${response}   
    Should Be Equal As Numbers    ${response[1]}    202

Register external repo
    [Documentation]    Register external rep for backup storage
    ${response}=    Register External Repo  ${auth_token}
    Log  ${response}    
    Should Be Equal As Numbers    ${response[1]}    202

Attach app to external repo
    [Documentation]    Attach  bundle app to external repo
    ${response}=    Attach App To Ext Repo  ${auth_token}
    Log  ${response}    
    Should Be Equal As Numbers    ${response[1]}    202


Copy File from Remote to Local
    Copy File On Local With Password    ${master-node-ip}    /root/.kube/config   ${CURDIR}/kubeconfig
    
Upload file to pod
    [Documentation]    Upload text file to pod
    ${response}=    Upload File To Pod    ${kubeconfig_path}  
    Log    ${response}    console=yes


Backup Creation
    [Documentation]    Create backup of bundle app in ext storage repository
    ${response}=    Backup Creation   ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Paused
   Log    Press ok to continue    console=yes 
   pause  
   Log    Execution resumed..     console=yes

Detach Bundle App
    [Documentation]    Detach bundle app from External Repo
    Detach Robin App

Delete Bundle App
    [Documentation]    Delete bundle app from cluster
    Delete Robin App   


Fetch backup Id
    [Documentation]    Fetch backup Id
    ${response}=    Fetch Backup Id    ${auth_token}
    Log  ${response}    
    Should Be Equal As Numbers    ${response[1]}    200
    Set Suite Variable    ${backupId}   ${response[0]} 

Bundle Robin App Restore
    [Documentation]    Restore bundle app from backup created in ext repo
    Bundle App Restore From Backup    ${backupId}    ${ns}    ${rpool}

Copy File from Remote to Local
    Copy File On Local With Password    ${master-node-ip}    /root/.kube/config   ${CURDIR}/kubeconfig

Verify Data Restore
    [Documentation]    Verify if data is restored succesfully
    ${response}=    List File From Pod    ${kubeconfig_path}
    Should Be Equal As Numbers    ${response}    202


Bundle backups Cleanup
    [Documentation]    Delete backups associated with App
    ${response}=    Delete Backups   ${auth_token}
    Log  ${response}    
    Should Be Equal As Numbers    ${response[1]}    202
    
Detach Bundle App
    [Documentation]    Detach bundle app from External Repo
    Detach Robin App

Bundle App Cleanup
    [Documentation]    Delete bundle app from cluster
    ${response}=    Delete App   ${auth_token}
    Log  ${response}    
    Should Be Equal As Numbers    ${response[1]}    202

External Repo Cleanup
    [Documentation]    Delete ext repo
    ${response}=    Delete Ext Repo   ${auth_token}
    Log  ${response}    
    Should Be Equal As Numbers    ${response[1]}    202

Bundle Cleanup
    Delete Robin Bundle 

Namespace Cleanup
    Delete Robin Namespace    ${ns}

#Collection Clean Up
#    Delete File Collection    ${fileCollectionId}