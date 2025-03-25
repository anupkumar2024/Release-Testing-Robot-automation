*** Settings ***
Documentation      Functional Keywords for Robin
Library            String
Library            Process
Library            OperatingSystem
Library            SSHLibrary
Library            Collections
Library            SCPLibrary
Variables          setup_config.yaml


*** Variables ***
${manifest-file}    ${CURDIR}/tests/bundle/manifest.yaml 
${bundle-scripts}   ${CURDIR}/tests/bundle/scripts        

*** Keywords ***
Open Connection and Log In
    [Arguments]          ${host}
    SSHLibrary.Open Connection      ${host}
    Login          ${ssh-user}    ${ssh-pass}    delay=3


Robin Login From Robot
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin login ${robin-username} --password ${robin-password}   return_stderr=True    return_rc=True
    Should Contain    ${stdout}    User ${robin-username} is logged into

Create Robin Namespace
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin namespace add ${ns}    return_stderr=True    return_rc=True

Setup dos2unix
    ${stdout}  ${stderr}  ${rc}=    Execute Command    yum install dos2unix -y    return_stderr=True    return_rc=True
    Should Be Equal As Integers    ${rc}    0
    
Copy File On Remote With Password
    [Arguments]          ${remoteIp}   ${sourceFile}   ${destFile}
    SCPLibrary.Open Connection   ${remoteIp}    username=${ssh-user}  password=${ssh-pass}
    SCPLibrary.Put File          ${sourceFile}       ${destFile}
    SCPLibrary.Close Connection

Copy File On Local With Password
    [Arguments]          ${remoteIp}   ${sourceFile}   ${destFile}
    SCPLibrary.Open Connection   ${remoteIp}    username=${ssh-user}  password=${ssh-pass}
    SCPLibrary.Get File          ${sourceFile}       ${destFile}
    SCPLibrary.Close Connection

Copy Directory On Remote With Password
    [Arguments]    ${remoteIp}    ${sourceDir}    ${destDir}
    SCPLibrary.Open Connection    ${remoteIp}    username=${ssh-user}    password=${ssh-pass}
    ${files}=    OperatingSystem.List Files In Directory    ${sourceDir}    recursive=True
    FOR    ${file}    IN    @{files}
        ${relativePath}=    String.Replace String    ${file}    ${sourceDir}/    
        ${remotePath}=    Catenate    SEPARATOR=/    ${destDir}    ${relativePath}
        SCPLibrary.Put File    ${file}    ${remotePath}
    END
    SCPLibrary.Close Connection

Edit file by sed
    [Arguments]    ${file}    ${org-str}    ${aft-str}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    sed -i -e 's/${org-str}/${aft-str}/g' ${file}    return_stderr=True    return_rc=True
    Should Be Equal As Integers    ${rc}    0


Create File Collection
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin collection create --replicas 1 --size 10G ${media} default --force --wait   return_stderr=True    return_rc=True
    Should Be Equal As Integers  ${rc}  0
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin collection list |grep FILE_COLLECTION|cut -d ' ' -f1|tail -1   return_stderr=True    return_rc=True
    Should Be Equal As Integers  ${rc}  0
    Set Suite Variable    ${fileCollectionId}    ${stdout}

Delete File Collection
    [Arguments]          ${collectionId}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin collection delete ${collectionId} -y --wait   return_stderr=True    return_rc=True
    Should Be Equal As Integers  ${rc}  0

#Check File Collection
#    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin collection list|grep FILE_COLLECTION|cut -d "|" -f5   return_stderr=True    return_rc=True
#    Should Be Equal As Integers  ${rc}  0
#    Should Contain    ${stdout}    READY

Check file Collection
    ${stdout}  ${stderr}  ${rc}=    Execute Command        ~/bin/robin collection list --json  return_stderr=True    return_rc=True
    ${stdout}=    Evaluate     json.loads("""${stdout}""")    json
    ${filecollections}=    Get Length    ${stdout['collections']}
    Set Test Variable    ${filecollections}
    Should Be Equal As Integers    ${rc}    0

Check bundle
    ${stdout}  ${stderr}  ${rc}=    Execute Command        ~/bin/robin bundle list --json  return_stderr=True    return_rc=True
    ${stdout}=    Evaluate     json.loads("""${stdout}""")    json
    ${bundle-length}=    Get Length     ${stdout['bundles']}
    ${bundles}=    Get Variable Value    ${stdout['bundles']}
    Set Test Variable    ${bundle-length}
    Set Test Variable    ${bundles}
    Should Be Equal As Integers    ${rc}    0
    

Check Bundle In List
    [Arguments]    ${bundles}    ${bundle-name}
    FOR    ${bundle}    IN    @{bundles}
        ${bundlename}=    Get Variable Value    ${bundle['name']}
        BuiltIn.Log    Checking Bundle Name:${bundlename}    console=yes
        IF    '${bundle-name}' == '${bundlename}'  
            Set Test Variable     ${found}    True
            Exit For Loop
        END        
    END
    Set Suite Variable    ${found}
    Log     ${found}    console=yes  
    IF    '${found}' == 'False'
        Upload Bundle to Robin    ${bundle-name}
    END    
Check Local File Exist
    [Arguments]          ${file}
    OperatingSystem.File Should Exist    ${file}

Upload Bundle to Robin
    [Arguments]          ${bundle-name}   
    # ${manifest}=  OperatingSystem.Get File  ${manifest-file}
    ${appFileDir} =   Catenate    SEPARATOR=  ${destTempDir}   bundle/
    ${iconDir} =   Catenate    SEPARATOR=  ${appFileDir}   icons/
    ${bundle-tar} =   Catenate    SEPARATOR=  ${appFileDir}   ${bundle-name}.tar.gz
    ${stdout}  ${stderr}  ${rc}=    Execute Command    rm -rf ${destTempDir}; mkdir ${destTempDir}; mkdir ${appFileDir};     return_stderr=True    return_rc=True
    ${stdout}  ${stderr}  ${rc}=    Execute Command    cd ${appFileDir}; mkdir -p icons scripts/k8s/pre scripts/sample_inputs;  return_stderr=True    return_rc=True    
    
    Copy File On Remote With Password  ${master-node-ip}   ${iconFile}   ${iconDir}
    Copy File On Remote With Password  ${master-node-ip}   ${manifest-file}   ${appFileDir}
    Copy File On Remote With Password  ${master-node-ip}   ${bundle-scripts}/app_info.py   ${appFileDir}scripts/
    Copy File On Remote With Password  ${master-node-ip}   ${bundle-scripts}/k8s/pre/cm1.yaml   ${appFileDir}scripts/k8s/pre/
    Copy File On Remote With Password  ${master-node-ip}   ${bundle-scripts}/k8s/pre/cm2.yaml   ${appFileDir}scripts/k8s/pre/
    Copy File On Remote With Password  ${master-node-ip}   ${bundle-scripts}/k8s/pre/cm3.yaml   ${appFileDir}scripts/k8s/pre/
    Copy File On Remote With Password  ${master-node-ip}   ${bundle-scripts}/k8s/pre/sa.yaml   ${appFileDir}scripts/k8s/pre/
    Copy File On Remote With Password  ${master-node-ip}   ${bundle-scripts}/sample_inputs/input_envfrom.yaml   ${appFileDir}scripts/sample_inputs

    Edit file by sed    ${appFileDir}manifest.yaml    media    ${media}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    cd ${appFileDir}; tar czvf ${bundle-name}.tar.gz *;     return_stderr=True    return_rc=True
    Should Be Equal As Integers  ${rc}  0

    Add Robin Bundle   ${bundle-name}   1.0.0   ${bundle-tar}  

Add Robin Bundle
    [Arguments]          ${bundle-name}   ${version}   ${image}   
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin bundle add ${bundle-name} ${version} ${image}  --wait   return_stderr=True    return_rc=True
    Log    ${stdout}
    Should Be Equal As Integers  ${rc}  0

robin bundle list
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin bundle list   return_stderr=True    return_rc=True
    Should Contain    ${stdout}    Name


Get Bundle Id
    [Arguments]          ${bundle-name}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin bundle list --json  return_stderr=True    return_rc=True
    ${stdout}=    Evaluate     json.loads("""${stdout}""")    json
    FOR    ${member}     IN      @{stdout['bundles']}
        IF    '${member['name']}'=='${bundle-name}'
            Set Suite Variable    ${bundleId}    ${member['bundleid']}
            ${bool-this-keyword}=    Set Variable    ${true}
            Exit For Loop
        END
    END
    Should Be True    ${bool-this-keyword}
    BuiltIn.Log         Bundle ID:${bundleId}   console=yes

Get Zone Id
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin bundle list --json   return_stderr=True    return_rc=True
    ${stdout}=    Evaluate     json.loads("""${stdout}""")    json
    FOR    ${member}     IN      @{stdout['bundles']}
        IF    '${member['name']}'=='${bundle-name}'
            Set Suite Variable    ${zoneId}    ${member['zoneid']}
            ${bool-this-keyword}=    Set Variable    ${true}
            Exit For Loop
        END
    END
    Should Be True    ${bool-this-keyword}
    BuiltIn.Log         Zone ID:${zoneId}       console=yes


Get Content Id
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin bundle list --json   return_stderr=True    return_rc=True
    ${stdout}=    Evaluate     json.loads("""${stdout}""")    json
    FOR    ${member}     IN      @{stdout['bundles']}
        IF    '${member['name']}'=='${bundle-name}'
            Set Suite Variable    ${contentId}    ${member['content_id']}
            ${bool-this-keyword}=    Set Variable    ${true}
            Exit For Loop
        END
    END
    Should Be True    ${bool-this-keyword}
    BuiltIn.Log         Content ID:${contentId}         console=yes

Log Bundle Info
    [Arguments]    ${bundleId}    ${zoneId}    ${contentId}
    Log To Console    Get Bundle Info | Bundle ID: ${bundleId} | Zone ID: ${zoneId} | Content ID: ${contentId}

Detach Robin App
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin app detach-repo ${app-name} ${repo} --wait -y  return_stderr=True    return_rc=True
    Open Connection and Log In    ${master-node-ip}
    Should Be Equal As Integers  ${rc}  0

Create Robin App
    Open Connection and Log In    ${master-node-ip}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin app create from-bundle ${app-name} ${bundleId} --wait --namespace ${ns} --rpool default  return_stderr=True    return_rc=True
    Should Be Equal As Integers  ${rc}  0

Delete Robin App
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin app delete ${app-name} --wait -y --iter --force  return_stderr=True    return_rc=True
    Open Connection and Log In    ${master-node-ip}
    Should Be Equal As Integers  ${rc}  0

hydrate app
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin app hydrate ${app-name} --wait   return_stderr=True    return_rc=True
    Open Connection and Log In    ${master-node-ip}
    Should Be Equal As Integers  ${rc}  0s

Delete Robin Bundle
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin bundle remove ${zoneId} ${bundleId} -y --wait  return_stderr=True    return_rc=True
    Should Be Equal As Integers  ${rc}  0

Unregister Robin External Repo
    [Arguments]    ${repo}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin repo unregister ${repo} --wait   return_stderr=True    return_rc=True
    Should Be Equal As Integers  ${rc}  0


Delete Robin Namespace
    [Arguments]    ${ns}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin namespace remove ${ns} -y   return_stderr=True    return_rc=True
    Should Be Equal As Integers  ${rc}  0

Bundle App Restore From Backup
    [Arguments]    ${backupId}    ${ns}    ${rpool}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin app create from-backup ${app-name} ${backupId} -n ${ns} --rpool ${rpool} --wait  return_stderr=True    return_rc=True
    Should Be Equal As Integers  ${rc}  0

Fetch volume Info
    [Arguments]    ${pvname}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin volume info ${pvname}    return_stderr=True    return_rc=True
    Log     ${stdout}
    Should Be Equal As Integers  ${rc}  0

    

## helm
Helm App Restore From Backup
    [Arguments]    ${backupIdHelm}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin app create from-backup ${app-name} ${backupIdHelm} --namespace ${ns} --same-name-namespace --wait  return_stderr=True    return_rc=True
    Should Be Equal As Integers  ${rc}  0

Delete Helm Bundle
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin bundle list --headers "Bundle Id",Name | grep ${app-name} | awk -F"," '{print $1}'   return_stderr=True    return_rc=True
    Set Test Variable    ${robin-bundle-id}    ${stdout}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin host list --headers Id | head -1 | awk -F ":" '{print $1}'   return_stderr=True    return_rc=True
    Set Test Variable    ${robin-bundle-zone}    ${stdout}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin bundle delete ${robin-bundle-zone} ${robin-bundle-id} -y --wait  return_stderr=True    return_rc=True
    Should Be Equal As Integers  ${rc}  0

Deregister ip-pool
    [Arguments]    ${ip-pool-name}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin ip-pool delete -y ${ip-pool-name}    return_stderr=True    return_rc=True
    Should Be Equal As Integers  ${rc}  0

List ip-pool
    ${stdout}  ${stderr}  ${rc}=    Execute Command    ~/bin/robin ip-pool list   return_stderr=True    return_rc=True
    Should Be Equal As Integers  ${rc}  0
    RETURN   ${stdout}            