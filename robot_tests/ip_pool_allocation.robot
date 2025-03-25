*** Settings ***
Library        ip_pool_allocation.py
Library        JSONLibrary
Resource       ${resource_dir}/robin_base.robot


Suite Setup        Open Connection and Log In      ${master-node-ip}


*** Test Cases ***
Load JSON File 
    ${data}=    Load JSON From File    ${resource_dir}/vars.json
    Set Suite Variable    @{ip_pool_name}    ${data['ip_pool_name']}
    Set Suite Variable    ${ip_pool_macvlan}    ${data['ip_pool_macvlan']}


Fetch Robin Token
    [Documentation]    Create Robin login and fetch auth token
    ${response}=    Robin Login
    Log  ${response}
    Set Suite Variable   ${auth_token}   ${response[1]}
    Should Be Equal As Numbers  ${response[2]}  200

Robin Manual Login
    Robin Login From Robot

IP Pool Allocation
    [Documentation]    Add IP Pool of ovs sriov dpdk
    ${response}=    IP Pool Allocation   ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers  ${response[1]}  200

IP Pool macvlan allocation
    [Documentation]    Add IP Pool of macvlan
    ${response}=    IP Pool macvlan Allocation   ${auth_token}
    Log  ${response}
    Should Be Equal As Numbers  ${response[1]}  200

List Robin ip-pool
    ${ip-pool-list}=    List ip-pool
    Log    \n${ip-pool-list}    console=yes

Delete Robin ip-pool
    FOR  ${ip-pool}  IN   @{ip_pool_name}[0]  
        Deregister ip-pool    ${ip-pool}
    END
    Deregister ip-pool    ${ip_pool_macvlan}             


