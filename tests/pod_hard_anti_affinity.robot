*** Settings ***
Library            pod_hard_anti_affinity.py
Resource           ${resource_dir}/robin_base.robot
Resource           ${resource_dir}/k8s_resources.robot

Suite Setup        Open Connection and Log In      ${master-node-ip}


*** variables ***
${file}    ${resource_dir}/tests/pod_hard_antiaffinity.yaml
${dest_file}    /root/pod_hard_antiaffinity.yaml


*** Test Cases ***

Robin Manual Login
    Robin Login From Robot
    
Create Namespace
    Create Robin Namespace

Copy File from Remote to Local
    Copy File On Local With Password    ${master-node-ip}    /root/.kube/config   ${CURDIR}/kubeconfig


Get No of nodes
    ${stdout}  ${stderr}  ${rc}=    Execute Command    kubectl get nodes | grep -v NAME| wc -l   return_stderr=True    return_rc=True
    Set Suite Variable    ${nodes_count}    ${stdout}
    Should Be Equal As Integers    ${rc}    0

Remove Existing yaml file
    ${stdout}  ${stderr}  ${rc}=    Execute Command    rm -rf ${dest_file}     return_stderr=True    return_rc=True
    Should Be Equal As Integers    ${rc}    0

Update Yaml to test Sufficient nodes
    Copy File On Remote With Password    ${master-node-ip}    ${file}    /root/
    ${stdout}   ${stderr}    ${rc}=    Execute Command    /usr/bin/dos2unix ${dest_file}     return_stderr=True  return_rc=True
    Should Be Equal As Integers    ${rc}    0
    Edit file by sed   ${dest_file}    replica_count    ${nodes_count} 

Test Pod Hard Antiaffinity with Sufficient Nodes   
    Create k8s App    ${dest_file}    ${ns}    
    Log    Verifying pod status    console=yes   
    @{pod-list}=    k8s_resources.Get pod names
    Set Suite Variable        @{pod-list}
    
    FOR     ${pod}    IN    @{pod-list}         
        Wait Until Keyword Succeeds    3x    5s    Check the pod status    1/1 Running    ${pod}
    END 

    Edit file by sed   ${dest_file}    ${nodes_count}    replica_count
    Copy File On Local With Password    ${master-node-ip}    ${dest_file}    ${resource_dir}/tests/
    ${response}=   Verify Pod Hard Anti Affinity    ${kubeconfig_path}
    Log    ${response}
    Should Be Equal As Numbers   ${response[0]}  200
    ${stdout}  ${stderr}  ${rc}=    Execute Command    kubectl get pods -n ${ns} -owide    return_stderr=True    return_rc=True
    Should Be Equal As Integers    ${rc}    0
    Log    ${stdout}    console=yes
    ${response}=   App Cleanup    ${kubeconfig_path}
    Log    ${response}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    rm -rf ${dest_file}     return_stderr=True    return_rc=True
    Should Be Equal As Integers    ${rc}    0


Update Yaml to test InSufficient nodes
    Copy File On Remote With Password    ${master-node-ip}    ${file}    /root/
    ${stdout}   ${stderr}    ${rc}=    Execute Command    /usr/bin/dos2unix ${dest_file}     return_stderr=True  return_rc=True
    Should Be Equal As Integers    ${rc}    0
    ${new_replicas}=    Evaluate    ${nodes_count} + ${extra_replicas}
    Set Suite Variable    ${new_replicas}            
    Edit file by sed   ${dest_file}    replica_count    ${new_replicas}


Test Pod Hard Antiaffinity with InSufficient Nodes 
    Create k8s App    ${dest_file}    ${ns}
    Log    Verifying pod status    console=yes       
    @{pod-list-pending}=    k8s_resources.Get pod names pending
    Set Suite Variable        @{pod-list-pending}

    FOR     ${pod}    IN    @{pod-list-pending}         
        Wait Until Keyword Succeeds    3x    5s    Check the pod status    0/1 Pending    ${pod}
    END 

    Edit file by sed   ${dest_file}    ${new_replicas}    replica_count
    Copy File On Local With Password    ${master-node-ip}    ${dest_file}    ${resource_dir}/tests/
    ${stdout}  ${stderr}  ${rc}=    Execute Command    kubectl get pods -n ${ns} -owide    return_stderr=True    return_rc=True
    Should Be Equal As Integers    ${rc}    0
    Log    ${stdout}    console=yes
    ${response}=   App Cleanup    ${kubeconfig_path}
    Log    ${response}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    rm -rf ${dest_file}     return_stderr=True    return_rc=True
    Should Be Equal As Integers    ${rc}    0

Delete Namespace
    sleep  4
    Delete Robin Namespace     ${ns}
