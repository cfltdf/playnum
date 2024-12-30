#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Organization  : CCR DataCenter
# @Time          : 2024/12/27 下午4:26
# @Author        : ccruser
# @File          : play.py
# @Function      : 文件说明
import dataclasses
import itertools
from queue import Queue
from threading import Thread, Lock
from typing import List, Dict

import pandas as pd
import streamlit as st


@dataclasses.dataclass
class PlayerStatus:
    name: str
    numbers: List[int]
    win: int = 0
    rank: int = 0


@dataclasses.dataclass
class GameStatus:
    id: int
    player_num: int
    number_num: int
    number_sum: int
    player_list: List[PlayerStatus]
    winner: str = None


def display(self: GameStatus):
    return f'{self.number_num}个数加起来是{self.number_sum}'


class GameThread(Thread):
    def __init__(self):
        super().__init__()
        self.lock = Lock()
        self.games: Dict[int, GameStatus] = dict()
        self.running: List[GameStatus] = list()
        self.finished: List[GameStatus] = list()
        self.queue = Queue()

    def run_create_game(self, player_name, player_num, number_num, number_sum, init_numbers):
        if not 1 < len(player_name) <= 10:
            raise Exception('玩家名称过长或者过短！')
        elif number_sum != sum(init_numbers) or number_num != len(init_numbers):
            raise Exception('数字和不对！')
        else:
            init_numbers.sort(reverse=True)
            ps = PlayerStatus(name=player_name, numbers=init_numbers)
            gs = GameStatus(id=len(self.games), player_num=player_num, number_num=number_num,
                            number_sum=number_sum, player_list=[ps])
            self.games[gs.id] = gs
            self.running.append(gs)
            return gs.id

    def run_submit_number(self, player_name, game_id, submit_numbers):
        gs = self.games[game_id]
        if not 1 < len(player_name) <= 10:
            raise Exception('玩家名称过长或者过短！')
        elif gs is None:
            raise Exception('游戏不存在！')
        elif gs.winner:
            raise Exception('游戏已结束！')
        elif gs.number_sum != sum(submit_numbers) or gs.number_num != len(submit_numbers):
            raise Exception('数字和不对！')
        else:
            submit_numbers.sort(reverse=True)
            for pps in gs.player_list:
                if pps.name == player_name:
                    ps = pps
                    ps.numbers = submit_numbers
                    break
            else:
                ps = PlayerStatus(name=player_name, numbers=submit_numbers)
                gs.player_list.append(ps)
                if len(gs.player_list) >= gs.player_num:
                    self.process(gs)
                    self.running.remove(gs)
                    self.finished.append(gs)
            return None

    def run(self):
        while True:
            ret_q, action, *params = self.queue.get()
            print(action, params)
            try:
                if action == 'create_game':
                    ret_q.put(self.run_create_game(*params))
                elif action == 'submit_number':
                    ret_q.put(self.run_submit_number(*params))
                else:
                    ret_q.put(Exception('非法命令'))
            except Exception as e:
                print(e)
                ret_q.put(e)

    def process(self, gs: GameStatus):
        for pa, pb in itertools.combinations(gs.player_list, 2):
            win_a = 0
            win_b = 0
            for num_a, num_b in zip(pa.numbers, pb.numbers):
                if num_a > num_b:
                    win_a += 1
                elif num_b > num_a:
                    win_b += 1
            if win_a > win_b:
                pa.win += 1
            elif win_b > win_a:
                pb.win += 1
        gs.player_list.sort(key=lambda x: x.win, reverse=True)
        for ps in gs.player_list:
            ps.rank = 1 + len([p for p in gs.player_list if p.win > ps.win])
        gs.winner = '、'.join(it.name for it in gs.player_list if it.rank == 1)

    def exec(self, command):
        print(command)
        ret_q = Queue()
        self.queue.put([ret_q, *command])
        return ret_q.get()

    def create_game(self, host_name, player_num, number_num, number_sum, init_numbers):
        ret_q = Queue()
        self.queue.put([ret_q, 'create_game', host_name, player_num, number_num, number_sum, init_numbers])
        return ret_q.get()

    def submit_number(self, player_name, game_id, submit_numbers):
        ret_q = Queue()
        self.queue.put([ret_q, 'submit_number', player_name, game_id, submit_numbers])
        return ret_q.get()


@st.cache_resource
def get_game():
    game_thread = GameThread()
    game_thread.start()
    return game_thread


st.set_page_config(
    page_title="数字游戏",
    page_icon=":robot:"
)

st.header('游戏规则：数字从大到小排序，依次比较')

if 'game_page' not in st.session_state:
    st.session_state.game_page = 1
if 'history_page' not in st.session_state:
    st.session_state.history_page = 1
if 'selected_game_id' not in st.session_state:
    st.session_state.selected_game_id = None
if 'player_name' not in st.session_state:
    st.session_state.player_name = None

game = get_game()
page_size = 10

st.sidebar.title('导航')
if st.session_state.player_name is None:
    player_name = st.sidebar.text_input('你是：', max_chars=10)
    if st.sidebar.button('登录', key='log-in'):
        if len(player_name) > 1:
            st.session_state.player_name = player_name
            st.rerun()
        else:
            st.sidebar.error('名字至少两个字！')
else:
    st.sidebar.write(f'你好，{st.session_state.player_name}！')
    if st.sidebar.button('登出', key='log-out'):
        st.session_state.player_name = None
        st.rerun()

    if st.sidebar.button('新游戏', key='button_new_game'):
        st.session_state.selected_game_id = None

    if len(game.running) > 0:
        st.sidebar.subheader('进行中游戏')
        game_start_index = (st.session_state.game_page - 1) * page_size
        game_end_index = min(game_start_index + page_size, len(game.running))
        show_games = game.running[game_start_index:game_end_index]

        for show_game in show_games:
            if st.sidebar.button(f'（{len(show_game.player_list)} / {show_game.player_num}）{display(show_game)}',
                                 key=f'show_game{show_game.id}'):
                st.session_state.selected_game_id = show_game.id
        pp, cp, np = st.sidebar.columns(3)
        total_game_pages = (len(game.running) + page_size - 1) // page_size  # 向上取整计算总页数
        if pp.button('上一页', key='prev_game') and st.session_state.game_page > 1:
            st.session_state.page -= 1
        cp.write(f"{st.session_state.game_page} / {total_game_pages}")
        if np.button('下一页', key='next_game') and st.session_state.game_page < total_game_pages:
            st.session_state.page += 1

    if len(game.finished) > 0:
        st.sidebar.subheader('已结束游戏')
        history_start_index = (st.session_state.history_page - 1) * page_size
        history_end_index = min(history_start_index + page_size, len(game.finished))
        show_histories = game.finished[history_start_index:history_end_index]

        for show_game in show_histories:
            if st.sidebar.button(f'{display(show_game)}（{show_game.player_num}人） {show_game.winner}',
                                 key=f'show_game{show_game.id}'):
                st.session_state.selected_game_id = show_game.id

        pp, cp, np = st.sidebar.columns(3)
        total_game_pages = (len(game.finished) + page_size - 1) // page_size  # 向上取整计算总页数
        if pp.button('上一页', key='prev_history') and st.session_state.history_page > 1:
            st.session_state.history_page -= 1
        cp.write(f"{st.session_state.history_page} / {total_game_pages}")
        if np.button('下一页', key='next_history') and st.session_state.history_page < total_game_pages:
            st.session_state.history_page += 1

    if st.session_state.selected_game_id is None:
        st.title('新游戏')
        pn, nn, ns = st.columns(3)
        new_player_num = pn.number_input('游戏人数', min_value=2, max_value=50)
        new_number_num = nn.number_input('数字数量', min_value=3, max_value=10)
        new_number_sum = ns.number_input('数字总和', min_value=10, max_value=100)
        numbers = []
        ncols = st.columns(min(new_number_num, 4))
        for i in range(new_number_num):
            ncol = ncols[i % len(ncols)]
            numbers.append(
                ncol.number_input(f'数字{i}', min_value=1, max_value=new_number_sum, key=f'number{i}',
                                  label_visibility='collapsed'))
        if st.button('提交'):
            res = game.create_game(st.session_state.player_name, new_player_num, new_number_num, new_number_sum,
                                   numbers)
            if isinstance(res, Exception):
                st.error(res)
            else:
                st.balloons()
                st.session_state.selected_game_id = res
                st.rerun()
    else:
        gs = game.games[st.session_state.selected_game_id]
        if gs.winner is None:
            st.title(f'{display(gs)}： {len(gs.player_list)} / {gs.player_num}')
            player_names = [it.name for it in gs.player_list]
            st.write('当前玩家：' + '、'.join(player_names))
            pn, nn, ns = st.columns(3)
            new_player_num = pn.number_input('游戏人数', value=gs.player_num, disabled=True)
            new_number_num = nn.number_input('数字数量', value=gs.number_num, disabled=True)
            new_number_sum = ns.number_input('数字总和', value=gs.number_sum, disabled=True)
            if st.session_state.player_name in player_names:
                ps = gs.player_list[player_names.index(st.session_state.player_name)]
            else:
                ps = None
            numbers = []
            ncols = st.columns(min(new_number_num, 4))
            for i in range(new_number_num):
                ncol = ncols[i % len(ncols)]
                numbers.append(
                    ncol.number_input(f'数字{i}', min_value=1, max_value=new_number_sum, key=f'number{i}',
                                      value=ps.numbers[i] if ps is not None else 1,
                                      label_visibility='collapsed'))
            if st.button('提交'):
                res = game.submit_number(st.session_state.player_name, gs.id, numbers)
                if isinstance(res, Exception):
                    st.error(res)
                else:
                    st.balloons()
                    st.session_state.selected_game_id = res
                    st.rerun()
        else:
            st.title(f'{display(gs)}： 胜者 {gs.winner}')
            df = pd.DataFrame(gs.player_list).rename(
                columns=dict(name='玩家名称', numbers='选择数字', win='胜场', rank='排名'))
            st.dataframe(df, use_container_width=True, hide_index=True)
