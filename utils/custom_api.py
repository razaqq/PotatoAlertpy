import asyncio
import logging
from typing import List, Union, Tuple
from aiohttp.client_exceptions import ClientConnectionError, ServerTimeoutError
from utils.api import ApiWrapper, ClanWrapper, WoWsNumbersWrapper
from utils.api_errors import InvalidApplicationIdError
from utils.stat_colors import color_avg_dmg, color_battles, color_winrate, color_personal_rating, color_avg_dmg_ship
from utils.ship_utils import shorten_name, get_nation_sort, get_class_sort
from utils.dcs import Player, Team
from assets.colors import DGrey
from PyQt5.QtCore import pyqtSignal, QObject


class Signals(QObject):
    status = pyqtSignal(int, str)
    players = pyqtSignal()
    averages = pyqtSignal()
    servers = pyqtSignal()
    clans = pyqtSignal()


class CustomApi:
    def __init__(self, config, pa):
        self.config = config
        self.pa = pa

    async def check_api_key(self):
        try:
            self.pa.signals.status.emit(1, 'Ready')
            await self.pa.api.get_account_info(0)
            return False
        except InvalidApplicationIdError:
            self.pa.signals.status.emit(3, 'Invalid API')
            logging.error('The API key you provided is invalid, please go to the settings and check it!')
            return True
        except ClientConnectionError:
            logging.exception('Check your internet connection!')
            self.pa.signals.status.emit(3, 'Connection')

    async def get_players(self, arena_info: dict) -> Tuple[List[Player], List[Player], Tuple[Team, Team]]:
        player_data = arena_info['vehicles']
        match_group = arena_info['matchGroup']
        # Get stats from wows-numbers and transform colors
        w = WoWsNumbersWrapper()
        expected = await w.get_expected()
        color_limits = await w.get_color_limits()
        color_limits = color_limits['average_damage_dealt']['eu']

        team2_api, team2_region, team2_account_id = None, None, None

        if match_group == 'clan':
            try:
                # Find out which region the 2nd clan is from
                self.pa.signals.status.emit(2, f'Getting regions')
                team2_names = [p['name'] for p in player_data if p['relation'] == 2]
                for region in ['eu', 'ru', 'na', 'asia']:
                    tasks = []
                    team2_api = ApiWrapper(self.config['DEFAULT']['api_key'], region)
                    for name in team2_names:
                        tasks.append(asyncio.ensure_future(team2_api.search_account(name)))
                    responses = await asyncio.gather(*tasks)
                    if [len(res['data']) for res in responses].count(1) == len(responses):  # All players found?
                        team2_account_id = responses[0]['data'][0]['account_id']
                        team2_region = region
                        break
                    else:
                        await team2_api.session.close()
                        team2_api = None

                if not team2_region:
                    pass  # TODO what to if they cant be found on any server?

                # Determine both clans rating
                self.pa.signals.status.emit(2, 'Getting clan ratings')
                # try to get clanIDs from players and use them to find clan rating
                cw = ClanWrapper()

                a1 = await self.pa.api.search_account([p['name'] for p in player_data if p['relation'] == 0][0])
                a1_id = a1['data'][0]['account_id']
                clan = await self.pa.api.get_player_clan(a1_id)
                clan_data = clan['data'][str(a1_id)]
                c1_id = clan_data['clan']['clan_id']
                c1_tag = clan_data['clan']['tag']
                c1_name = clan_data['clan']['name']
                c1_color = await cw.get_rating(c1_id)
                c1 = (c1_name, c1_tag, c1_color)

                clan = await team2_api.get_player_clan(team2_account_id)
                clan_data = clan['data'][str(team2_account_id)]
                c2_id = clan_data['clan']['clan_id']
                c2_tag = clan_data['clan']['tag']
                c2_name = clan_data['clan']['name']
                c2_color = await cw.get_rating(c2_id)
                c2 = (c2_name, c2_tag, c2_color)
            except (KeyError, IndexError, TypeError, ServerTimeoutError, TimeoutError) as e:
                logging.exception(e)
                c1 = ('', '', DGrey)
                c2 = ('', '', DGrey)
                team2_api = None

            self.pa.servers = (self.config['DEFAULT']['region'], team2_region)
            self.pa.signals.servers.emit()
            self.pa.clans = (c1, c2)
            self.pa.signals.clans.emit()
        else:
            self.pa.servers = (None, None)
            self.pa.signals.servers.emit()
            self.pa.clans = (None, None)
            self.pa.signals.clans.emit()

        # SYNC
        players = []
        total = len(player_data)
        for p in player_data:
            self.pa.signals.status.emit(2, f'Getting stats ({round(len(players) / total * 100, 1)}%)')
            api = self.pa.api if not (team2_api and p['relation'] == 2) else team2_api
            player = await self.get_player(api, p, match_group, expected, color_limits)
            if player:
                player.region = self.config['DEFAULT']['region'] if not (team2_api and p['relation'] == 2) \
                    else team2_region
                players.append(player)

        if team2_api:
            await team2_api.session.close()

        t1_avg, t2_avg = self.get_averages_and_colors(players)
        team1 = sorted([p for p in players if p.team == 0 or p.team == 1],
                       key=lambda x: (x.class_ship, x.tier_ship, x.nation_ship), reverse=True)
        team2 = sorted([p for p in players if p.team == 2],
                       key=lambda x: (x.class_ship, x.tier_ship, x.nation_ship), reverse=True)
        return team1, team2, (t1_avg, t2_avg)

    async def get_player(self, api, p, match_group: str, expected, color_limits) -> Union[Player, None]:
        tasks = []
        p_name = p['name']
        team = p['relation']
        ship_name = 'Error'
        clan_color, clan_tag = None, ''
        background = None
        battles, winrate, avg_dmg, winrate_ship, battles_ship, avg_dmg_ship = [0] * 6
        class_sort, nation_sort, tier_sort = [0] * 3

        # COOP BOTS
        if match_group == 'cooperative' and (team == 2 or (p_name.startswith(':') and p_name.endswith(':'))):
            ship_info = await self.pa.api.get_ship_infos(p['shipId'])
            ship = ship_info['data'][str(p['shipId'])]
            ship_name = shorten_name(ship['name'])
            class_sort = get_class_sort(ship['type'])  # these three are for sorting them in the board
            nation_sort = get_nation_sort(ship['nation'])
            tier_sort = ship['tier']
            return Player(0, True, team, [p_name, ship_name], [None, None], class_sort, tier_sort, nation_sort,
                          clan_tag)

        if (match_group == 'pve' or match_group == 'pve_premade') and team == 2:  # SCENARIO
            return None

        try:  # try to get account id by searching by name, enter empty player if we get a KeyError
            account_search = await api.search_account(p['name'])
            account_id = account_search['data'][0]['account_id']
        except (KeyError, IndexError):
            return Player(0, True, team, [p_name, ship_name], [None, None], class_sort, tier_sort, nation_sort,
                          clan_tag)

        tasks.append(asyncio.ensure_future(api.get_account_info(account_id)))
        tasks.append(asyncio.ensure_future(self.pa.api.get_ship_infos(p['shipId'])))
        tasks.append(asyncio.ensure_future(api.get_ship_stats(account_id)))
        if not match_group == 'clan':  # Don't add clan tags in clan wars
            tasks.append(asyncio.ensure_future(api.get_player_clan(account_id)))
        responses = await asyncio.gather(*tasks)
        account_info = responses[0]
        ship_info = responses[1]
        ship_stats = responses[2]
        clan = responses[3] if not match_group == 'clan' else None

        pr = self.get_overall_personal_rating(account_id, ship_stats, expected)

        try:  # get general account info and overall stats
            account_info = account_info['data'][str(account_id)]
            hidden_profile = account_info['hidden_profile']
            if not hidden_profile:
                stats = account_info['statistics']['pvp']
                if stats and 'battles' in stats:
                    battles = stats['battles']
                    if battles and stats['wins'] and stats['damage_dealt']:
                        # at least one match, otherwise we divide by 0
                        winrate = round(stats['wins'] / battles * 100, 1)
                        avg_dmg = int(round(stats['damage_dealt'] / battles, -2))
        except KeyError:
            hidden_profile = True

        if not match_group == 'clan':  # Don't add clan tags in clan wars
            try:  # get clan info and append clan tag to player name
                clan_data = clan['data'][str(account_id)]
                if clan_data and clan_data['clan']:
                    clan_tag = clan_data['clan']['tag']
                    # p_name = f"[{clan_tag}]{p['name']}"
                    clan_id = clan_data['clan']['clan_id']
                    cw = ClanWrapper()
                    clan_color = await cw.get_rating(clan_id)
            except KeyError:
                pass

        try:
            ship = ship_info['data'][str(p['shipId'])]

            if ship:
                ship_name = shorten_name(ship['name'])
                class_sort = get_class_sort(ship['type'])  # these three are for sorting them in the board
                nation_sort = get_nation_sort(ship['nation'])
                tier_sort = ship['tier']

                if not hidden_profile:
                    player_data = ship_stats['data'][str(account_id)]
                    if player_data:
                        current_ship_stats = [ss for ss in player_data if ss['ship_id'] == p['shipId']]
                        if current_ship_stats:
                            current_ship_stats = current_ship_stats[0]['pvp']
                            if 'battles' in current_ship_stats:
                                battles_ship = current_ship_stats['battles']
                                if battles_ship and 'damage_dealt' in current_ship_stats:
                                    avg_dmg_ship = int(round(current_ship_stats['damage_dealt'] / battles_ship, -2))
                                if battles_ship and 'wins' in current_ship_stats:  # check that at least one match
                                    winrate_ship = round(current_ship_stats['wins'] / battles_ship * 100, 1)
        except KeyError:
            pass

        # Get personal rating for background
        if not hidden_profile:
            if pr:
                background = color_personal_rating(pr)

        # Put all stats in a dataclass
        row = [p_name, ship_name]
        colors = [None, None]
        if not hidden_profile:
            row.extend([str(battles), str(winrate), str(avg_dmg)])
            colors.extend([color_battles(battles), color_winrate(winrate), color_avg_dmg(avg_dmg)])
            if ship_name != 'Error':
                row.extend([str(battles_ship), str(winrate_ship), str(avg_dmg_ship)])
                colors.extend([None, color_winrate(winrate_ship, battles_ship),
                               color_avg_dmg_ship(avg_dmg_ship, str(p['shipId']), color_limits, battles_ship)])
        return Player(account_id, hidden_profile, team, row, colors, class_sort, tier_sort, nation_sort, clan_tag,
                      background, clan_color)

    @staticmethod
    def get_overall_personal_rating(account_id: int = 0, stats=None, expected=None):
        try:
            if not expected:
                return False
            total_pr = []
            total_battles = 0
            if stats:
                ship_stats = stats['data'][str(account_id)]
                if ship_stats:
                    for ship in ship_stats:
                        ship_id = str(ship['ship_id'])
                        battles = ship['pvp']['battles']
                        if ship_id in expected['data']:
                            s = expected['data'][ship_id]
                            if not s:
                                continue
                            expected_dmg = s['average_damage_dealt'] * battles
                            expected_wins = s['win_rate'] * battles
                            expected_frags = s['average_frags'] * battles
                            if not expected_frags or not expected_dmg or not expected_wins:
                                continue
                        else:
                            continue
                        r_dmg = ship['pvp']['damage_dealt'] / expected_dmg
                        r_wins = ship['pvp']['wins'] * 100 / expected_wins
                        r_frags = ship['pvp']['frags'] / expected_frags
                        n_dmg = max(0, (r_dmg - 0.4) / (1 - 0.4))
                        n_frags = max(0, (r_frags - 0.1) / (1 - 0.1))
                        n_wins = max(0, (r_wins - 0.7) / (1 - 0.7))
                        pr = 700 * n_dmg + 300 * n_frags + 150 * n_wins
                        total_pr.append(pr * ship['pvp']['battles'])
                        total_battles += ship['pvp']['battles']
            return sum(total_pr) / total_battles
        except (KeyError, IndexError, ZeroDivisionError):
            return False

    @staticmethod
    def get_averages_and_colors(players: List[Player]):
        t1, t2 = Team(), Team()

        for p in players:
            if not p.hidden_profile:
                team = t1 if p.team == 1 or p.team == 0 else t2
                team.matches += int(p.row[2])
                team.winrate += float(p.row[3]) * int(p.row[2])  # multiply with # matches
                team.avg_dmg += int(p.row[4]) * int(p.row[2])

        for team in [t1, t2]:
            if team.matches:
                team.winrate_c = color_winrate(team.winrate / team.matches)
                team.avg_dmg_c = color_avg_dmg(team.avg_dmg / team.matches)
                team.avg_dmg = int(round(team.avg_dmg / team.matches, -2))
                team.winrate = round(team.winrate / team.matches, 1)

        return t1, t2
