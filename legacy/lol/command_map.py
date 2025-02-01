import pymongo

from lol.commands import (
    backfill,
    champ_dmg,
    champ_kdas,
    champ_pbs,
    champ_winrates,
    help_cmd,
    list_summoners,
    matchups,
    most_seen,
    track_summoner,
    untrack_summoner,
    update_api_key,
    update_matches,
    update_summoners,
    update_v5,
)


class CommandMap(object):

    def __init__(self):
        self.commands = {}

    def register_command(self, command):
        if command.name in self.commands:
            raise RuntimeError(f'Command "{command.name}" is already registered')
        self.commands[command.name] = command

    @staticmethod
    def get_default():
        command_map = CommandMap()

        command_map.register_command(help_cmd.HelpCommand("help", command_map))
        command_map.register_command(track_summoner.TrackSummonerCommand("track"))
        command_map.register_command(untrack_summoner.UntrackSummonerCommand("untrack"))
        command_map.register_command(list_summoners.ListSummonersCommand("list_summoners"))
        command_map.register_command(update_matches.UpdateMatchesCommand("update"))
        command_map.register_command(update_summoners.UpdateSummonersCommand("update_summoners"))
        command_map.register_command(update_api_key.UpdateApiKeyCommand("update_api_key"))
        command_map.register_command(update_v5.UpdateV5Command("update_v5"))
        command_map.register_command(champ_winrates.ChampionWinratesCommand("winrates"))
        command_map.register_command(champ_kdas.ChampionKdasCommand("kdas"))
        command_map.register_command(champ_pbs.ChampionPersonalBestsCommand("pbs"))
        command_map.register_command(most_seen.MostSeenCommand("most_seen"))
        command_map.register_command(matchups.MatchupsCommand("matchups"))
        command_map.register_command(matchups.CurrentMatchupsCommand("current_matchups"))
        command_map.register_command(champ_dmg.ChampionDmgCommand("damage"))
        command_map.register_command(
            backfill.BackfillMatchParticipantPuuidsCommand("backfill_match_participant_puuids")
        )

        client = pymongo.MongoClient()
        for _, command in command_map.commands.items():
            command.set_mongo_client(client)

        return command_map
