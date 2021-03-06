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
module: ce_evpn_global
version_added: "2.3"
short_description: Manages global configuration of EVPN.
extends_documentation_fragment: cloudengine
description:
    - Manages global configuration of EVPN.
author: Zhijin Zhou (@CloudEngine-Ansible)
notes:
    - Before configuring evpn_overlay_enable=false, delete other EVPN configurations.
options:
    evpn_overlay_enable:
        description:
            - configure EVPN as the VXLAN control plane.
        required: true
        choices: ['true','false']
'''

EXAMPLES = '''
# Configure EVPN as the VXLAN control plan
- ce_evpn_global: evpn_overlay_enable=true
# Unconfigure EVPN as the VXLAN control plan
- ce_evpn_global: evpn_overlay_enable=false
'''

RETURN = '''
proposed:
    description: k/v pairs of parameters passed into module
    returned: always
    type: dict
    sample: {
                "evpn_overlay_enable": "true"
            }
existing:
    description: k/v pairs of existing attributes on the device
    type: dict
    sample: {
                "evpn_overlay_enable": "false"
            }
end_state:
    description: k/v pairs of end attributes on the interface
    returned: always
    type: dict or null
    sample: {
                "evpn_overlay_enable": "true"
            }
updates:
    description: command list sent to the device
    returned: always
    type: list
    sample: [
                "evpn-overlay enable",
            ]
changed:
    description: check to see if a change was made on the device
    returned: always
    type: boolean
    sample: true
'''


from ansible.module_utils.network import NetworkModule, NetworkError
from ansible.module_utils.cloudengine import get_cli_exception


class EvpnGlobal(object):
    """Manange global configuration of EVPN"""

    def __init__(self, argument_spec, ):
        self.spec = argument_spec
        self.module = None
        self.init_module()

        # EVPN global configuration parameters
        self.overlay_enable = self.module.params['evpn_overlay_enable']

        self.commands = list()
        self.global_info = dict()
        self.conf_exist = False

        # host info
        self.host = self.module.params['host']
        self.username = self.module.params['username']
        self.password = self.module.params['password']
        self.port = self.module.params['port']

        # state
        self.changed = False
        self.updates_cmd = list()
        self.results = dict()
        self.proposed = dict()
        self.existing = dict()
        self.end_state = dict()

    def init_module(self):
        """init_module"""
        self.module = NetworkModule(
            argument_spec=self.spec, connect_on_load=False, supports_check_mode=True)

    def cli_load_config(self, commands):
        """load config by cli"""
        if not self.module.check_mode:
            try:
                self.module.config.load_config(commands)
            except NetworkError:
                err = get_cli_exception()
                self.module.fail_json(msg=err)

    def cli_add_command(self, command, undo=False):
        """add command to self.update_cmd and self.commands"""
        if undo and command.lower() not in ["quit", "return"]:
            cmd = "undo " + command
        else:
            cmd = command

        self.commands.append(cmd)          # set to device
        if command.lower() not in ["quit", "return"]:
            self.updates_cmd.append(cmd)   # show updates result

    def get_evpn_global_info(self):
        """ get current EVPN global configration"""
        self.global_info['evpnOverLay'] = 'false'

        exp = " | include evpn-overlay enable"
        config = self.module.config.get_config(
            include_defaults=False, regular=exp)
        if config:
            self.global_info['evpnOverLay'] = 'true'

    def get_existing(self):
        """get existing config"""
        self.existing = dict(
            evpn_overlay_enable=self.global_info['evpnOverLay'])

    def get_proposed(self):
        """get proposed config"""
        self.proposed = dict(evpn_overlay_enable=self.overlay_enable)

    def get_end_state(self):
        """get end config"""
        self.get_evpn_global_info()
        self.end_state = dict(
            evpn_overlay_enable=self.global_info['evpnOverLay'])

    def show_result(self):
        """ show result"""
        self.results['changed'] = self.changed
        self.results['proposed'] = self.proposed
        self.results['existing'] = self.existing
        self.results['end_state'] = self.end_state
        if self.changed:
            self.results['updates'] = self.updates_cmd
        else:
            self.results['updates'] = list()

        self.module.exit_json(**self.results)

    def judge_if_config_exist(self):
        """ judge whether configuration has existed"""
        if self.overlay_enable == self.global_info['evpnOverLay']:
            return True

        return False

    def config_evnp_global(self):
        """ set global EVPN configration"""
        if not self.conf_exist:
            if self.overlay_enable == 'true':
                self.cli_add_command('evpn-overlay enable')
            else:
                self.cli_add_command('evpn-overlay enable', True)

            if self.commands:
                self.cli_load_config(self.commands)
                self.changed = True

    def work(self):
        """excute task"""
        self.get_evpn_global_info()
        self.get_existing()
        self.get_proposed()
        self.conf_exist = self.judge_if_config_exist()

        self.config_evnp_global()

        self.get_end_state()
        self.show_result()


def main():
    """main function entry"""

    argument_spec = dict(
        evpn_overlay_enable=dict(
            required=True, type='str', choices=['true', 'false']),
    )

    evpn_global = EvpnGlobal(argument_spec)
    evpn_global.work()

if __name__ == '__main__':
    main()
