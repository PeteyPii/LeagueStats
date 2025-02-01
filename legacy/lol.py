import os
import sys

import cassiopeia as cass

from lol import command_map


def main(argv):
    cass.apply_settings(os.path.join(os.getcwd(), "settings.json"))
    # cass.set_default_region('NA')
    all_commands_map = command_map.CommandMap.get_default()

    if len(argv) <= 1:
        print(f"Invalid usage. Usage: {sys.argv[0]} <command> [args...]\n")
        all_commands_map.commands["help"].run([])
        sys.exit(1)
    try:
        command = all_commands_map.commands[argv[1]]
    except KeyError:
        print(f'Unknown command "{argv[1]}"')
        print(f"Usage: {sys.argv[0]} <command> [args...]\n")
        all_commands_map.commands["help"].run([])
        sys.exit(1)

    command.run(argv[2:])


if __name__ == "__main__":
    main(sys.argv)
