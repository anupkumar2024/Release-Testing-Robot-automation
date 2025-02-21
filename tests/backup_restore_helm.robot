*** Settings ***
Library            ${resource_dir}/tests/backup_restore_helm.py
Library            ${resource_dir}/test.py
Library            JSONLibrary
Resource           ${resource_dir}/robin_base.robot

Suite Setup        Open Connection and Log In      ${master-node-ip}

*** variables ***
${json_file}    ${CURDIR}/vars.json
${kubeconfig_path}   ${CURDIR}/kubeconfig

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

Copy chart tar file to masternode
    Copy File On Remote With Password    ${master-node-ip}    ${CURDIR}/${chartName}.tgz    /root/


Create Helm App
    [Documentation]    Create helm app from chart
    ${response}=    Create Helm App
    Log  ${response}
    Should Contain    ${response[0]}    deployed

Register helm app with robin
    [Documentation]    Register helm app and it resources with Robin
    ${response}=    Register Helm App  ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Register external repo
    [Documentation]    Register external rep for backup storage
    ${response}=    Register Ext Storage Repo  ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202


Upload file to pod
    [Documentation]    Upload text file to pod
    ${response}=    Upload File To Pod    ${kubeconfig_path}
    Should Be Equal As Numbers    ${response}    200
    
Attach helm app to external repo
    [Documentation]    Attach helm app to external repo
    ${response}=    Attach App To Ext Repo  ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Backup Creation
    [Documentation]    Create backup of helm app in ext storage repository
    ${response}=    Backup Creation   ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Detach Helm App
    [Documentation]    Detach repo from helm app
    ${response}=    Detach App From Repo   ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Delete Helm App
    [Documentation]    Delete helm app from cluster
    Delete Robin App

Fetch backup Id
    [Documentation]    Fetch backup Id
    ${response}=    Fetch Backup Id    ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    200
    Set Suite Variable    ${backupIdHelm}   ${response[0]}

Helm App Restore
    [Documentation]    Restore Helm app from backup 
    Helm App Restore From Backup    ${backupIdHelm} 

Verify Data Restore
    [Documentation]    Verify if data is restored succesfully
    ${response}=    List File From Pod    ${kubeconfig_path}
    Should Be Equal As Numbers    ${response}    202

Register Restored Helm App
    [Documentation]    reregister helm app with robin
    ${response}=    Register Helm App   ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Hydrate Restored Volumes
    [Documentation]    hydrate restored pv registerd with robin
    ${response}=    hydrate volumes   ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Attach restored helm app to external repo
    [Documentation]    Attach restored helm app to external repo
    ${response}=    Attach App To Ext Repo  ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Restored Helm App Backup Creation
    [Documentation]    Create backup of restored helm app in ext storage repository
    ${response}=    Backup Creation   ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202


Detach Restored Helm App
    [Documentation]    Detach repo from  restored helm app
    ${response}=    Detach App From Repo   ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Delete Restored Helm App
    [Documentation]    Delete Restored helm app from cluster
    Delete Robin App

Create new helm app from backup
    [Documentation]    Create helm app from backup created from restored app
    Helm App Restore From Backup    ${backupIdHelm}

Register New Restored Helm App
    [Documentation]    reregister helm app with robin
    ${response}=    Register Helm App   ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202


Unregister Helm App
    [Documentation]    Unregister new helm app from robin
    ${response}=    Unregister Helm App  ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    202

Verify Pods After Deregister
    [Documentation]    Verify helm pods status
    ${response}=    Verify Helm pod    ${kubeconfig_path}
    Log  ${response}
    Should Be Equal As Numbers    ${response[1]}    200

    
Helm backups Cleanup
    [Documentation]    Delete backups associated with Helm App
    ${response}=    Delete Backups   ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers    ${response}    202

Helm App Cleanup
    [Documentation]    Delete the helm app and its resources
    ${response}=    Helm App Cleanup   
    Log  ${response}    console=yes


External Storage Repo Cleanup
    Wait Until Keyword Succeeds    2x    10s    Unregister Robin External Repo    ${repo}

Helm App Cleanup
    [Documentation]    Delete the helm app and its resources
    ${response}=    Helm App Cleanup   
    Log  ${response}    console=yes

Helm bundle Cleanup
    Delete Helm Bundle    

Namespace Cleanup
    Delete Robin Namespace    ${ns}