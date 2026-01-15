import argparse
import logging
import os
import platform
import requests
import sys
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
try:    TOKEN, CHATS = os.environ['TOKEN'], os.environ['CHATS']
except: from env import TOKEN, CHATS

logging.basicConfig(
    level=logging.INFO, 
    format= '[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Constants
DEPTH_LIMIT = 7

def loop_resolve(f, resolution, lim, *args):
    if lim == 0:
        raise Exception('Reached the limit for number of tries')
    try:
        return f(*args)
    except Exception as e:
        print('Issue found:', e, flush=True)
        resolution()
        return loop_resolve(f, resolution, lim-1, *args)

def get_windows_browser():
    service = Service()
    options = webdriver.ChromeOptions()
    #options.add_argument('--headless') # to debug, comment this line
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    browser = webdriver.Chrome(service=service, options=options)
    return browser

def get_linux_browser():
    chrome_service = Service(ChromeDriverManager(chrome_type='chromium').install())
    chrome_options = Options()
    options = [
        "--headless",
        "--disable-gpu",
        "--window-size=1920,1200",
        "--ignore-certificate-errors",
        "--disable-extensions",
        "--no-sandbox",
        "--disable-dev-shm-usage"
    ]
    for option in options: chrome_options.add_argument(option)
    browser = webdriver.Chrome(service=chrome_service, options=chrome_options)
    browser.execute_cdp_cmd('Emulation.setTimezoneOverride', {'timezoneId': 'Singapore'})
    return browser

def solve(mode, supplier):
    # start browser
    browser = supplier()
    browser.maximize_window()
    browser.set_page_load_timeout(20)
    try:
        logging.info('Getting HTML source page...')
        browser.get('https://squaredle.app/' + (
            '' if mode == 'daily' else
            '?level=xp' if mode == 'xp' else
            f'?puzzle={mode}'
        ))
        time.sleep(5)
        try:
            logging.info('Skipping tutorial...')
            browser.find_element(By.CLASS_NAME, "skipTutorial").click()
            browser.find_element(By.ID, "confirmAccept").click()
            time.sleep(5)
        except:
            logging.info('Closing popup...')
            popups = browser.find_elements(By.CLASS_NAME, 'popup')
            for popup in popups:
                if popup.is_displayed():
                    close = popup.find_element(By.CLASS_NAME, 'closeBtn')
                    ActionChains(browser).move_to_element(close).click(close).perform()
                    time.sleep(0.5)
        for _ in range(3):
            try:
                logging.info('Checking if we can reveal first letters...')
                checklist = browser.find_element(By.ID, 'hintFirstLetters')
                ActionChains(browser).move_to_element(checklist).click(checklist).perform()
                has_hint = True; break
            except:
                logging.info('First letter hint not available...')
                has_hint = False
            time.sleep(0.5)
    except Exception as e:
        logging.info(f'{type(e).__name__}: {e}')
        browser.quit()
        return solve(mode, supplier)

    # parse source page
    t1 = time.time()
    logging.info('Source page obtained! Parsing source page now...\n')
    soup = BeautifulSoup(browser.page_source, 'html.parser')

    sq = ''.join(s.find(class_='unnecessaryWrapper').contents[0] for s in soup.find('div', class_='board').findAll('div', class_='letter'))
    lengths = [int(s.contents[0].strip('letters')) for s in soup.find('div', class_='wordLengths').findAll('h3') if s.contents[0].endswith('letters')]
    try: bonus = soup.find('div', class_='wordLengths').find('li').contents[0].split()[0]
    except: bonus = ''
    max_len = max(max(lengths), len(bonus))
    logging.info(f'Squaredle is "{sq}" and maximum length is {max_len}')

    # prep Unsquaredle
    t2 = time.time()
    long_words = set()
    n = round(len(sq)**0.5)
    if has_hint and n > 5:
        max_len = min(max_len, DEPTH_LIMIT) # bonus word VS runtime trade-off
        long_words = {*filter(lambda x: '*' in x and len(x)>max_len, (str(s.contents[0]).strip().split()[0].upper() for s in soup.findAll('li') if str(s.contents[0]).strip()))}

    g = [[] for _ in range(len(sq))]
    for i in range(n-1):
        for j in range(n): g[n*i+j].append(n*i+n+j), g[n*i+n+j].append(n*i+j), g[n*j+i].append(n*j+i+1), g[n*j+i+1].append(n*j+i)
        for j in range(n-1): g[n*i+j].append(n*i+j+n+1), g[n*i+j+n+1].append(n*i+j), g[n*i+n+j].append(n*i+j+1), g[n*i+j+1].append(n*i+n+j)

    bm0 = 0 # making mask for non-tiles
    for i in range(len(sq)):
        if sq[i] == ' ': bm0 |= 1<<i

    ans = set()
    def bt(idx, bm=bm0, w=[]):
        if (1<<idx)&bm or len(w)>max_len: return
        w.append(sq[idx]); bm |= 1<<idx
        if (ww:=''.join(w)) in ss: ans.add(ww)
        for nxt in g[idx]: bt(nxt, bm, w)
        bm ^= 1<<idx; w.pop()
    def bt2(idx, target, bm=bm0, w=[]):
        if (1<<idx)&bm or len(w)>len(target) or (w and w[-1]!=target[len(w)-1]) or target in ans: return
        w.append(sq[idx]); bm |= 1<<idx
        if (ww:=''.join(w)) == target: ans.add(ww)
        for nxt in g[idx]: bt2(nxt, target, bm, w)
        bm ^= 1<<idx; w.pop()

    for i in range(len(sq)): bt(i)
    for wh in sorted(long_words):
        ll, rr = wh.find('*'), wh.rfind('*')
        wl, wr = wh[:ll], wh[rr+1:]
        for w in ss:
            if len(w) == len(wh) and w.startswith(wl) and w.endswith(wr):
                for i in range(len(sq)):
                    bt2(i, w)
                    if w in ans: break
                if w in ans: print(wh, w)
    ans = sorted(ans); ans.extend(ans[:3]) # retry first few for a good measure
    logging.info(f'Found {len(ans)} candidate words!')

    if mode == 'lirpa-loof':
        ans = [w[::-1] for w in ans]

    # try all!
    t3 = time.time()
    popups = browser.find_elements(By.CLASS_NAME, 'popup')
    for i in ans:
        print(i, flush=True)
        for _ in range(2):
            ActionChains(browser).send_keys(i).perform()
            ActionChains(browser).send_keys(Keys.ENTER).perform()
            for popup in popups:
                if popup.is_displayed():
                    for _ in range(3):
                        try:
                            close = popup.find_element(By.CLASS_NAME, 'closeBtn')
                            ActionChains(browser).move_to_element(close).click(close).perform()
                        except: pass
                        time.sleep(0.5)
            try: browser.find_element(By.ID, 'explainerPermaClose').click()
            except: pass
            try: browser.find_element(By.ID, 'explainerClose').click()
            except: pass

    # share results!
    t4 = time.time()
    browser.find_element(By.XPATH, '/html/body/div[1]/header/div/div[2]/button[2]').click() # it doesn't work without xpath?
    time.sleep(1) # wait to load if you are on top of some category
    soup = BeautifulSoup(browser.page_source, 'html.parser')
    try:
        result = [*{*filter(lambda x: all('A'<=i<='Z' for i in x), (str(s.find('a').contents[0]).strip().split()[0].upper() for s in soup.find('div', class_='wordLengths').findAll('li') if s.find('a') and str(s.find('a').contents[0]).strip()))}]
        result += [*filter(lambda x: all('A'<=i<='Z' or i=='*' for i in x), (str(s.contents[0]).strip().split()[0].upper() for s in soup.find('div', class_='wordLengths').findAll('li') if str(s.contents[0]).strip()))]
        for w in sorted(result, key=lambda x: (len(x), x)): print(len(w), w)
        logging.info('Obtained finalized list of words')
    except:
        logging.info('Cannot obtain finalized list of words')
    browser.quit()
    return round(t2-t1, 5), round(t3-t2, 5), round(t4-t1, 5), '\n'.join(soup.find('pre').contents)

def send(token, chat_id, bot_message):
    resp = requests.get(f'https://api.telegram.org/bot{token}/sendMessage', params={
        'chat_id': chat_id,
        'parse_mode': 'MarkdownV2',
        'text': bot_message,
        'disable_web_page_preview': False
        })
    logging.info(resp.json().get('description') if not resp.ok else resp.ok)

def get_word_list():
    # populate word list, might take a while :)
    ss = set()
    urls = [
        'https://raw.githubusercontent.com/scrabblewords/scrabblewords/main/words/North-American/6-letter-stems.txt',
        'https://raw.githubusercontent.com/scrabblewords/scrabblewords/main/words/North-American/7-letter-stems.txt',
        'https://raw.githubusercontent.com/scrabblewords/scrabblewords/main/words/North-American/NSWL2020.txt',
        'https://raw.githubusercontent.com/scrabblewords/scrabblewords/main/words/North-American/NWL2020.txt',
        'https://github.com/dwyl/english-words/raw/master/words_alpha.txt',
        'https://github.com/dwyl/english-words/raw/master/words.txt',
        'https://github.com/tabatkins/wordle-list/raw/main/words',
        'https://github.com/powerlanguage/word-lists/raw/master/word-list-raw.txt',
        'https://github.com/sadamson/longest-word/raw/master/usa.txt',
        'https://github.com/matthewreagan/WebstersEnglishDictionary/raw/master/WebstersEnglishDictionary.txt',
        'https://foldoc.org/Dictionary',
        'https://www-cs-faculty.stanford.edu/~knuth/sgb-words.txt'
    ]
    for url in urls:
        try: ss |= {*(i for i in requests.get(url).content.decode().upper().replace('\n', ' ').split() if all('A'<=l<='Z' for l in i) and len(i)>3)}; logging.info(f'{len(ss)} {url}')
        except: logging.info(f'{len(ss)} FAIL {url}')
    # GH keeps throwing a 403 error so let's not do this
    '''
    for length in range(4, 53):
        r = requests.get(f'https://www.litscape.com/words/length/{length}_letters/{length}_letter_words.html')
        if r.ok: ss |= {w for w in r.content.decode().upper().replace('\n', ' ').replace('<', ' ').replace('>', ' ').split() if len(w)==length and all('A'<=l<='Z' for l in w)}; logging.info(f'{len(ss)} {length}')
        else: logging.info(f'{len(ss)} FAIL ({r.status_code}) {length}')
    '''
    ss |= set(w.strip() for w in open('data/litscape.txt').readlines())
    ss |= set(w.strip() for w in open('data/special.txt').readlines())
    logging.info(f'Database of {len(ss)} words loaded!')
    return ss

if __name__ == '__main__':
    ss = get_word_list()
    curr_os = (pf:=platform.platform())[:pf.find('-')]
    supplier = {'Windows': get_windows_browser, 'Linux': get_linux_browser}.get(curr_os)
    assert supplier, f'Unsquaredle not supported for {curr_os} yet :('

    parser = argparse.ArgumentParser(prog='unsquaredle', description='Solve Squaredle in no time')
    parser.add_argument('-m', '--mode', default='daily', help='Mode of puzzle')
    parser.add_argument('-c', '--cron', default=0, help='Delay solving until new day (0 or 1)')
    args = parser.parse_args()

    if int(args.cron):
        while (t:=int(time.time()%86400))//3600 < 10: # not 10AM GMT yet
            time.sleep(10)
            logging.info(f'Waiting... Current time: {str(t//3600).zfill(2)}:{str(t//60%60).zfill(2)}:{str(t%60).zfill(2)} GMT')

    t_parse, t_algo, t_selenium, verdict = loop_resolve(solve, lambda: None, 3, args.mode.strip(), supplier)
    print(f'\nTime to parse Squaredle board: {t_parse}', flush=True)
    print(f'Time to run backtracking: {t_algo}', flush=True)
    print(f'Time to apply candidate words on web: {t_selenium}\n', flush=True)
    print(verdict)

    # Telebot integration
    for chat_id in CHATS.split(','):
        send(TOKEN, chat_id, f'{verdict}\n#unsquaredle' \
             .replace('.', '\\.') \
             .replace('*', '\\*') \
             .replace('(', '\\(') \
             .replace(')', '\\)') \
             .replace('#', '\\#') \
             .replace('+', '\\+') \
             .replace('-', '\\-') \
             .replace('=', '\\=')
        )
