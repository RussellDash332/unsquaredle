import os

PUZZLES = [
    '5star',
    '10x10',
    '10x10-2',
    'arbor-day-24',
    'arrrrr',
    'discord200',
    'gemstones',
    'hajj-24',
    'hannukah',
    'hanukkah23',
    'kwanzaa',
    'kwanzaa23',
    'medical',
    'nye23',
    'olympics-24',
    'otherworldly',
    'pasta',
    'poetry',
    'rare-disease',
    'reddit',
    'special',
    'spooky',
    'spooky2',
    'spooky3',
    'sub50',
    'sub500',
    'thanksgiving',
    'time',
    'uk',
    'valentine',
    'valentine24',
    'waffle-ingredients',
    'waffle',
    'waffle2',
    'xmas'
]

def make_content(puzzle):
    secrets = '''        env:
          TOKEN: ${{ secrets.TOKEN }}
          CHATS: ${{ secrets.CHATS }}'''
    content = f'''name: {puzzle} squaredle
on:
  workflow_dispatch:
jobs:
  squaredle:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Chrome setup matters
        run: |-
          apt list --installed
          sudo apt purge google-chrome-stable
          sudo apt purge chromium-browser
          sudo apt install -y chromium-browser
          pip install -r requirements.txt
      - name: It's Squardlin time!
        run: python main.py -m {puzzle}
{secrets}
'''
    with open(os.path.join('.github', 'workflows', f'{puzzle}.yml'), 'w+') as f:
        f.write(content)

# Unleash them
[*map(make_content, PUZZLES)]