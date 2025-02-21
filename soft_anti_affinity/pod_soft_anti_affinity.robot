*** Settings ***
Library  pod_soft_anti_affinity.py


*** Test Cases ***
Load Yaml
    [Documentation]    Load Yaml with Namepsace of App
    ${response}=    Load Yaml with Namespace
    Log  ${response}

Create App
    [Documentation]    Create App with deployment.yaml File
    ${response}=    Create App
    Log  ${response}

Fetch Node List
    [Documentation]   Fetch Node names where PODS are scheduled
    ${response}=     get Pod Node Name
    Log   ${response}

Verify Pod Anti Affinity
    [Documentation]    Verify Pod Soft Anti Affinity
    ${response}=   Verify Pod Anti Affinity
    Log    ${response}
    Should Be Equal As Numbers   ${response[0]}  200

App cleanup
    [Documentation]    Delete deployment
    ${response}=   App Cleanup
    Log    ${response}