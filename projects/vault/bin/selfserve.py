#!/usr/bin/env python3

"""
    selfserve.py
"""

import os
import json
from jinja2 import Template


def create_secrets_engine_and_policies(template, service_name, env_name, namespace):
    """
    create_secrets_engine_and_policies:
    """
    with open(template, encoding="utf-8") as self_serve:
        self_serve_tpl = Template(self_serve.read())

    j_data = json.loads(
        self_serve_tpl.render(
            namespace=namespace, service_name=service_name, env_name=env_name
        )
    )

    with open(os.path.join(os.getcwd(), f"{service_name}.json"), 'w', encoding="utf-8") as output:
        output.write(
            json.dumps(
                j_data,
                separators=(',', ':'),
                indent=4,
                sort_keys=True
            )
        )


    return dict(
        read=f"{service_name}-{env_name}-read-access",
        write=f"{service_name}-{env_name}-write-access",
    )


def get_groups(data):
    """
    get_groups:
    """
    # get groups from json data. Need to make sure that groups are only defined once.
    groups = []
    api_paths = data.get("api_paths")
    for api_path in api_paths:
        if api_path.get("api_path").startswith("v1/auth/ldap/groups/"):
            groups.append(api_path.get("api_path").split("/")[-1])
    return groups


def get_namespace():
    """
    get_namespace:
    """
    my_dir = os.getcwd()
    return my_dir.split("/")[-1]


def get_default_template():
    """
    get_default_template:
    """
    return os.path.join(os.path.dirname(__file__), "./templates/selfserve.json.tpl")


def main(service_name, env_name, namespace, read_access, write_access, template):
    """
    main:
    """
    policies = create_secrets_engine_and_policies(
        template, service_name, env_name, namespace
    )
    add_ldap_groups(read_access, write_access, policies)


def prompt_add(data):
    """
    prompt_add:
    """
    group_name = data.get("api_path").split("/")[-1]
    if (
        input(
            f"{group_name} was not in found in ldap configuration. Would you like to add? [y|n]"
        ).strip()
        == "y"
    ):
        return True
    return False


def add_ldap_groups(read_access, write_access, policies):
    """
    add_ldap_groups:
    """
    read_policy = policies.get("read")
    write_policy = policies.get("write")

    with open(
        os.path.join(os.getcwd(), "ldap-groups-policies.json"), "r", encoding="utf-8"
    ) as ldap_groups:
        ldap_group_json = json.loads(ldap_groups.read())
        current_groups = get_groups(ldap_group_json)
        new_groups = set()
        for ldap_group in ldap_group_json.get("api_paths"):
            for group in read_access:
                if group not in current_groups:
                    data = {
                        "api_action": "post",
                        "api_path": f"v1/auth/ldap/groups/{group}",
                        "api_payload": {"policies": [read_policy]},
                    }
                    new_groups.add(json.dumps(data))
                if ldap_group.get("api_path").endswith(f"/{group}"):
                    if read_policy in ldap_group["api_payload"]["policies"]:
                        continue
                    ldap_group["api_payload"]["policies"].append(read_policy)

            for group in write_access:
                if group not in current_groups:
                    data = {
                        "api_action": "post",
                        "api_path": f"v1/auth/ldap/groups/{group}",
                        "api_payload": {"policies": [write_policy]},
                    }
                    new_groups.add(json.dumps(data))
                if ldap_group.get("api_path").endswith(f"/{group}"):
                    if write_policy in ldap_group["api_payload"]["policies"]:
                        continue
                    ldap_group["api_payload"]["policies"].append(write_policy)

        for group in new_groups:
            group = json.loads(group)
            if prompt_add(group):
                ldap_group_json["api_paths"].append(group)

    with open(
        os.path.join(os.getcwd(), "ldap-groups-policies.json"), "w", encoding="utf-8"
    ) as ldap_groups:
        ldap_groups.write(
            json.dumps(ldap_group_json, separators=(",", ":"), indent=4, sort_keys=True)
        )


if __name__ == "__main__":
    from optparse import OptionParser, OptionGroup

    p = OptionParser()
    p.add_option(
        "--template",
        default=get_default_template(),
        help="specify template. default: %default",
    )
    perms = OptionGroup(
        p, "Permissions", "Specify which LDAP groups should have read and write access"
    )
    perms.add_option("-r", dest="read_access", default=[], action="append")
    perms.add_option("-w", dest="write_access", default=[], action="append")
    p.add_option_group(perms)
    svc = OptionGroup(p, "Service", "Specify name, environment, and namespace")
    svc.add_option("--service")
    svc.add_option("--namespace", help="default: %default", default=get_namespace())
    svc.add_option("--env")
    p.add_option_group(svc)
    opt, args = p.parse_args()
    main(
        opt.service,
        opt.env,
        opt.namespace,
        opt.read_access,
        opt.write_access,
        opt.template,
    )
