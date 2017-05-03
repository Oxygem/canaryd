from canaryd.packages import six

from canaryd.plugin import Plugin

# Mapping for iptables code arguments to variable names
IPTABLES_ARGS = {
    '-A': 'chain',
    '-j': 'jump',

    # Boolean matches
    '-p': 'protocol',
    '-s': 'source',
    '-d': 'destination',
    '-i': 'in_interface',
    '-o': 'out_interface',

    # Logging
    '--log-prefix': 'log_prefix',

    # NAT exit rules
    '--to-destination': 'to_destination',
    '--to-source': 'to_source',
    '--to-ports': 'to_ports',
}


class Iptables(Plugin):
    spec = ('chain', {
        'policy': six.text_type,
        'rules': [dict],
    })

    command = 'iptables-save'

    @staticmethod
    def parse(output):
        chains = {}

        for line in output.splitlines():
            # Parse the chains
            if line.startswith(':'):
                line = line[1:]

                chain, policy, _ = line.split()
                chains[chain] = {
                    'rules': [],
                    'policy': policy,
                }

            # Pass the rules
            if not line.startswith('-A'):
                continue

            bits = line.split()

            definition = {}

            key = None
            args = []
            not_arg = False

            def add_args():
                arg_string = ' '.join(args)

                if key in IPTABLES_ARGS:
                    definition_key = (
                        'not_{0}'.format(IPTABLES_ARGS[key])
                        if not_arg
                        else IPTABLES_ARGS[key]
                    )
                    definition[definition_key] = arg_string
                else:
                    definition.setdefault('extras', []).extend((key, arg_string))

            for bit in bits:
                if bit == '!':
                    if key:
                        add_args()
                        args = []
                        key = None

                    not_arg = True

                elif bit.startswith('-'):
                    if key:
                        add_args()
                        args = []
                        not_arg = False

                    key = bit

                else:
                    args.append(bit)

            if key:
                add_args()

            if 'extras' in definition:
                definition['extras'] = definition['extras']

            chain = definition.pop('chain')
            chains[chain]['rules'].append(definition)

        return chains

    @staticmethod
    def generate_events(type_, chain_name, data_changes, settings):
        # We only handle updates here, added/removed chains are handled as default
        if type_ != 'updated':
            return

        # Check policy
        if 'policy' in data_changes:
            yield 'updated', None, {
                'policy': data_changes['policy'],
            }

        # Diff rules
        if 'rules' in data_changes:
            previous_rules, rules = data_changes['rules']

            # Find deleted roles
            deleted_rules = []

            for i, rule in enumerate(previous_rules):
                # If we've run out of rules in the previous state, add
                if len(rules) <= i:
                    deleted_rules.append(rule)

                # Otherwise compare
                elif rules[i] != rule:
                    deleted_rules.append(rule)

            if deleted_rules:
                rule_type = 'rule' if len(deleted_rules) == 1 else 'rules'

                yield 'deleted', '{0} removed from {1}'.format(
                    rule_type.title(),
                    chain_name,
                ), data_changes

            # Find new rules
            new_rules = []

            for i, rule in enumerate(rules):
                # If we've run out of rules in the previous state, add
                if len(previous_rules) <= i:
                    new_rules.append(rule)

                # Otherwise compare
                elif previous_rules[i] != rule:
                    new_rules.append(rule)

            if new_rules:
                rule_type = 'rule' if len(new_rules) == 1 else 'rules'

                yield 'added', '{0} added to {1}'.format(
                    rule_type.title(),
                    chain_name,
                ), data_changes


class Ip6tables(Iptables):
    command = 'ip6tables-save'
