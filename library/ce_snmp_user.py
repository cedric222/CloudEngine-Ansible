#!/usr/bin/python
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'version': '1.0'}

DOCUMENTATION = '''
---
module: ce_snmp_user
version_added: "2.3"
short_description: Manages SNMP user configuration.
description:
    - Manages SNMP user configurations on CloudEngine switches.
extends_documentation_fragment: cloudengine
author:
    - wangdezhuang (@CloudEngine-Ansible)
options:
    acl_number:
        description:
            - Access control list number.
        required: false
        default: null
    usm_user_name:
        description:
            - Unique name to identify the USM user.
        required: false
        default: null
    aaa_local_user:
        description:
            - Unique name to identify the local user.
        required: false
        default: null
    remote_engine_id:
        description:
            - Remote engine id of the USM user.
        required: false
        default: null
    user_group:
        description:
            - Name of the group where user belongs to.
        required: false
        default: null
    auth_protocol:
        description:
            - Authentication protocol ( md5 | sha ).
        required: false
        default: null
        choices: ['noAuth', 'md5', 'sha']
    auth_key:
        description:
            - The authentication password. Simple password length <8-255>. Field max.
        required: false
        default: null
    priv_protocol:
        description:
            - Encryption protocol.
        required: false
        default: null
        choices: ['noPriv', 'des56', '3des168', 'aes128', 'aes192', 'aes256']
    priv_key:
        description:
            - The encryption password. Simple password length <8-255>. Field max.
        required: false
        default: null
'''

EXAMPLES = '''
# config SNMP usm user
  - name: "config SNMP usm user"
    ce_snmp_user:
        state:  present
        usm_user_name:  wdz_snmp
        remote_engine_id:  800007DB03389222111200
        acl_number:  2000
        user_group:  wdz_group
        host:  {{inventory_hostname}}
        username:  {{username}}
        password:  {{password}}

# undo SNMP usm user
  - name: "undo SNMP usm user"
    ce_snmp_user:
        state:  absent
        usm_user_name:  wdz_snmp
        remote_engine_id:  800007DB03389222111200
        acl_number:  2000
        user_group:  wdz_group
        host:  {{inventory_hostname}}
        username:  {{username}}
        password:  {{password}}

# config SNMP local user
  - name: "config SNMP local user"
    ce_snmp_user:
        state:  present
        aaa_local_user:  wdz_user
        auth_protocol:  md5
        auth_key:  huawei123
        priv_protocol:  des56
        priv_key:  huawei123
        host:  {{inventory_hostname}}
        username:  {{username}}
        password:  {{password}}

# undo SNMP local user
  - name: "config SNMP local user"
    ce_snmp_user:
        state:  absent
        aaa_local_user:  wdz_user
        auth_protocol:  md5
        auth_key:  huawei123
        priv_protocol:  des56
        priv_key:  huawei123
        host:  {{inventory_hostname}}
        username:  {{username}}
        password:  {{password}}
'''

RETURN = '''
changed:
    description: check to see if a change was made on the device
    returned: always
    type: boolean
    sample: true
proposed:
    description: k/v pairs of parameters passed into module
    returned: always
    type: dict
    sample: {"acl_number": "2000", "remote_engine_id": "800007DB03389222111200",
             "state": "present", "user_group": "wdz_group",
             "usm_user_name": "wdz_snmp"}
existing:
    description:
        - k/v pairs of existing aaa server
    type: dict
    sample: {"snmp local user": {"local_user_info": []},
             "snmp usm user": {"usm_user_info": []}}
end_state:
    description: k/v pairs of aaa params after module execution
    returned: always
    type: dict
    sample: {"snmp local user": {"local_user_info": []},
             "snmp local user": {"local_user_info": [{"aclNumber": "2000", "engineID": "800007DB03389222111200",
                                 "groupName": "wdz_group", "userName": "wdz_snmp"}]}}
updates:
    description: command sent to the device
    returned: always
    type: list
    sample: ["snmp-agent remote-engineid 800007DB03389222111200 usm-user v3 wdz_snmp wdz_group acl 2000"]
'''

import sys
from xml.etree import ElementTree
from ansible.module_utils.network import NetworkModule
from ansible.module_utils.cloudengine import get_netconf

try:
    from ncclient.operations.rpc import RPCError
    HAS_NCCLIENT = True
except ImportError:
    HAS_NCCLIENT = False


# get snmp v3 USM user
CE_GET_SNMP_V3_USM_USER_HEADER = """
    <filter type="subtree">
      <snmp xmlns="http://www.huawei.com/netconf/vrp" content-version="1.0" format-version="1.0">
        <usmUsers>
          <usmUser>
            <userName></userName>
            <remoteEngineID></remoteEngineID>
            <engineID></engineID>
"""
CE_GET_SNMP_V3_USM_USER_TAIL = """
          </usmUser>
        </usmUsers>
      </snmp>
    </filter>
"""
# merge snmp v3 USM user
CE_MERGE_SNMP_V3_USM_USER_HEADER = """
    <config>
      <snmp xmlns="http://www.huawei.com/netconf/vrp" content-version="1.0" format-version="1.0">
        <usmUsers>
          <usmUser operation="merge">
            <userName>%s</userName>
            <remoteEngineID>%s</remoteEngineID>
            <engineID>%s</engineID>
"""
CE_MERGE_SNMP_V3_USM_USER_TAIL = """
          </usmUser>
        </usmUsers>
      </snmp>
    </config>
"""
# create snmp v3 USM user
CE_CREATE_SNMP_V3_USM_USER_HEADER = """
    <config>
      <snmp xmlns="http://www.huawei.com/netconf/vrp" format-version="1.0" content-version="1.0">
        <usmUsers>
          <usmUser operation="create">
            <userName>%s</userName>
            <remoteEngineID>%s</remoteEngineID>
            <engineID>%s</engineID>
"""
CE_CREATE_SNMP_V3_USM_USER_TAIL = """
          </usmUser>
        </usmUsers>
      </snmp>
    </config>
"""
# delete snmp v3 USM user
CE_DELETE_SNMP_V3_USM_USER_HEADER = """
    <config>
      <snmp xmlns="http://www.huawei.com/netconf/vrp" content-version="1.0" format-version="1.0">
        <usmUsers>
          <usmUser operation="delete">
            <userName>%s</userName>
            <remoteEngineID>%s</remoteEngineID>
            <engineID>%s</engineID>
"""
CE_DELETE_SNMP_V3_USM_USER_TAIL = """
          </usmUser>
        </usmUsers>
      </snmp>
    </config>
"""

# get snmp v3 aaa local user
CE_GET_SNMP_V3_LOCAL_USER = """
    <filter type="subtree">
      <snmp xmlns="http://www.huawei.com/netconf/vrp" content-version="1.0" format-version="1.0">
        <localUsers>
          <localUser>
            <userName></userName>
            <authProtocol></authProtocol>
            <authKey></authKey>
            <privProtocol></privProtocol>
            <privKey></privKey>
          </localUser>
        </localUsers>
      </snmp>
    </filter>
"""
# merge snmp v3 aaa local user
CE_MERGE_SNMP_V3_LOCAL_USER = """
    <config>
      <snmp xmlns="http://www.huawei.com/netconf/vrp" content-version="1.0" format-version="1.0">
        <localUsers>
          <localUser operation="merge">
            <userName>%s</userName>
            <authProtocol>%s</authProtocol>
            <authKey>%s</authKey>
            <privProtocol>%s</privProtocol>
            <privKey>%s</privKey>
          </localUser>
        </localUsers>
      </snmp>
    </config>
"""
# create snmp v3 aaa local user
CE_CREATE_SNMP_V3_LOCAL_USER = """
    <config>
      <snmp xmlns="http://www.huawei.com/netconf/vrp" content-version="1.0" format-version="1.0">
        <localUsers>
          <localUser operation="create">
            <userName>%s</userName>
            <authProtocol>%s</authProtocol>
            <authKey>%s</authKey>
            <privProtocol>%s</privProtocol>
            <privKey>%s</privKey>
          </localUser>
        </localUsers>
      </snmp>
    </config>
"""
# delete snmp v3 aaa local user
CE_DELETE_SNMP_V3_LOCAL_USER = """
    <config>
      <snmp xmlns="http://www.huawei.com/netconf/vrp" content-version="1.0" format-version="1.0">
        <localUsers>
          <localUser operation="delete">
            <userName>%s</userName>
            <authProtocol>%s</authProtocol>
            <authKey>%s</authKey>
            <privProtocol>%s</privProtocol>
            <privKey>%s</privKey>
          </localUser>
        </localUsers>
      </snmp>
    </config>
"""


class SnmpUser(object):
    """ Manages SNMP user configuration """

    def __init__(self, **kwargs):
        """ Class init """

        self.local_engine_id = None

        self.netconf = get_netconf(**kwargs)

    def netconf_get_config(self, **kwargs):
        """ Get configure by netconf """

        module = kwargs["module"]
        conf_str = kwargs["conf_str"]

        try:
            con_obj = self.netconf.get_config(filter=conf_str)
        except RPCError:
            err = sys.exc_info()[1]
            module.fail_json(msg='Error: %s' % err.message.replace("\r\n", ""))

        return con_obj

    def netconf_set_config(self, **kwargs):
        """ Set configure by netconf """

        module = kwargs["module"]
        conf_str = kwargs["conf_str"]

        try:
            con_obj = self.netconf.set_config(config=conf_str)
        except RPCError:
            err = sys.exc_info()[1]
            module.fail_json(msg='Error: %s' % err.message.replace("\r\n", ""))

        return con_obj

    def check_snmp_v3_usm_user_args(self, **kwargs):
        """ Check snmp v3 usm user invalid args """

        module = kwargs["module"]
        result = dict()
        result["usm_user_info"] = []
        need_cfg = False
        state = module.params['state']
        usm_user_name = module.params['usm_user_name']
        remote_engine_id = module.params['remote_engine_id']

        acl_number = module.params['acl_number']
        user_group = module.params['user_group']
        auth_protocol = module.params['auth_protocol']
        auth_key = module.params['auth_key']
        priv_protocol = module.params['priv_protocol']
        priv_key = module.params['priv_key']

        local_user_name = module.params['aaa_local_user']

        if usm_user_name:

            if local_user_name:
                module.fail_json(
                    msg='Error: Please do not input usm_user_name and local_user_name at the same time.')

            if len(usm_user_name) > 32 or len(usm_user_name) == 0:
                module.fail_json(
                    msg='Error: The length of usm_user_name %s is out of [1 - 32].' % usm_user_name)
            if remote_engine_id:
                if len(remote_engine_id) > 64 or len(remote_engine_id) < 10:
                    module.fail_json(
                        msg='Error: The length of remote_engine_id %s is out of [10 - 64].' % remote_engine_id)

            conf_str = CE_GET_SNMP_V3_USM_USER_HEADER

            if acl_number:
                if acl_number.isdigit():
                    if int(acl_number) > 2999 or int(acl_number) < 2000:
                        module.fail_json(
                            msg='Error: The value of acl_number %s is out of [2000 - 2999].' % acl_number)
                else:
                    if not acl_number[0].isalpha() or len(acl_number) > 32 or len(acl_number) < 1:
                        module.fail_json(
                            msg='Error: The length of acl_number %s is out of [1 - 32].' % acl_number)

                conf_str += "<aclNumber></aclNumber>"

            if user_group:
                if len(user_group) > 32 or len(user_group) == 0:
                    module.fail_json(
                        msg='Error: The length of user_group %s is out of [1 - 32].' % user_group)

                conf_str += "<groupName></groupName>"

            if auth_protocol:
                conf_str += "<authProtocol></authProtocol>"

            if auth_key:
                if len(auth_key) > 255 or len(auth_key) == 0:
                    module.fail_json(
                        msg='Error: The length of auth_key %s is out of [1 - 255].' % auth_key)

                conf_str += "<authKey></authKey>"

            if priv_protocol:
                if not auth_protocol:
                    module.fail_json(
                        msg='Error: Please input auth_protocol at the same time.')

                conf_str += "<privProtocol></privProtocol>"

            if priv_key:
                if len(priv_key) > 255 or len(priv_key) == 0:
                    module.fail_json(
                        msg='Error: The length of priv_key %s is out of [1 - 255].' % priv_key)
                conf_str += "<privKey></privKey>"

            conf_str += CE_GET_SNMP_V3_USM_USER_TAIL
            con_obj = self.netconf_get_config(module=module, conf_str=conf_str)

            if "<data/>" in con_obj.xml:
                if state == "present":
                    need_cfg = True

            else:
                xml_str = con_obj.xml.replace('\r', '').replace('\n', '').\
                    replace('xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"', "").\
                    replace('xmlns="http://www.huawei.com/netconf/vrp"', "")

                root = ElementTree.fromstring(xml_str)
                usm_user_info = root.findall("data/snmp/usmUsers/usmUser")
                if usm_user_info:
                    for tmp in usm_user_info:
                        tmp_dict = dict()
                        for site in tmp:
                            if site.tag in ["userName", "remoteEngineID", "engineID", "groupName", "authProtocol",
                                            "authKey", "privProtocol", "privKey", "aclNumber"]:
                                tmp_dict[site.tag] = site.text

                        result["usm_user_info"].append(tmp_dict)

                if result["usm_user_info"]:
                    for tmp in result["usm_user_info"]:
                        if "userName" in tmp.keys():
                            if state == "present":
                                if tmp["userName"] != usm_user_name:
                                    need_cfg = True
                            else:
                                if tmp["userName"] == usm_user_name:
                                    need_cfg = True
                        if "remoteEngineID" in tmp.keys():
                            if remote_engine_id:
                                enable = "true"
                            else:
                                enable = "false"

                            if state == "present":
                                if tmp["remoteEngineID"] != enable:
                                    need_cfg = True
                            else:
                                if tmp["remoteEngineID"] == enable:
                                    need_cfg = True
                        if remote_engine_id:
                            if "engineID" in tmp.keys():
                                if state == "present":
                                    if tmp["engineID"] != remote_engine_id:
                                        need_cfg = True
                                else:
                                    if tmp["engineID"] == remote_engine_id:
                                        need_cfg = True
                        if user_group:
                            if "groupName" in tmp.keys():
                                if state == "present":
                                    if tmp["groupName"] != user_group:
                                        need_cfg = True
                                else:
                                    if tmp["groupName"] == user_group:
                                        need_cfg = True
                        if auth_protocol:
                            if "authProtocol" in tmp.keys():
                                if state == "present":
                                    if tmp["authProtocol"] != auth_protocol:
                                        need_cfg = True
                                else:
                                    if tmp["authProtocol"] == auth_protocol:
                                        need_cfg = True
                        if auth_key:
                            if "authKey" in tmp.keys():
                                if state == "present":
                                    if tmp["authKey"] != auth_key:
                                        need_cfg = True
                                else:
                                    if tmp["authKey"] == auth_key:
                                        need_cfg = True
                        if priv_protocol:
                            if "privProtocol" in tmp.keys():
                                if state == "present":
                                    if tmp["privProtocol"] != priv_protocol:
                                        need_cfg = True
                                else:
                                    if tmp["privProtocol"] == priv_protocol:
                                        need_cfg = True
                        if priv_key:
                            if "privKey" in tmp.keys():
                                if state == "present":
                                    if tmp["privKey"] != priv_key:
                                        need_cfg = True
                                else:
                                    if tmp["privKey"] == priv_key:
                                        need_cfg = True
                        if acl_number:
                            if "aclNumber" in tmp.keys():
                                if state == "present":
                                    if tmp["aclNumber"] != acl_number:
                                        need_cfg = True
                                else:
                                    if tmp["aclNumber"] == acl_number:
                                        need_cfg = True

        result["need_cfg"] = need_cfg
        return result

    def check_snmp_v3_local_user_args(self, **kwargs):
        """ Check snmp v3 local user invalid args """

        module = kwargs["module"]
        result = dict()
        result["local_user_info"] = []
        need_cfg = False
        state = module.params['state']
        local_user_name = module.params['aaa_local_user']
        auth_protocol = module.params['auth_protocol']
        auth_key = module.params['auth_key']
        priv_protocol = module.params['priv_protocol']
        priv_key = module.params['priv_key']

        usm_user_name = module.params['usm_user_name']

        if local_user_name:

            if usm_user_name:
                module.fail_json(
                    msg='Error: Please do not input usm_user_name and local_user_name at the same time.')

            if not auth_protocol or not auth_key or not priv_protocol or not priv_key:
                module.fail_json(
                    msg='Error: Please input auth_protocol auth_key priv_protocol priv_key for local user.')

            if len(local_user_name) > 32 or len(local_user_name) == 0:
                module.fail_json(
                    msg='Error: The length of local_user_name %s is out of [1 - 32].' % local_user_name)

            if len(auth_key) > 255 or len(auth_key) == 0:
                module.fail_json(
                    msg='Error: The length of auth_key %s is out of [1 - 255].' % auth_key)

            if len(priv_key) > 255 or len(priv_key) == 0:
                module.fail_json(
                    msg='Error: The length of priv_key %s is out of [1 - 255].' % priv_key)

            conf_str = CE_GET_SNMP_V3_LOCAL_USER
            con_obj = self.netconf_get_config(module=module, conf_str=conf_str)

            if "<data/>" in con_obj.xml:
                if state == "present":
                    need_cfg = True

            else:
                xml_str = con_obj.xml.replace('\r', '').replace('\n', '').\
                    replace('xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"', "").\
                    replace('xmlns="http://www.huawei.com/netconf/vrp"', "")

                root = ElementTree.fromstring(xml_str)
                local_user_info = root.findall(
                    "data/snmp/localUsers/localUser")
                if local_user_info:
                    for tmp in local_user_info:
                        tmp_dict = dict()
                        for site in tmp:
                            if site.tag in ["userName", "authProtocol", "authKey", "privProtocol", "privKey"]:
                                tmp_dict[site.tag] = site.text

                        result["local_user_info"].append(tmp_dict)

                if result["local_user_info"]:
                    for tmp in result["local_user_info"]:
                        if "userName" in tmp.keys():
                            if state == "present":
                                if tmp["userName"] != local_user_name:
                                    need_cfg = True
                            else:
                                if tmp["userName"] == local_user_name:
                                    need_cfg = True
                        if auth_protocol:
                            if "authProtocol" in tmp.keys():
                                if state == "present":
                                    if tmp["authProtocol"] != auth_protocol:
                                        need_cfg = True
                                else:
                                    if tmp["authProtocol"] == auth_protocol:
                                        need_cfg = True
                        if auth_key:
                            if "authKey" in tmp.keys():
                                if state == "present":
                                    if tmp["authKey"] != auth_key:
                                        need_cfg = True
                                else:
                                    if tmp["authKey"] == auth_key:
                                        need_cfg = True
                        if priv_protocol:
                            if "privProtocol" in tmp.keys():
                                if state == "present":
                                    if tmp["privProtocol"] != priv_protocol:
                                        need_cfg = True
                                else:
                                    if tmp["privProtocol"] == priv_protocol:
                                        need_cfg = True
                        if priv_key:
                            if "privKey" in tmp.keys():
                                if state == "present":
                                    if tmp["privKey"] != priv_key:
                                        need_cfg = True
                                else:
                                    if tmp["privKey"] == priv_key:
                                        need_cfg = True

        result["need_cfg"] = need_cfg
        return result

    def merge_snmp_v3_usm_user(self, **kwargs):
        """ Merge snmp v3 usm user operation """

        module = kwargs["module"]
        usm_user_name = module.params['usm_user_name']
        remote_engine_id = module.params['remote_engine_id']
        acl_number = module.params['acl_number']
        user_group = module.params['user_group']
        auth_protocol = module.params['auth_protocol']
        auth_key = module.params['auth_key']
        priv_protocol = module.params['priv_protocol']
        priv_key = module.params['priv_key']

        cmds = []

        if remote_engine_id:
            conf_str = CE_MERGE_SNMP_V3_USM_USER_HEADER % (
                usm_user_name, "true", remote_engine_id)
            cmd = "snmp-agent remote-engineid %s usm-user v3 %s" % (
                remote_engine_id, usm_user_name)
        else:
            if not self.local_engine_id:
                module.fail_json(
                    msg='Error: The local engine id is null, please input remote_engine_id.')

            conf_str = CE_MERGE_SNMP_V3_USM_USER_HEADER % (
                usm_user_name, "false", self.local_engine_id)
            cmd = "snmp-agent usm-user v3 %s" % usm_user_name

        if user_group:
            conf_str += "<groupName>%s</groupName>" % user_group
            cmd += " %s" % user_group

        if acl_number:
            conf_str += "<aclNumber>%s</aclNumber>" % acl_number
            cmd += " acl %s" % acl_number

        cmds.append(cmd)

        if remote_engine_id:
            cmd = "snmp-agent remote-engineid %s usm-user v3 %s" % (
                remote_engine_id, usm_user_name)
        else:
            cmd = "snmp-agent usm-user v3 %s" % usm_user_name

        if auth_protocol:
            conf_str += "<authProtocol>%s</authProtocol>" % auth_protocol

            if auth_protocol != "noAuth":
                cmd += " authentication-mode %s" % auth_protocol

        if auth_key:
            conf_str += "<authKey>%s</authKey>" % auth_key

            if auth_protocol != "noAuth":
                cmd += " cipher %s" % "******"

        cmds.append(cmd)

        if remote_engine_id:
            cmd = "snmp-agent remote-engineid %s usm-user v3 %s" % (
                remote_engine_id, usm_user_name)
        else:
            cmd = "snmp-agent usm-user v3 %s" % usm_user_name

        if priv_protocol:
            conf_str += "<privProtocol>%s</privProtocol>" % priv_protocol

            if auth_protocol != "noAuth" and priv_protocol != "noPriv":
                cmd += " privacy-mode %s" % priv_protocol

        if priv_key:
            conf_str += "<privKey>%s</privKey>" % priv_key

            if auth_protocol != "noAuth" and priv_protocol != "noPriv":
                cmd += " cipher  %s" % "******"

        cmds.append(cmd)

        conf_str += CE_MERGE_SNMP_V3_USM_USER_TAIL
        con_obj = self.netconf_set_config(module=module, conf_str=conf_str)

        if "<ok/>" not in con_obj.xml:
            module.fail_json(msg='Error: Merge snmp v3 usm user failed.')

        return cmds

    def create_snmp_v3_usm_user(self, **kwargs):
        """ Create snmp v3 usm user operation """

        module = kwargs["module"]
        usm_user_name = module.params['usm_user_name']
        remote_engine_id = module.params['remote_engine_id']
        acl_number = module.params['acl_number']
        user_group = module.params['user_group']
        auth_protocol = module.params['auth_protocol']
        auth_key = module.params['auth_key']
        priv_protocol = module.params['priv_protocol']
        priv_key = module.params['priv_key']

        cmds = []

        if remote_engine_id:
            conf_str = CE_CREATE_SNMP_V3_USM_USER_HEADER % (
                usm_user_name, "true", remote_engine_id)
            cmd = "snmp-agent remote-engineid %s usm-user v3 %s" % (
                remote_engine_id, usm_user_name)
        else:
            if not self.local_engine_id:
                module.fail_json(
                    msg='Error: The local engine id is null, please input remote_engine_id.')

            conf_str = CE_CREATE_SNMP_V3_USM_USER_HEADER % (
                usm_user_name, "false", self.local_engine_id)
            cmd = "snmp-agent usm-user v3 %s" % usm_user_name

        if user_group:
            conf_str += "<groupName>%s</groupName>" % user_group
            cmd += " %s" % user_group

        if acl_number:
            conf_str += "<aclNumber>%s</aclNumber>" % acl_number
            cmd += " acl %s" % acl_number

        cmds.append(cmd)

        if remote_engine_id:
            cmd = "snmp-agent remote-engineid %s usm-user v3 %s" % (
                remote_engine_id, usm_user_name)
        else:
            cmd = "snmp-agent usm-user v3 %s" % usm_user_name

        if auth_protocol:
            conf_str += "<authProtocol>%s</authProtocol>" % auth_protocol

            if auth_protocol != "noAuth":
                cmd += " authentication-mode %s" % auth_protocol

        if auth_key:
            conf_str += "<authKey>%s</authKey>" % auth_key

            if auth_protocol != "noAuth":
                cmd += " cipher %s" % "******"

        cmds.append(cmd)

        if remote_engine_id:
            cmd = "snmp-agent remote-engineid %s usm-user v3 %s" % (
                remote_engine_id, usm_user_name)
        else:
            cmd = "snmp-agent usm-user v3 %s" % usm_user_name

        if priv_protocol:
            conf_str += "<privProtocol>%s</privProtocol>" % priv_protocol

            if auth_protocol != "noAuth" and priv_protocol != "noPriv":
                cmd += " privacy-mode %s" % priv_protocol

        if priv_key:
            conf_str += "<privKey>%s</privKey>" % priv_key

            if auth_protocol != "noAuth" and priv_protocol != "noPriv":
                cmd += " cipher  %s" % "******"

        cmds.append(cmd)

        conf_str += CE_CREATE_SNMP_V3_USM_USER_TAIL
        con_obj = self.netconf_set_config(module=module, conf_str=conf_str)

        if "<ok/>" not in con_obj.xml:
            module.fail_json(msg='Error: Create snmp v3 usm user failed.')

        return cmds

    def delete_snmp_v3_usm_user(self, **kwargs):
        """ Delete snmp v3 usm user operation """

        module = kwargs["module"]
        usm_user_name = module.params['usm_user_name']
        remote_engine_id = module.params['remote_engine_id']
        acl_number = module.params['acl_number']
        user_group = module.params['user_group']
        auth_protocol = module.params['auth_protocol']
        auth_key = module.params['auth_key']
        priv_protocol = module.params['priv_protocol']
        priv_key = module.params['priv_key']

        if remote_engine_id:
            conf_str = CE_DELETE_SNMP_V3_USM_USER_HEADER % (
                usm_user_name, "true", remote_engine_id)
            cmd = "undo snmp-agent remote-engineid %s usm-user v3 %s" % (
                remote_engine_id, usm_user_name)
        else:
            if not self.local_engine_id:
                module.fail_json(
                    msg='Error: The local engine id is null, please input remote_engine_id.')

            conf_str = CE_DELETE_SNMP_V3_USM_USER_HEADER % (
                usm_user_name, "false", self.local_engine_id)
            cmd = "undo snmp-agent usm-user v3 %s" % usm_user_name

        if user_group:
            conf_str += "<groupName>%s</groupName>" % user_group

        if acl_number:
            conf_str += "<aclNumber>%s</aclNumber>" % acl_number

        if auth_protocol:
            conf_str += "<authProtocol>%s</authProtocol>" % auth_protocol

        if auth_key:
            conf_str += "<authKey>%s</authKey>" % auth_key

        if priv_protocol:
            conf_str += "<privProtocol>%s</privProtocol>" % priv_protocol

        if priv_key:
            conf_str += "<privKey>%s</privKey>" % priv_key

        conf_str += CE_DELETE_SNMP_V3_USM_USER_TAIL
        con_obj = self.netconf_set_config(module=module, conf_str=conf_str)

        if "<ok/>" not in con_obj.xml:
            module.fail_json(msg='Error: Delete snmp v3 usm user failed.')

        return cmd

    def merge_snmp_v3_local_user(self, **kwargs):
        """ Merge snmp v3 local user operation """

        module = kwargs["module"]
        local_user_name = module.params['aaa_local_user']
        auth_protocol = module.params['auth_protocol']
        auth_key = module.params['auth_key']
        priv_protocol = module.params['priv_protocol']
        priv_key = module.params['priv_key']

        conf_str = CE_MERGE_SNMP_V3_LOCAL_USER % (
            local_user_name, auth_protocol, auth_key, priv_protocol, priv_key)
        con_obj = self.netconf_set_config(module=module, conf_str=conf_str)

        if "<ok/>" not in con_obj.xml:
            module.fail_json(msg='Error: Merge snmp v3 local user failed.')

        cmd = "snmp-agent local-user v3 %s " % local_user_name + "authentication-mode %s " % auth_protocol + \
            "cipher ****** " + "privacy-mode %s " % priv_protocol + "cipher  ******"

        return cmd

    def create_snmp_v3_local_user(self, **kwargs):
        """ Create snmp v3 local user operation """

        module = kwargs["module"]
        local_user_name = module.params['aaa_local_user']
        auth_protocol = module.params['auth_protocol']
        auth_key = module.params['auth_key']
        priv_protocol = module.params['priv_protocol']
        priv_key = module.params['priv_key']

        conf_str = CE_CREATE_SNMP_V3_LOCAL_USER % (
            local_user_name, auth_protocol, auth_key, priv_protocol, priv_key)
        con_obj = self.netconf_set_config(module=module, conf_str=conf_str)

        if "<ok/>" not in con_obj.xml:
            module.fail_json(msg='Error: Create snmp v3 local user failed.')

        cmd = "snmp-agent local-user v3 %s " % local_user_name + "authentication-mode %s " % auth_protocol + \
            "cipher ****** " + "privacy-mode %s " % priv_protocol + "cipher  ******"

        return cmd

    def delete_snmp_v3_local_user(self, **kwargs):
        """ Delete snmp v3 local user operation """

        module = kwargs["module"]
        local_user_name = module.params['aaa_local_user']
        auth_protocol = module.params['auth_protocol']
        auth_key = module.params['auth_key']
        priv_protocol = module.params['priv_protocol']
        priv_key = module.params['priv_key']

        conf_str = CE_DELETE_SNMP_V3_LOCAL_USER % (
            local_user_name, auth_protocol, auth_key, priv_protocol, priv_key)
        con_obj = self.netconf_set_config(module=module, conf_str=conf_str)

        if "<ok/>" not in con_obj.xml:
            module.fail_json(msg='Error: Delete snmp v3 local user failed.')

        cmd = "undo snmp-agent local-user v3 %s" % local_user_name

        return cmd

    def get_snmp_local_engine(self, **kwargs):
        """ Get snmp local engine operation """

        module = kwargs["module"]

        regular = "| include snmp | include local-engineid"
        tmp_cfg = module.config.get_config(
            include_all=True, regular=regular)

        if tmp_cfg:
            tmp_data = tmp_cfg.split(r"snmp-agent local-engineid ")
            self.local_engine_id = tmp_data[1]


def main():
    """ Module main function """

    argument_spec = dict(
        state=dict(choices=['present', 'absent'], default='present'),
        acl_number=dict(type='str'),
        usm_user_name=dict(type='str'),
        remote_engine_id=dict(type='str'),
        user_group=dict(type='str'),
        auth_protocol=dict(choices=['noAuth', 'md5', 'sha']),
        auth_key=dict(type='str', no_log=True),
        priv_protocol=dict(
            choices=['noPriv', 'des56', '3des168', 'aes128', 'aes192', 'aes256']),
        priv_key=dict(type='str', no_log=True),
        aaa_local_user=dict(type='str')
    )

    if not HAS_NCCLIENT:
        raise Exception("the ncclient library is required")

    module = NetworkModule(argument_spec=argument_spec,
                           connect_on_load=False,
                           supports_check_mode=True)

    changed = False
    proposed = dict()
    existing = dict()
    end_state = dict()
    updates = []

    state = module.params['state']
    host = module.params['host']
    port = module.params['port']
    username = module.params['username']
    password = module.params['password']
    acl_number = module.params['acl_number']
    usm_user_name = module.params['usm_user_name']
    remote_engine_id = module.params['remote_engine_id']
    user_group = module.params['user_group']
    auth_protocol = module.params['auth_protocol']
    auth_key = module.params['auth_key']
    priv_protocol = module.params['priv_protocol']
    priv_key = module.params['priv_key']
    aaa_local_user = module.params['aaa_local_user']

    snmp_user_obj = SnmpUser(
        host=host, port=port, username=username, password=password)

    if not snmp_user_obj:
        module.fail_json(msg='Error: Init module failed.')

    # get proposed
    proposed["state"] = state
    if acl_number:
        proposed["acl_number"] = acl_number
    if usm_user_name:
        proposed["usm_user_name"] = usm_user_name
    if remote_engine_id:
        proposed["remote_engine_id"] = remote_engine_id
    if user_group:
        proposed["user_group"] = user_group
    if auth_protocol:
        proposed["auth_protocol"] = auth_protocol
    if auth_key:
        proposed["auth_key"] = auth_key
    if priv_protocol:
        proposed["priv_protocol"] = priv_protocol
    if priv_key:
        proposed["priv_key"] = priv_key
    if aaa_local_user:
        proposed["aaa_local_user"] = aaa_local_user

    snmp_v3_usm_user_rst = snmp_user_obj.check_snmp_v3_usm_user_args(
        module=module)
    snmp_v3_local_user_rst = snmp_user_obj.check_snmp_v3_local_user_args(
        module=module)

    snmp_user_obj.get_snmp_local_engine(module=module)

    # state exist snmp v3 user config
    exist_tmp = dict()
    for item in snmp_v3_usm_user_rst:
        if item != "need_cfg":
            exist_tmp[item] = snmp_v3_usm_user_rst[item]
    if exist_tmp:
        existing["snmp usm user"] = exist_tmp

    exist_tmp = dict()
    for item in snmp_v3_local_user_rst:
        if item != "need_cfg":
            exist_tmp[item] = snmp_v3_local_user_rst[item]
    if exist_tmp:
        existing["snmp local user"] = exist_tmp

    if state == "present":
        if snmp_v3_usm_user_rst["need_cfg"]:
            if len(snmp_v3_usm_user_rst["usm_user_info"]) != 0:
                cmd = snmp_user_obj.merge_snmp_v3_usm_user(module=module)
                changed = True
                updates.append(cmd)
            else:
                cmd = snmp_user_obj.create_snmp_v3_usm_user(module=module)
                changed = True
                updates.append(cmd)

        if snmp_v3_local_user_rst["need_cfg"]:
            if len(snmp_v3_local_user_rst["local_user_info"]) != 0:
                cmd = snmp_user_obj.merge_snmp_v3_local_user(
                    module=module)
                changed = True
                updates.append(cmd)
            else:
                cmd = snmp_user_obj.create_snmp_v3_local_user(
                    module=module)
                changed = True
                updates.append(cmd)

    else:
        if snmp_v3_usm_user_rst["need_cfg"]:
            cmd = snmp_user_obj.delete_snmp_v3_usm_user(module=module)
            changed = True
            updates.append(cmd)
        if snmp_v3_local_user_rst["need_cfg"]:
            cmd = snmp_user_obj.delete_snmp_v3_local_user(module=module)
            changed = True
            updates.append(cmd)

    # state exist snmp v3 user config
    snmp_v3_usm_user_rst = snmp_user_obj.check_snmp_v3_usm_user_args(
        module=module)
    end_tmp = dict()
    for item in snmp_v3_usm_user_rst:
        if item != "need_cfg":
            end_tmp[item] = snmp_v3_usm_user_rst[item]
    if end_tmp:
        end_state["snmp usm user"] = end_tmp

    snmp_v3_local_user_rst = snmp_user_obj.check_snmp_v3_local_user_args(
        module=module)
    end_tmp = dict()
    for item in snmp_v3_local_user_rst:
        if item != "need_cfg":
            end_tmp[item] = snmp_v3_local_user_rst[item]
    if end_tmp:
        end_state["snmp local user"] = end_tmp

    results = dict()
    results['proposed'] = proposed
    results['existing'] = existing
    results['changed'] = changed
    results['end_state'] = end_state
    results['updates'] = updates

    module.exit_json(**results)


if __name__ == '__main__':
    main()
