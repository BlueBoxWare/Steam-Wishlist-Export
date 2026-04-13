A Python script to export your Steam wishlist.

# Usage

Download the script `steam_wishlist.py` and run it with a recent version of Python 3,
using one of two ways:

### Using the Steam Web API (requires a [Steam Web API key](https://steamcommunity.com/dev/apikey))

```shell
python steam_wishlist.py --api <steam 64 bit user id> --key <your api key>
```

To find your Steam 64 bit user id, see [the Steam docs](https://help.steampowered.com/en/faqs/view/2816-BE67-5B69-0FEC).

### By downloading your wishlist

- Open your Steam wishlist in your browser
- Use `Save Page As` to save the page as `HTML Only`.
- Run `steam_wislist.py` and specify the saved page:

```shell
python steam_wislist.py --file <filename of saved page>
```

# Output

The wishlist is written to stdout. By default `steam_wishlist.py` will output JSON. Use `--table` to get a formatted table as output or `--csv`
to get [CSV](https://en.wikipedia.org/wiki/Comma-separated_values) instead.
The default separator for CSV is TAB and can be changed with the `-S/--separator` option.
The `-F/--fields` argument can be used to specify which fields to output. For example:

```shell
python steam_wishlist.py ... --table --fields id,type,name
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
usage: steam_wishlist.py [-h] (-f <file> | -a <steamid> | --list <file>)
                         [-c COUNTRY] [-l LANG] [-e] [--key KEY] [-q]
                         [--sleep SLEEP] [--debug] [-j | -C | -t] [-s <file>]
                         [--overwrite] [-O] [-L LINE_LENGTH] [-F FIELDS]
                         [-S SEPARATOR] [--quote {never,minimal,always}]
                         [--header] [--sort <field>] [--num] [--reverse]
                         [-p PLATFORM] [--free] [--no-free] [--demo]
                         [--achievements] [--cards] [--released]
                         [--no-released] [--early] [--no-early] [--type TYPE]
                         [-T CATEGORY] [-G GENRE] [--discount <int>]
                         [--price <int>] [--metacritic <int>] [-P] [-W]
                         [--cache-file CACHE_FILE] [--refresh] [--no-cache]
                         [--cache-info-hours CACHE_INFO_HOURS]
                         [--cache-price-hours CACHE_PRICE_HOURS]
                         [--cache-wishlist-hours CACHE_WISHLIST_HOURS]
                         [--keep-cache] [--no-errors] [--retry-errors]
                         [--list-errors]

Export your Steam wishlist

options:
  -h, --help            show this help message and exit
  -c COUNTRY, --country COUNTRY
                        Country code for fetching store data (default: us)
  -l LANG, --lang LANG  Language for fetching store data (default: english)
                        (supported values: arabic, bulgarian, schinese,
                        tchinese, czech, danish, dutch, english, finnish,
                        french, german, greek, hungarian, indonesian, italian,
                        japanese, korean, norwegian, polish, portuguese,
                        brazilian, romanian, russian, spanish, latam, swedish,
                        thai, turkish, ukrainian, vietnamese)
  -e, --extract-only    Extract the game ids from the wishlist. Do not
                        download any additional information. Filtering is not
                        possible. Only the fields id, priority and date_added
                        are available.
  --key KEY             Your Steam Web API key. Only required when using --api
                        to get the wishlist using the Steam Web Api.
  -q, --quiet           Don't report progress on stderr
  --sleep SLEEP         Number of seconds to sleep between network requests
                        (default: 3, minimum: 2)
  --debug               Output debugging information

Input:
  -f <file>, --file <file>
                        Extract wishlist from <file>, which contains the saved
                        HTML of a wishlist
  -a <steamid>, --api <steamid>
                        Use the Steam Web API to get the wishlist for the user
                        with <steamid>. Use --key <key> to specify your Steam
                        Web API key.
  --list <file>         Read app ids from <file>, containing one id per line

Output:
  -j, --json            Output json (default)
  -C, --csv             Output CSV
  -t, --table           Output a table
  -s <file>, --save <file>
                        Save results to <file> instead of stdout
  --overwrite           Overwrite the <file> specified with --save if it
                        already exists
  -O, --one-line        One line per item (table)
  -L LINE_LENGTH, --line-length LINE_LENGTH
                        Maximum line length (table)
  -F FIELDS, --fields FIELDS
                        Comma-separated list of fields to include. Can be
                        repeated
  -S SEPARATOR, --separator SEPARATOR
                        Field separator used for CSV output (default: tab)
  --quote {never,minimal,always}
                        CSV quoting style (default: never, meaning: escape
                        delimiters occuring in fields)
  --header              Include header (CSV and table)

Sorting (Table and CSV):
  --sort <field>        Sort by <field>
  --num                 Sort numerically
  --reverse             Reverse sort

Filters:
  -p PLATFORM, --platform PLATFORM
                        Comma-separated list of platforms. Only include games
                        for these platforms (default: all). Can be repeated.
                        Possible values: linux, win, mac.
  --free                Free games only
  --no-free             Non-free games only
  --demo                Games with demos only
  --achievements        Games with achievements only
  --cards               Games with trading cards only
  --released            Released games only
  --no-released         Unreleased games only
  --early               Early access games only
  --no-early            No early access games
  --type TYPE           Comma-separated list of types. Can be repeated.
                        Possible values: game, dlc, mod, demo, application,
                        music. Default: all.
  -T CATEGORY, --category CATEGORY
                        Comma-separated list of categories (names or ids).
                        List only games with any of these categories. Can be
                        repeated for multiple categories. Case-insensitive,
                        spaces and non-alphanumeric characters are ignored. If
                        the category is an integer, it is assumed to be an id
                        instead of a name. Names and ids can be mixed.
  -G GENRE, --genre GENRE
                        Comma-separated list of genres (names or ids). List
                        only games with any of these genres. Can be repeated
                        for multiple genres. Case-insensitive, spaces and non-
                        alphanumeric characters are ignored. If the genre is
                        an integer, it is assumed to be an id instead of a
                        name. Names and ids can be mixed.

Price filters:
  --discount <int>      Games with a discount percentage of <int> or more
  --price <int>         Games with a price of <int> or less. <int> should be
                        an integer, for example $19.99 should be specified as
                        199:with9
  --metacritic <int>    Games with a metacritic score of <int> or higher

Caching:
  -P, --refresh-prices  Fetch latest prices, instead of using the cache
  -W, --refresh-wishlist
                        Fetch up-to-date wishlist, instead of using the cache
                        (API only)
  --cache-file CACHE_FILE
                        Path of the file to use for caching (default:
                        '.steam_wishlist.cache' in the current directory)
  --refresh             Do not use cached data
  --no-cache            Do not create (or update) the cache file
  --cache-info-hours CACHE_INFO_HOURS
                        Duration after which cached game information is
                        considered outdated (in hours, default: 72)
  --cache-price-hours CACHE_PRICE_HOURS
                        Duration after which cached price information is
                        considered outdated (in hours, default: 24)
  --cache-wishlist-hours CACHE_WISHLIST_HOURS
                        Duration after which the cached wishlist is considered
                        outdated (in hours, API only, default: 1)
  --keep-cache          Do not evict outdated data from cache

Errors:
  --no-errors           Do not include items for which no information could be
                        downloaded for whatever reason
  --retry-errors        Retry downloading app information for items which
                        failed before
  --list-errors         List the ids of all items for which information could
                        not be downloaded

Available wishlist fields, also see JSON ouput:
    about_the_game, achievements, background, background_raw, capsule_image,
    capsule_imagev5, categories, coming_soon, currency, content_descriptors,
    detailed_description, developers, discount_percent, dlc,
    final (final price), final_formatted (final price, formatted), genres,
    header_image, id (app id), initial (original price), initial_formatted
    (original price, formatted), is_free, linux, linux_requirements, mac,
    mac_requirements, metacritic, movies, name, package_groups, packages,
    pc_requirements, price_overview, publishers, ratings, recommendations,
    required_age, reviews, screenshots, short_description, support_info,
    supported_languages, type, website, windows

Price fields:
    currency            currency of the price
    initial             inital price (without discount)
    final               final price (with discount)
    discount_percent    discount percent
    initial_formatted   initial price, formatted
    final_formatted     final price, formatted

Extra fields available for convenience:
    catids              list of ids of the categories of the game
    catnames            list of names of the categories of the game
    date                release date
    date_added          when the game was added to wishlist
    genreids            list of ids to the genres of the game
    genrenames          list of names of the genre of the game
    index               index/count of the current item (table and CSV only)
    link                link to store page of the game
    priority            priority of the game on wishlist
    score               metacritic score

With -e/--extract-only, only these fields are available:
    id                  store id of the game
    priority            priority of the game on wishlist
    date_added          when the game was added to wishlist
```

