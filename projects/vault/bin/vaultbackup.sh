#!/bin/bash
set -x 
mode=${1}
vault_path=${2}
vault_cluster=${3}
vault_ldap=${4:-ldap}
vault_namespace=${5:-puppet}
export VAULT_ADDR="https://vault-${vault_cluster}01.corp.clover.com:8200"
export VAULT_NAMESPACE=${vault_namespace}
vault login -method=ldap -path=${vault_ldap} username=${LDAP_USERNAME}

function backup {
    touch backup-$(basename ${vault_path})-${vault_cluster}.bkup
    vault_path=${1}
    vault read ${vault_path} --format=json | jq -r .data > $(basename ${vault_path})-${vault_cluster}.json
}

function restore {
    vault_path=${1}
    stat backup-$(basename ${vault_path})-${vault_cluster}.bkup || exit 1;
    vault write ${vault_path} @$(basename ${vault_path})-${vault_cluster}.json
    rm backup-$(basename ${vault_path})-${vault_cluster}.bkup
}

case ${mode} in

  backup)
    backup ${vault_path}
    ;;

  restore)
    restore ${vault_path}
esac
