
import csv
import os
import pathlib
import sys
from argparse import ArgumentParser

import matplotlib.pyplot as plt
import pyperclip
import requests
from bs4 import BeautifulSoup


def get_comment(target_url):
    '''
    list型を返す
    要素はdict型
        message コメント str型
        timestanp 投稿された時間(秒) int型
    '''
    comment_data = []
    dict_str = ''
    next_url = ''
    session = requests.Session()
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'}

    # 動画ページにrequestsを実行，htmlソースを入手し，live_chat_replayの先頭urlを入手
    try:
        html = requests.get(target_url)
    except Exception as e:
        print(e)
        sys.exit()

    soup = BeautifulSoup(html.text, 'html.parser')

    for iframe in soup.find_all('iframe'):
        if 'live_chat_replay' in iframe['src']:
            next_url = iframe['src']

    ALLlist = []
    MatchList = []
    KawaiiList = []
    maxIDX = 0
    cnt_minute = 0

    while True:
        html = session.get(next_url, headers=headers)
        soup = BeautifulSoup(html.text, 'lxml')

        # 次に飛ぶurlのデータがある部分をfind_allで探してsplitで整形
        for scrp in soup.find_all('script'):
            if 'window["ytInitialData"]' in scrp.text:
                dict_str = scrp.text.split(' = ', 1)[1]

        # javascript表記を整形，falseとtrueの表記を直す
        dict_str = dict_str.replace('false', 'False')
        dict_str = dict_str.replace('true', 'True')

        # 辞書形式と認識するとかんたんにデータを取得できるが，末尾に邪魔なのがあるので消しておく（「空白2つ + \n + ;」を消す）
        dict_str = dict_str.rstrip('  \n;')
        # 辞書形式に変換
        try:
            dics = eval(dict_str)
        except Exception:
            with open('error_dict_str.txt', 'w') as f:
                f.write(dict_str)
            with open('error_soup.txt', 'w') as f:
                f.write(str(soup))
            print('コメントの変換に失敗しました')
            # print(dict_str)
            print(sys.exc_info()[0])
            sys.exit()

        # 'https://www.youtube.com/live_chat_replay?continuation=' + continue_url が次のlive_chat_replayのurl
        # 次のurlが取得できなければ終了
        try:
            continue_url = dics['continuationContents']['liveChatContinuation'][
                'continuations'][0]['liveChatReplayContinuationData']['continuation']
        except Exception:
            print("Exception")
            break
        next_url = 'https://www.youtube.com/live_chat_replay?continuation=' + continue_url

        # dics['continuationContents']['liveChatContinuation']['actions']がコメントデータのリスト．先頭はノイズデータなので[1:]で保存
        for samp in dics['continuationContents']['liveChatContinuation']['actions'][1:]:
            d = {}
            try:
                samp = samp['replayChatItemAction']['actions'][0]['addChatItemAction']['item']
                chat_type = list(samp.keys())[0]
                if 'liveChatTextMessageRenderer' == chat_type:
                    # 通常チャットの処理
                    if 'simpleText' in samp['liveChatTextMessageRenderer']['message']:
                        d['message'] = samp['liveChatTextMessageRenderer']['message']['simpleText']
                    else:
                        d['message'] = ''
                        for elem in samp['liveChatTextMessageRenderer']['message']['runs']:
                            if 'text' in elem:
                                d['message'] += elem['text']
                            else:
                                d['message'] += elem['emoji']['shortcuts'][0]
                    t = samp['liveChatTextMessageRenderer']['timestampText']['simpleText']
                    d['timestamp'] = convert_time(t)
                    d['id'] = samp['liveChatTextMessageRenderer']['authorExternalChannelId']
                elif 'liveChatPaidMessageRenderer' == chat_type:
                    # スパチャの処理
                    if 'simpleText' in samp['liveChatPaidMessageRenderer']['message']:
                        d['message'] = samp['liveChatPaidMessageRenderer']['message']['simpleText']
                    else:
                        d['message'] = ''
                        for elem in samp['liveChatPaidMessageRenderer']['message']['runs']:
                            if 'text' in elem:
                                d['message'] += elem['text']
                            else:
                                d['message'] += elem['emoji']['shortcuts'][0]
                    t = samp['liveChatPaidMessageRenderer']['timestampText']['simpleText']
                    d['timestamp'] = convert_time(t)
                    d['id'] = samp['liveChatPaidMessageRenderer']['authorExternalChannelId']
                elif 'liveChatPaidStickerRenderer' == chat_type:
                    # コメントなしスパチャ
                    continue
                elif 'liveChatLegacyPaidMessageRenderer' == chat_type:
                    # 新規メンバーメッセージ
                    continue
                elif 'liveChatPlaceholderItemRenderer' == chat_type:
                    continue
                else:
                    print('知らないチャットの種類' + chat_type)
                    continue
            except Exception:
                # print(Exception.args)
                continue

            ALLlist.append(int(d['timestamp']/60)*60)
            if '草' in d['message'] :
                MatchList.append(int(d['timestamp']/60)*60)
            if 'かわいい' in d['message'] :
                KawaiiList.append(int(d['timestamp']/60)*60)

            comment_data.append(d)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.hist([ALLlist,MatchList,KawaiiList], bins=50, color=['red','green','blue'], label=['All', '草','かわいい'],alpha=0.5)
    ax.set_xlabel('length [cm]')
    plt.show()

    return comment_data


def convert_time(input_t):
    if input_t[0] == '-':
        return 0
    t = list(map(int, input_t.split(':')))
    if len(t) == 2:
        t = 60 * t[0] + t[1]
    else:
        t = 60 * 60 * t[0] + 60 * t[1] + t[2]
    return t

def inverse_convert_time(t, margin):
    if t - margin > 0:
        m, s = divmod(t - margin, 60)
        h, m = divmod(m, 60)
    else:
        m, s = divmod(t, 60)
        h, m = divmod(m, 60)

    if h > 0:
        return f'{h:.0f}:{m:02.0f}:{s:02.0f}'
    else:
        return f'{m:.0f}:{s:02.0f}'


def parse():
    parser = ArgumentParser()
    parser.add_argument('url', help='youtubeのurl', type=str)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse()
    comment_data = get_comment(args.url)

