*** Settings ***
Documentation      Resource File for k8s
Library            SSHLibrary
Library            OperatingSystem
Library            String
Variables          setup_config.yaml

*** Variables ***

*** Keywords ***
Get pod names
    FOR    ${index}    IN RANGE   5
        Sleep  5 seconds
        ${stdout}  ${stderr}  ${rc}=    Execute Command    kubectl get pods -n ${ns} | grep -v NAME | awk '{print $1}'    return_stderr=True    return_rc=True
        ${stdout-length}=    Get Length    ${stdout}
        Exit For Loop If    ${stdout-length}!=0
    END
    Should Not Be Empty    ${stdout}
    @{pod-list}=    Split To Lines    ${stdout}
    RETURN     @{pod-list}

Get pod names pending
    FOR    ${index}    IN RANGE   5
        Sleep  5 seconds
        ${stdout}  ${stderr}  ${rc}=    Execute Command    kubectl get pods -n ${ns} | grep Pending | awk '{print $1}'    return_stderr=True    return_rc=True
        ${stdout-length}=    Get Length    ${stdout}
        Exit For Loop If    ${stdout-length}!=0
    END
    Should Not Be Empty    ${stdout}
    @{pod-list-pending}=    Split To Lines    ${stdout}
    RETURN     @{pod-list-pending}


Check the pod status 
    [Arguments]    ${status}    ${pod}    
    ${stdout}  ${stderr}  ${rc}=    Execute Command    kubectl get pods -n ${ns} | grep ${pod} | awk '{print $2,$3}'    return_stderr=True    return_rc=True
    Should Match Regexp    ${stdout}    ${status}
    Set Test Variable    ${stdout}    console=yes

Create k8s App
    [Arguments]    ${yaml_file}    ${namespace}
    ${stdout}  ${stderr}  ${rc}=    Execute Command    kubectl apply -f ${yaml_file} -n ${namespace}     return_stderr=True    return_rc=True
    Should Be Equal As Integers    ${rc}    0
