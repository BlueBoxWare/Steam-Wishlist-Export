A Python script to export your Steam wishlist.

> :warning: Provided as-is, use at your own risk.

Only tested on Linux.

# Usage

- Download the script `steam_wishlist.py` and run it with a recent version of Python 3.
- Supply your 17 digit [SteamID](https://help.steampowered.com/en/faqs/view/2816-BE67-5B69-0FEC) ([Tool](https://steamdb.info/calculator/)):

```shell
python3 steam_wishlist.py <steamID>
```

# Private wishlist

If your wishlist is private, you'll have to take a few extra steps:

- Log in to your Steam account with your browser.
- Copy the value of the `steamLoginSecure` cookie. This value is a long string starting with `76561198` followed by a lot of random letters and numbers.
- Supply the value of that cookie to `steam_wishlist.py` with the `-c` parameter:

```shell
python3 steam_wishlist.py -c <steamLoginSecure cookie> <steamID>
```

The `steamLoginSecure` cookie regularly expires/changes, so you'll have to repeat this process every time you run steam_wislist.py.
**Never share or publish your `steamLoginSecure` cookie!**

# Output

The wishlist is written to stdout. By default `steam_wishlist.py` will output JSON. Use the `--csv` option to have it output [CSV](https://en.wikipedia.org/wiki/Comma-separated_values)
instead. The default separator for CSV is TAB and can be changed with the `-s/--separator` option. The `-f/--fields` argument can be used to specify which fields to output. For example:

```shell
python3 steam_wishlist.py <steamID> --csv -f gameid,type,name
```

Example output:

```text
581300  Game    Black Mirror
582890  Game    Estranged: The Departure
865670  DLC     Prey - Mooncras
591380  Game    Bomb Squad Academy
593380  DLC     XCOM 2: War of the Chosen
```

# Full help (steam_wislisht.py -h)

```text
usage: steam_wishlist.py [-h] [-c <cookie>] [-q] [-j | -t] [-f FIELDS] [-s SEPARATOR] [--quote {never,minimal,always}] [--sort <field>] [--num] [--reverse]
                         [--save <file> | --load <file>] [-p {linux,win,mac}] [--free] [--no-free] [--demo] [--achievements] [--cards] [--released] [--no-released]
                         [--early] [--no-early] [--type {game,dlc,mod,demo,application,music}] [--tag TAG] [--deck <int>] [--prices <country code>] [--refresh]
                         [--discount <int>] [--price <int>]
                         [<userid>]

Export your Steam wishlist

positional arguments:
  <userid>              Steam user id, which is a 17 digit number. See https://help.steampowered.com/en/faqs/view/2816-BE67-5B69-0FEC.

options:
  -h, --help            show this help message and exit
  -c <cookie>, --cookie <cookie>
                        value of steamLoginSecure browser cookie, required for private wishlist
  -q, --quiet           don't report progress on stderr
  -j, --json            output json (default)
  -t, --csv             output CSV
  -f FIELDS, --fields FIELDS
                        comma-separated list of fields to include
  -s SEPARATOR, --separator SEPARATOR
                        field separator used for CSV output (default tab)
  --quote {never,minimal,always}
                        CSV quoting style (default: never, meaning: escape delimiters occuring in fields)
  --save <file>         save unprocessed wishlist to <file>
  --load <file>         load saved wishlist (with --save) from <file> instead of downloading

sorting (CSV):
  --sort <field>        sort by <field>
  --num, --numeric      sort numerically
  --reverse             reverse sort

filters:
  -p {linux,win,mac}, --platform {linux,win,mac}
                        supported platform (linux, win or mac). Can be repeated for multiple platforms
  --free                free games only
  --no-free             non-free games only
  --demo                games with demos only
  --achievements        games with achievements only
  --cards               games with trading cards only
  --released            released games only
  --no-released         unreleased games only
  --early               early access games only
  --no-early            no early access games
  --type {game,dlc,mod,demo,application,music}
                        type of app. Can be repeated for multiple types
  --tag TAG             list only games with this tag. Can be repeated for multiple tags. Case-insensitive, spaces and non-alphabetic characters are ignored
  --deck <int>          list only games with a Steam Deck compatibility rating of <int> or higher (must be an int between 0 and 3, inclusive)

price information:
  --prices <country code>
                        fetch current prices and discounts from the store. <country code> is the 2 letter country code for which the regional prices should be fetched.
                        When using --load, prices are loaded from file unless the file does not contain prices
  --refresh             when used with --load, fetch up to date prices from the Steam store instead of using prices from the loaded file

price filters:
  --discount <int>      list games with a discount percentage of <int> or more
  --price <int>         list games with a price of <int> or less. <int> should be an int, for example $19.99 should be specified as 1999

Available wishlist fields, see JSON ouput:
    name, capsule, review_score, review_desc, reviews_total, reviews_percent,
    release_date, release_string, platform_icons, subs, type, screenshots,
    review_css, priority, added, background, rank, tags, is_free_game,
    deck_compat, win, mac, linux, free, prerelease

Additional provided fields for CSV output:
    gameid, link, released

Additional fields when using --prices to get price information:
    initial, final, discount_percent, initial_formatted, final_formatted, currency
```
