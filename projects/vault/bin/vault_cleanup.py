#!/usr/bin/env python
import os
import json
from projects.vault.lib.logger import get_logger

logger = get_logger("vault_cleanup")

def get_groups(data):
    # get groups from json data. Need to make sure that groups are only defined once.
    dirty_paths = list()
    api_paths = data.get('api_paths')
    for api_path in api_paths:
        if api_path.get('api_path').startswith('v1/auth/ldap/groups/'):
            dirty_paths.append(dict(namespace=data.get("_namespace"), api_path=api_path)) 
    return dirty_paths

def insert_group(ldap_groups, target_group):
    target_group.pop("namespace")
    ldap_groups['api_paths'].append(target_group)

def remove_group(non_ldap_groups, target_group):
    
    non_ldap_groups['api_paths'].pop(target_group)

def get_non_ldap_groups_files(root_dir):
    for root, dirs, files in os.walk(root_dir, topdown=False):
        ldap_groups_file = os.path.join(root, "ldap-groups-policies.json")
        for file in files:
            if os.path.join(root, file) == ldap_groups_file:
                continue
            elif os.path.join(root, file).endswith(".json"):
                yield os.path.join(root, file)


def get_ldap_groups_files(root_dir):
    for root, dirs, files in os.walk(root_dir, topdown=False):
        ldap_groups_file = os.path.join(root, "ldap-groups-policies.json")
        for file in files:
            if os.path.join(root, file) == ldap_groups_file:
                return os.path.join(root, file)

def clean_file(file_path):
    new_paths = list()
    with open(file_path) as data_file:
        data = json.loads(data_file.read())
        
    for api_path in data['api_paths']:
        if api_path.get('api_path').startswith('v1/auth/ldap/groups/'):
            continue
        else:
            new_paths.append(api_path)
    data['api_paths'] = new_paths
    with open(file_path, 'w') as data_file:
        data_file.write(
            json.dumps(
                data,
                separators=(',',':'),
                indent=4,
                sort_keys=True
            )
        )

def main(directory="."):
    bad_guys = set()
    for root, dirs, files in os.walk(directory, topdown=False):
        for dir in dirs:
            for grpfile in get_non_ldap_groups_files(os.path.join(root, dir)):
                # print(grpfile)
                with open(grpfile) as nlgf:
                    groups_file = json.loads(nlgf.read())
                    ldap_groups = get_groups(groups_file)
                    for group in ldap_groups:
                        bad_guys.add((os.path.abspath(grpfile), json.dumps(group)))

    for actor in bad_guys:
        bad_file = actor[0]
        _dir = os.path.dirname(actor[0])
        data = json.loads(actor[1])
        ldap_groups_file_path = os.path.join(_dir, "ldap-groups-policies.json")
        #  print(actor, _dir, ldap_groups_file_path)
        if os.path.isfile(ldap_groups_file_path):
            with open(os.path.join(_dir, "ldap-groups-policies.json")) as ldap_groups_file:
                ldap_groups = json.loads(ldap_groups_file.read())
        else:
            ldap_groups = {
                "_namespace": data.get('namespace'),
                 "api_paths": list()
            }
        insert_group(ldap_groups, data)
        with open(os.path.join(_dir, "ldap-groups-policies.json"), 'w') as ldap_groups_file:
            ldap_groups_file.write(
                json.dumps(
                    ldap_groups,
                    separators=(',', ':'),
                    indent=4,
                    sort_keys=True
                )
            )
            logger.info("Created: " + os.path.join(_dir, "ldap-groups-policies.json"))
        
        clean_file(bad_file)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Clean up vault ldap groups")
    parser.add_argument("--directory", default=".", help="Directory to clean (default: %(default)s)")
    args = parser.parse_args()
    main(args.directory)
        
            
# some namespace directories dont have ldap-groups-policies.json files, we need to create them.