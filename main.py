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

__VERSION__ = '116.0.5845'

def get_mode():
    if len(sys.argv) == 1:  mode = 'xp'
    else:                   mode = sys.argv[1].strip()
    return mode

def loop_resolve(f, resolution, lim, *args):
    if lim == 0:
        raise Exception('Reached the limit for number of tries')
    try:
        return f(*args)
    except Exception as e:
        print('Issue found:', e)
        resolution()
        return loop_resolve(f, resolution, lim-1, *args)

def get_windows_browser():
    service = Service()
    options = webdriver.ChromeOptions()
    options.add_argument('--headless') # to debug, comment this line
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    browser = webdriver.Chrome(service=service, options=options)
    return browser

def get_linux_browser():
    version = __VERSION__
    chrome_service = Service(ChromeDriverManager(chrome_type='chromium', driver_version=version).install())
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
            '' if mode == 'default' else
            '?level=xp' if mode == 'xp' else
            f'?puzzle={mode}'
        ))
        time.sleep(2)
        logging.info('Skipping tutorial...')
        browser.find_element(By.CLASS_NAME, "skipTutorial").click()
        browser.find_element(By.ID, "confirmAccept").click()
        time.sleep(2)
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
    try: bonus = soup.find('div', class_='wordLengths').find('li').contents[0]
    except: bonus = ''
    max_len = max(max(lengths), len(bonus))
    logging.info(f'Squardle is "{sq}" and maximum length is {max_len}')

    # prep Unsquardle
    t2 = time.time()
    n = round(len(sq)**0.5)
    g = [[] for _ in range(len(sq))]
    for i in range(n-1):
        for j in range(n): g[n*i+j].append(n*i+n+j), g[n*i+n+j].append(n*i+j), g[n*j+i].append(n*j+i+1), g[n*j+i+1].append(n*j+i)
        for j in range(n-1): g[n*i+j].append(n*i+j+n+1), g[n*i+j+n+1].append(n*i+j), g[n*i+n+j].append(n*i+j+1), g[n*i+j+1].append(n*i+n+j)

    bm0 = 0 # making mask for non-tiles
    for i in range(len(sq)):
        if sq[i] == ' ': bm0 |= 1<<i
    
    ans = []
    def bt(idx, bm=bm0, w=[]):
        if (1<<idx)&bm or len(w)>max_len: return
        w.append(sq[idx]); bm |= 1<<idx
        if len(w)>3 and (ww:=''.join(w)) in ss: ans.append(ww)
        for nxt in g[idx]: bt(nxt, bm, w)
        bm ^= 1<<idx; w.pop()

    for i in range(len(sq)): bt(i)
    ans = sorted({*ans})
    logging.info(f'Found {len(ans)} candidate words!')

    # try all!
    t3 = time.time()
    popups = browser.find_elements(By.CLASS_NAME, 'popup')
    for i in ans:
        print(i)
        ActionChains(browser).send_keys(i).perform()
        ActionChains(browser).send_keys(Keys.ENTER).perform()
        for popup in popups:
            if popup.is_displayed():
                close = popup.find_element(By.CLASS_NAME, 'closeBtn')
                ActionChains(browser).move_to_element(close).click(close).perform()
                time.sleep(0.3)
        try: browser.find_element(By.ID, 'explainerPermaClose').click()
        except: pass

    # share results!
    t4 = time.time()
    browser.find_element(By.XPATH, '/html/body/header/div/div[2]/button[2]').click() # it doesn't work without xpath?
    time.sleep(1) # wait to load if you are on top of some category
    soup = BeautifulSoup(browser.page_source, 'html.parser')
    browser.quit()
    return round(t2-t1, 5), round(t3-t2, 5), round(t4-t1, 5), '\n'.join(soup.find('pre').contents)

def send(token, chat_id, bot_message):
    resp = requests.get(f'https://api.telegram.org/bot{token}/sendMessage', params={
        'chat_id': chat_id,
        'parse_mode': 'MarkdownV2',
        'text': bot_message,
        'disable_web_page_preview': True
        })
    logging.info(resp.ok)

if __name__ == '__main__':
    curr_os = (pf:=platform.platform())[:pf.find('-')]
    supplier = {'Windows': get_windows_browser, 'Linux': get_linux_browser}.get(curr_os)
    assert supplier, f'Unsquardle not supported for {curr_os} yet :('

    ss = set()
    urls = [
        'https://github.com/dwyl/english-words/raw/master/words_alpha.txt',
        'https://github.com/dwyl/english-words/raw/master/words.txt',
        'https://github.com/tabatkins/wordle-list/raw/main/words',
        'https://github.com/charlesreid1/five-letter-words/blob/master/sgb-words.txt',
        'https://github.com/powerlanguage/word-lists/blob/master/common-7-letter-words.txt',
        'https://github.com/powerlanguage/word-lists/blob/master/word-list-7-letters.txt',
        'https://github.com/powerlanguage/word-lists/raw/master/word-list-raw.txt'
    ]
    for url in urls:
        try: ss |= {*(i for i in requests.get(url).content.decode().upper().split() if i.isalpha())}
        except: pass
    logging.info(f'Database of {len(ss)} words loaded!')

    mode = get_mode()
    t_parse, t_algo, t_selenium, verdict = loop_resolve(solve, lambda: None, 3, mode, supplier)
    print()
    print(f'Time to parse Squardle board: {t_parse}')
    print(f'Time to run backtracking: {t_algo}')
    print(f'Time to apply candidate words on web: {t_selenium}')
    print()
    print(verdict)

    # Telebot integration
    for chat_id in CHATS.split(','): send(TOKEN, chat_id, f'{verdict}\n#unsquardle')