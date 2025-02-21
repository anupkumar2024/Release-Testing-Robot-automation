#! /bin/bash

# Run backup restore robin bundle app test
#cd backup_restore && robot -d ../outputs/bundleAppRestore/  backup_restore_bundle.robot 

# Run backup restore helm app
robot -d ../outputs/helmAppRestore/  backup_restore_helm.robot 

