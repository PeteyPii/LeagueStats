import textwrap

from lol import command


class HelpCommand(command.Command):

    def __init__(self, name, command_map):
        super().__init__(name)
        self._command_map = command_map

    def help_message(self):
        return (
            f"Usage: {self._program} {self.name} [command]\n"
            "Prints a help message about all commands or one particular command."
        )

    def _run_impl(self, args):
        if len(args) > 1:
            self.print_invalid_usage()
            print("")

        if len(args) != 1 or args[0] not in self._command_map.commands:
            print("Available commands:")
            for name in sorted(self._command_map.commands):
                command = self._command_map.commands[name]
                if not command.is_expert_command() or self.flag("x"):
                    print(f"  {name}")
                    print(textwrap.indent(command.help_message(), "    "))
        else:
            print(self._command_map.commands[args[0]].help_message())
            if self._command_map.commands[args[0]]._flags:
                print("\nAvailable flags:")
                print(textwrap.indent(self._command_map.commands[args[0]].help_message_flags(), "  "))
