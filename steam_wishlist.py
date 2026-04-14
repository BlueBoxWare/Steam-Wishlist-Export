#!/usr/bin/env python3

from __future__ import annotations

import argparse
import atexit
import csv
import gzip
import json
import locale
import re
import shutil
import signal
import string
import sys
import textwrap
import time
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

BACKOFF = [5, 20, 60, 2 * 60, 10 * 60, 30 * 60]

LANGUAGES = {
    "ar": "arabic",
    "bg": "bulgarian",
    "zh_CN": "schinese",
    "zh_TW": "tchinese",
    "cs": "czech",
    "da": "danish",
    "nl": "dutch",
    "en": "english",
    "fi": "finnish",
    "fr": "french",
    "de": "german",
    "el": "greek",
    "hu": "hungarian",
    "id": "indonesian",
    "it": "italian",
    "ja": "japanese",
    "ko": "korean",
    "no": "norwegian",
    "pl": "polish",
    "pt": "portuguese",
    "pt_BR": "brazilian",
    "ro": "romanian",
    "ru": "russian",
    "es": "spanish",
    "es_419": "latam",
    "sv": "swedish",
    "th": "thai",
    "tr": "turkish",
    "uk": "ukrainian",
    "vi": "vietnamese",
}

RENAME = {"steam_release_date": "release_date", "is_free": "free"}

default_country = "<unknown>"
try:
    default_country = locale.getdefaultlocale()[0].split("_")[1].lower()  # pyright: ignore [reportOptionalMemberAccess]
except:
    pass

default_lang = "english"
try:
    l = locale.getdefaultlocale()[0]
    if l in LANGUAGES:
        default_lang = LANGUAGES[l]
    else:
        default_lang = LANGUAGES[l.split("_")[0]]  # pyright: ignore [reportOptionalMemberAccess]
except:
    pass

cache: dict[str, dict] = {}

##
## Command line arguments
##

parser = argparse.ArgumentParser(
    prog="steam_wishlist.py",
    description="Export your Steam wishlist",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
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
""",
)
group_input = parser.add_argument_group("Input").add_mutually_exclusive_group(
    required=True
)
group_input.add_argument(
    "-f",
    "--file",
    help="Extract wishlist from <file>, which contains the saved HTML of a wishlist",
    type=str,
    metavar="<file>",
)
group_input.add_argument(
    "-a",
    "--api",
    help="Use the Steam Web API to get the wishlist for the user with <steamid>. Use --key <key> to specify your Steam Web API key. ",
    type=int,
    metavar="<steamid>",
)
group_input.add_argument(
    "--list",
    help="Read app ids from <file>, containing one id per line",
    type=str,
    metavar="<file>",
)

parser.add_argument(
    "-c",
    "--country",
    help="Country code for fetching store data (default: %(default)s)",
    default=default_country,
    type=str,
)
parser.add_argument(
    "-l",
    "--lang",
    help=f"Language for fetching store data (default: %(default)s) (supported values: {', '.join(LANGUAGES.values())})",
    default=default_lang,
    type=str,
)
parser.add_argument(
    "-e",
    "--extract-only",
    help="Extract the game ids from the wishlist. Do not download any additional information. Filtering is not possible."
    " Only the fields id, priority and date_added are available.",
    action="store_true",
)
parser.add_argument(
    "--key",
    help="Your Steam Web API key. Only required when using --api to get the wishlist using the Steam Web Api.",
    type=str,
)
parser.add_argument(
    "-q",
    "--quiet",
    help="Don't report progress on stderr",
    action="store_true",
)
parser.add_argument(
    "--sleep",
    help="Number of seconds to sleep between network requests (default: %(default)s, minimum: 2)",
    type=int,
    default=3,
)
parser.add_argument("--debug", help="Output debugging information", action="store_true")

group_output = parser.add_argument_group("Output")
group_output_format = group_output.add_mutually_exclusive_group()
group_output_format.add_argument(
    "-j",
    "--json",
    help="Output json (default)",
    action="store_true",
)
group_output_format.add_argument("-C", "--csv", help="Output CSV", action="store_true")
group_output_format.add_argument(
    "-t", "--table", help="Output a table", action="store_true"
)

group_output.add_argument(
    "-s", "--save", help="Save results to <file> instead of stdout", metavar="<file>"
)
group_output.add_argument(
    "--overwrite",
    help="Overwrite the <file> specified with --save if it already exists",
    action="store_true",
)
group_output.add_argument(
    "-O", "--one-line", help="One line per item (table)", action="store_true"
)
group_output.add_argument(
    "-L", "--line-length", help="Maximum line length (table)", type=int
)
group_output.add_argument(
    "-F",
    "--fields",
    help="Comma-separated list of fields to include. Can be repeated",
    action="append",
)
group_output.add_argument(
    "-S",
    "--separator",
    help="Field separator used for CSV output (default: tab)",
    default="\t",
)
group_output.add_argument(
    "--quote",
    help="CSV quoting style (default: never, meaning: escape delimiters occuring in fields)",
    choices=["never", "minimal", "always"],
    default="never",
)
group_output.add_argument(
    "--header", help="Include header (CSV and table)", action="store_true"
)

group_sort = parser.add_argument_group("Sorting (Table and CSV)")
group_sort.add_argument("--sort", help="Sort by <field>", metavar="<field>")
group_sort.add_argument(
    "--num",
    help="Sort numerically",
    action="store_true",
)
group_sort.add_argument("--reverse", help="Reverse sort", action="store_true")

group_filters = parser.add_argument_group("Filters")
group_filters.add_argument(
    "-p",
    "--platform",
    help="Comma-separated list of platforms. Only include games for these platforms (default: all). Can be repeated. Possible values: linux, win, mac.",
    action="append",
)
group_filters.add_argument("--free", help="Free games only", action="store_true")
group_filters.add_argument("--no-free", help="Non-free games only", action="store_true")
group_filters.add_argument("--demo", help="Games with demos only", action="store_true")
group_filters.add_argument(
    "--achievements",
    help="Games with achievements only",
    action="store_true",
)
group_filters.add_argument(
    "--cards",
    help="Games with trading cards only",
    action="store_true",
)
group_filters.add_argument(
    "--gfn",
    help="Games on GeForce NOW which are playable through Steam",
    action="store_true",
)
group_filters.add_argument(
    "--released",
    help="Released games only",
    action="store_true",
)
group_filters.add_argument(
    "--no-released",
    help="Unreleased games only",
    action="store_true",
)
group_filters.add_argument(
    "--early",
    help="Early access games only",
    action="store_true",
)
group_filters.add_argument(
    "--no-early",
    help="No early access games",
    action="store_true",
)
group_filters.add_argument(
    "--type",
    help="Comma-separated list of types. Can be repeated. Possible values: game, dlc, mod, demo, application, music. Default: all.",
    action="append",
)
group_filters.add_argument(
    "-T",
    "--category",
    help=(
        "Comma-separated list of categories (names or ids)."
        " List only games with any of these categories. Can be repeated for multiple categories. Case-insensitive, spaces and non-alphanumeric characters are ignored."
        " If the category is an integer, it is assumed to be an id instead of a name. Names and ids can be mixed."
    ),
    action="append",
)
group_filters.add_argument(
    "-G",
    "--genre",
    help=(
        "Comma-separated list of genres (names or ids)."
        " List only games with any of these genres. Can be repeated for multiple genres. Case-insensitive, spaces and non-alphanumeric characters are ignored."
        " If the genre is an integer, it is assumed to be an id instead of a name. Names and ids can be mixed."
    ),
    action="append",
)

group_price_filter = parser.add_argument_group("Price filters")
group_price_filter.add_argument(
    "--discount",
    help="Games with a discount percentage of <int> or more",
    metavar="<int>",
    type=int,
)
group_price_filter.add_argument(
    "--price",
    help="Games with a price of <int> or less. <int> should be an integer, for example $19.99 should be specified as 199:with9",
    metavar="<int>",
    type=int,
)
group_price_filter.add_argument(
    "--metacritic",
    help="Games with a metacritic score of <int> or higher",
    metavar="<int>",
    type=int,
)

group_cache = parser.add_argument_group("Caching")
group_cache.add_argument(
    "-P",
    "--refresh-prices",
    help="Fetch latest prices, instead of using the cache",
    action="store_true",
)
group_cache.add_argument(
    "-W",
    "--refresh-wishlist",
    help="Fetch up-to-date wishlist, instead of using the cache (API only)",
    action="store_true",
)
group_cache.add_argument(
    "--cache-file",
    help="Path of the file to use for caching (default: '%(default)s' in the current directory)",
    default=".steam_wishlist.cache",
)
group_cache.add_argument(
    "--refresh",
    help="Do not use cached data",
    action="store_true",
)
group_cache.add_argument(
    "--no-cache", help="Do not create (or update) the cache file", action="store_true"
)
group_cache.add_argument(
    "--cache-info-hours",
    help="Duration after which cached game information is considered outdated (in hours, default: %(default)s)",
    default=3 * 24,
    type=int,
)
group_cache.add_argument(
    "--cache-price-hours",
    help="Duration after which cached price information is considered outdated (in hours, default: %(default)s)",
    default=24,
    type=int,
)
group_cache.add_argument(
    "--cache-wishlist-hours",
    help="Duration after which the cached wishlist is considered outdated (in hours, API only, default: %(default)s)",
    default=1,
    type=int,
)
group_cache.add_argument(
    "--keep-cache",
    help="Do not evict outdated data from cache",
    action="store_true",
)

group_errors = parser.add_argument_group("Errors")
group_errors.add_argument(
    "--no-errors",
    help="Do not include items for which no information could be downloaded for whatever reason",
    action="store_true",
)
group_errors.add_argument(
    "--retry-errors",
    help="Retry downloading app information for items which failed before",
    action="store_true",
)
group_errors.add_argument(
    "--list-errors",
    help="List the ids of all items for which information could not be downloaded",
    action="store_true",
)

args = parser.parse_args()

if args.sleep < 2:
    print(
        "Minimum value for --sleep is 2 seconds, to prevent your IP from being (temporarily) blocked.",
        file=sys.stderr,
    )
    sys.exit(1)

LOCK_FILE: Path = Path(args.cache_file + ".lock")


##
## Helpers
##
def perror(msg: str) -> None:
    print(msg, file=sys.stderr, end="", flush=True)


def progress(msg: str) -> None:
    if not args.quiet and not args.extract_only:
        perror(msg)


def request(url: str) -> urllib.request.Request:
    req = urllib.request.Request(url)
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    )
    return req


def clean_str(s: str) -> str:
    return "".join([c.lower() for c in s if c.isalnum()])


def flatten_args(args: list[str]) -> list[str]:
    l = []
    for a in args:
        l.extend(a.split(","))
    return l


def wants(wanted: list[str], values_key: str, data: dict[str, Any]) -> bool:
    wanted = flatten_args(wanted)
    values = data.get(values_key, [])
    values = [clean_str(w["description"]) for w in values] + [
        str(w["id"]) for w in values
    ]
    return any(clean_str(w) in values for w in wanted)


def sleep(secs: int = args.sleep) -> None:
    if args.quiet:
        time.sleep(secs)
        return
    for _ in range(secs):
        time.sleep(1)
        progress(".")


def integer(value: int | None, name: str, maximum: int | None = None) -> int:
    if value is None:
        return 0
    if maximum and value > maximum:
        perror(f"--{name} must be between 0 and {max}, inclusive.\n")
        sys.exit(1)
    return value


def cleanup_cache(d: dict, duration: int) -> dict:
    if args.keep_cache:
        return d
    curr_time = int(datetime.now(timezone.utc).timestamp())
    for key in list(d):
        if key == "_time_" and d[key] < curr_time - duration * 60 * 60:
            return {}
        if isinstance(d[key], dict):
            d[key] = cleanup_cache(d[key], duration)
            if not bool(d[key]):
                del d[key]
    return d


def get_cached(key: list[str], default: Any = None) -> Any:  # noqa: ANN401
    value: dict = cache
    for k in key:
        if k in value:
            value = value[k]
        else:
            return default
    return value


def app_key(appid: int) -> list[str]:
    return ["apps", args.country, args.lang, str(appid)]


def price_key(appid: int) -> list[str]:
    return ["prices", args.country, args.lang, str(appid)]


def list_key(userid: int) -> list[str]:
    return ["wishlist", str(userid)]


def is_cached(key: list[str], duration: int) -> bool:
    curr_time = int(datetime.now(timezone.utc).timestamp())
    value: dict = cache
    for k in key:
        value = value.get(k, {})
    return not args.refresh and value.get("_time_", 0) > curr_time - duration * 60 * 60


def do_cache(key: list[str], value: dict) -> None:
    value["_time_"] = int(datetime.now(timezone.utc).timestamp())
    c: dict = cache
    for k in key[:-1]:
        c = c.setdefault(k, {})
    c[key[-1]] = value


def extract_wishlist(src: str) -> dict[int, tuple[int, int]]:
    wishlist = {}
    pattern = re.compile(
        r"renderContext\s*=\s*JSON.parse\(\"(.*?)\"\);\s*</script>",
    )
    try:
        r = pattern.search(src).group(1).encode().decode("unicode_escape")  # pyright: ignore [reportOptionalMemberAccess]
        js = json.loads(json.loads(r)["queryData"])
        for query in js["queries"]:
            if "WishlistSortedFiltered" in query["queryKey"]:
                for item in query["state"]["data"]["items"]:
                    wishlist[item["appid"]] = (item["date_added"], item["priority"])
    except Exception:
        if args.debug:
            raise
        perror(f"Could not find wishlist data in {args.file}.\n")
        sys.exit(1)
    return wishlist


def fetch_app_info(appid: int) -> dict:
    retry = 0
    response = None
    url = f"https://store.steampowered.com/api/appdetails/?cc={args.country}&l={args.lang}&appids={appid}"
    req = request(url)
    while retry < len(BACKOFF):
        try:
            response = urllib.request.urlopen(req)
            break
        except Exception:
            progress(" Error fetching.\nRetry")
            sleep(BACKOFF[retry])
            retry = retry + 1
            if retry >= len(BACKOFF):
                perror(" Too many failures. Aborting.\n")
                save_cache()
                raise

    if not response:
        sys.exit(1)

    sleep()

    text = response.read()
    if not text:
        progress(f" Empty response for {appid}.")
        text = "{}"
    json_obj = json.loads(text)
    try:
        data = json_obj[str(appid)]["data"]
    except KeyError:
        perror(" Error fetching.\n")
        return {"_error_": True}

    progress("\n")

    return data


def save_cache() -> None:
    if args.no_cache:
        return
    if args.debug:
        progress("Saving cache.\n")
    with gzip.open(args.cache_file, "wt") as f:
        json.dump(cache, f)


def length(s: str) -> int:
    l = 0
    for c in s:
        l += 2 if unicodedata.east_asian_width(c) in "WF" else 1
    return l


def diff(s: str) -> int:
    return length(s) - len(s)


def sorter(appid: int) -> Any:  # noqa: ANN401
    value = wishlist[appid][0]
    if not args.sort or args.sort == "id":
        value = appid
    else:
        data = {
            "id": appid,
            "priority": wishlist[appid][1],
            "date_added": wishlist[appid][0],
        }
        if not args.extract_only:
            data = get_cached(app_key(appid))
        value = data.get(
            args.sort,
            0 if args.num else "",
        )
    if args.num or str(value).isdigit():
        return int(value)
    return str(value)


def on_exit() -> None:
    save_cache()
    LOCK_FILE.unlink(missing_ok=True)


def on_kill(*_) -> None:  # noqa: ANN002
    sys.exit(0)


##
## Main
##
wishlist: dict[int, tuple[int, int]] = {}

if LOCK_FILE.exists():
    name = Path(__file__).name
    perror(
        f"Cache file '{Path(args.cache_file).resolve()}' is already in use by another instance of {name}.\n"
        "Make sure no other instances are currently running.\n"
        f"If there are no other instances running, delete the file '{LOCK_FILE.absolute()}'.\n"
    )
    sys.exit(1)

try:
    open(LOCK_FILE, "w").close()
except Exception as e:
    perror(f"Could not create lock file '{LOCK_FILE}': {e}.\n")
    if args.debug:
        raise
    sys.exit(1)

atexit.register(on_exit)
signal.signal(signal.SIGINT, on_kill)
signal.signal(signal.SIGTERM, on_kill)

## Load cache
if not args.extract_only:
    try:
        progress("Loading cache.\n")
        with gzip.open(args.cache_file, "rt") as f:
            cache = json.load(f)
            cleanup_cache(cache.get("apps", {}), args.cache_info_hours)
            cleanup_cache(cache.get("prices", {}), args.cache_price_hours)
            cleanup_cache(cache.get("lists", {}), args.cache_info_hours)
            cleanup_cache(cache.get("wishlist", {}), args.cache_wishlist_hours)
    except FileNotFoundError:
        pass


outfile: TextIO = sys.stdout
if args.save:
    if args.overwrite:
        outfile = open(args.save, "w")
    elif Path(args.save).exists():
        perror(
            f"File '{args.save}' already exists. Use --overwrite to overwrite the file.\n"
        )
        sys.exit(1)
    else:
        outfile = open(args.save, "x")

## Load wishlist
if args.api:
    if not args.refresh_wishlist and is_cached(
        list_key(args.api), args.cache_wishlist_hours
    ):
        progress("Loading wishlist from cache.\n")
        wishlist = get_cached(list_key(args.api))["data"]
    else:
        if not args.key:
            perror(
                "When using --api, specify your Steam Web API key with --key <key>\n"
            )
            sys.exit(1)
        url = f"https://api.steampowered.com/IWishlistService/GetWishlist/v1/?steamid={args.api}&key={args.key}"
        progress("Fetching wishlist using API.\n")
        with urllib.request.urlopen(request(url)) as resp:
            try:
                data = json.loads(resp.read())
                for i in data["response"]["items"]:
                    wishlist[i["appid"]] = (i["date_added"], i["priority"])
            except Exception:
                if args.debug:
                    perror(f"URL: {url}\nContent: {resp.read()}\n")
                    raise
                perror("Could not download wishlist. Wrong API key? Wrong steamid?\n")
                sys.exit(1)
        do_cache(list_key(args.api), {"data": wishlist})
        save_cache()
else:
    with open(args.file or args.list) as f:
        if args.list:
            wishlist = {int(l.strip()): (0, 0) for l in f}
        elif args.file:
            wishlist = extract_wishlist(f.read())


if args.list_errors:
    for appid in wishlist:
        if "_error_" in get_cached(app_key(appid)):
            print(appid)
    sys.exit(0)

progress(f"{len(wishlist)} items in wishlist.\n")

## Fetch game information
if args.retry_errors:
    for appid in wishlist:
        data = get_cached(app_key(appid))
        if "_error_" in data:
            data["_time_"] = 0


to_fetch: list[int] = sorted(
    [app for app in wishlist if not is_cached(app_key(app), args.cache_info_hours)]
)

if args.extract_only:
    to_fetch = []
else:
    progress(
        f"{len(to_fetch)} items to download. {len(wishlist) - len(to_fetch)} items alreay in cache.\n"
    )

for i, appid in enumerate(to_fetch):
    progress(f"[{i + 1}/{len(to_fetch)}] Downloading info for appid {appid}")

    data = fetch_app_info(appid)
    data["link"] = f"https://store.steampowered.com/app/{appid}"
    data["date_added"] = wishlist[appid][0]
    data["priority"] = wishlist[appid][1]
    data["catids"] = sorted([int(c["id"]) for c in data.get("categories", [])])
    data["catnames"] = sorted([c["description"] for c in data.get("categories", [])])
    data["genreids"] = sorted([int(c["id"]) for c in data.get("genres", [])])
    data["genrenames"] = sorted([c["description"] for c in data.get("genres", [])])
    data["score"] = data.get("metacritic", {}).get("score", -1)
    data["id"] = appid
    data.pop("steam_appid", None)

    for key in ["platforms", "release_date"]:
        for k, v in data.get(key, {}).items():
            data[k] = v
        data.pop(key, None)

    if "price_overview" in data:
        do_cache(price_key(appid), data["price_overview"])
        del data["price_overview"]
    else:
        do_cache(price_key(appid), {})

    do_cache(app_key(appid), data)

if to_fetch:
    save_cache()

errors = len([i for i in wishlist if get_cached(app_key(i), {}).get("_error_", False)])
if errors > 0:
    progress(
        f"Info for {errors} items could not be downloaded, possibly because they are removed from the Steam store or not available in this region ({args.country}).\n"
    )
    progress(
        "Use --list-errors to view them. Use --no-errors to exclude them from the output. Use --retry-errors to retry downloading them.\n"
    )

if args.no_errors:
    wishlist = {
        appid: data
        for appid, data in wishlist.items()
        if "_error_" not in get_cached(app_key(appid))
    }

# Fetch price information
BATCH_SIZE = 100
ids_to_fetch: list[str] = []
for appid in wishlist:
    if args.refresh_prices or not is_cached(price_key(appid), args.cache_price_hours):
        if not get_cached(app_key(appid), {}).get("_error_", False):
            ids_to_fetch.append(str(appid))

if args.extract_only:
    ids_to_fetch = []

count = 1

for i in range(0, len(ids_to_fetch), BATCH_SIZE):
    progress(f"Fetching price information, batch {count}")
    sleep()
    progress("\n")
    count = count + 1
    batch = ids_to_fetch[i : i + BATCH_SIZE]
    url = "https://store.steampowered.com/api/appdetails/?filters=price_overview&cc={}&appids={}".format(
        args.country,
        ",".join(batch),
    )
    with urllib.request.urlopen(request(url)) as response:
        json_obj = json.loads(response.read())
        for gameid, obj in json_obj.items():
            result = {}
            if "data" in obj:
                if "price_overview" in obj["data"]:
                    result = obj["data"]["price_overview"]
            else:
                perror(f"Error fetching prices for {gameid}\n")
            do_cache(price_key(gameid), result)

if ids_to_fetch:
    save_cache()

# Insert price information
if not args.extract_only:
    for appid in wishlist:
        for k, v in {
            "currency": "",
            "initial": 0,
            "final": 0,
            "discount_percent": 0,
            "initial_formatted": "-",
            "final_formatted": "-",
        }.items():
            get_cached(app_key(appid))[k] = get_cached(price_key(appid), {}).get(k, v)

##
## Filters
##
wanted_discount = integer(args.discount, "Discount", 100)
wanted_price = integer(args.price, "Price")
metacritic = integer(args.metacritic, "metacritic", 100)

filter_lists: list[list[int]] = []
to_load = []
if args.demo:
    to_load.append("demos")
if args.cards:
    to_load.append("cards")
if args.achievements:
    to_load.append("achievements")
if args.gfn:
    to_load.append("gfn")

if args.extract_only:
    to_load = []

for tl in to_load:
    if is_cached(["lists", tl], args.cache_price_hours):
        filter_lists.append(get_cached(["lists", tl, "data"]))
    else:
        url = "https://raw.githubusercontent.com/BlueBoxWare/steamdb/main/data/" + tl
        progress(f"Fetching {tl} list")
        sleep()
        with urllib.request.urlopen(request(url)) as response:
            l = [int(s.decode("utf-8")) for s in response.read().split(b"\n") if s]
            do_cache(["lists", tl], {"data": l})
            filter_lists.append(l)
            progress(" Done.\n")

filtered: set[int] = set()
for appid in wishlist:
    if args.extract_only:
        filtered = set(wishlist.keys())
        break

    data: dict = get_cached(app_key(appid))
    add_game: bool = True

    if args.platform:
        add_game = False
        for platform in ["windows", "mac", "linux"]:
            if data.get(platform, False) and platform in flatten_args(args.platform):
                add_game = True

    if args.type:
        wanted_types = flatten_args(args.type)
        add_game = add_game and data.get("type", "").lower() in wanted_types

    if args.free and not data.get("is_free", False):
        add_game = False

    if args.no_free and data.get("is_free", False):
        add_game = False

    if args.released and data.get("coming_soon", False):
        add_game = False

    early_access = any(g["id"] == "70" for g in data.get("genres", []))

    if args.early and not early_access:
        add_game = False

    if args.no_early and early_access:
        add_game = False

    if add_game and args.category:
        add_game = wants(args.category, "categories", data)

    if add_game and args.genre:
        add_game = wants(args.genre, "genres", data)

    if add_game and args.discount:
        add_game = data.get("discount_percent", 0) >= wanted_discount

    if add_game and args.metacritic:
        add_game = data.get("metacritic", {}).get("score", 0) >= metacritic

    if add_game and args.price is not None:
        add_game = data.get("final", 0) <= wanted_price

    for filter_list in filter_lists:
        add_game = add_game and appid in filter_list

    if add_game:
        filtered.add(appid)

##
## Output
##

progress("\n")

wanted_fields: list[str] | None = (
    None if not getattr(args, "fields", None) else flatten_args(args.fields)
)


if args.csv:
    if not wanted_fields:
        wanted_fields = ["id"]

    quoting = csv.QUOTE_NONE
    if args.quote == "minimal":
        quoting = csv.QUOTE_MINIMAL
    elif args.quote == "always":
        quoting = csv.QUOTE_ALL

    writer = csv.writer(
        outfile,
        delimiter=args.separator,
        quoting=quoting,
        escapechar="\\",
    )

    if args.header:
        writer.writerow([string.capwords(f) for f in wanted_fields])

    for index, appid in enumerate(sorted(filtered, key=sorter, reverse=args.reverse)):
        data: dict = {}
        if args.extract_only:
            data = {
                "id": appid,
                "priority": wishlist[appid][1],
                "date_added": wishlist[appid][0],
            }
        else:
            data = get_cached(app_key(appid))
        data["index"] = index
        if "id" not in data:
            continue
        output_fields = []
        for field in wanted_fields:
            value = data.get(field, "?")
            if type(value) is list:
                sep = "," if args.separator != "," else ":"
                value = sep.join([str(v) for v in value])
            output_fields.append(str(value))
        if "".join(output_fields):
            writer.writerow(output_fields)

elif args.table:
    if not wanted_fields:
        if args.extract_only:
            wanted_fields = ["id"]
        else:
            wanted_fields = [
                "id",
                "name",
                "final_formatted",
                "discount_percent",
                "link",
            ]

    widths = [0 for _ in wanted_fields]
    lines: list[list[str]] = []

    for index, appid in enumerate(sorted(filtered, key=sorter, reverse=args.reverse)):
        data: dict = {}
        if args.extract_only:
            data = {
                "id": appid,
                "priority": wishlist[appid][1],
                "date_added": wishlist[appid][0],
            }
        else:
            data = get_cached(app_key(appid))
        data["index"] = index
        if "id" not in data:
            continue
        line = []
        for field in wanted_fields:
            value = data.get(field, "?")
            if type(value) is list:
                value = ", ".join([str(v) for v in value])
            line.append(str(value))
        lines.append(line)

    if args.header:
        lines.insert(0, [string.capwords(f) for f in wanted_fields])

    margin = 2
    max_width = args.line_length or shutil.get_terminal_size().columns
    min_width = max(30, int(max_width / 5))

    for line in lines:
        for i, item in enumerate(line):
            if length(item) + margin > widths[i]:
                widths[i] = length(item) + margin

    if sum(widths) > max_width:
        too_long = [w for w in widths if w >= min_width]
        not_too_long = [w for w in widths if w < min_width]
        scale = (max_width - sum(not_too_long)) / sum(too_long)
        widths = [int(w * scale) if w >= min_width else w for w in widths]

    if args.one_line:
        for line in lines:
            for i, cell in enumerate(line):
                try:
                    cell = textwrap.shorten(cell, widths[i] - margin, placeholder="..")
                except ValueError:
                    perror("\n\nError: Can't fit all fields properly on one line.")
                    sys.exit(1)
                print(
                    f"{cell:<{widths[i] - diff(cell)}}",
                    file=outfile,
                    end="",
                    flush=True,
                )
            print(file=outfile)

    else:
        for line in lines:
            cells = [
                textwrap.wrap(c, widths[i] - diff(c) - margin)
                for i, c in enumerate(line)
            ]
            max_lines = max(len(w) for w in cells)

            for i in range(max_lines):
                line = ""
                for index, cell in enumerate(cells):
                    content = cell[i] if i < len(cell) else ""
                    line += f"{content:<{widths[index] - diff(content)}}"
                print(line, file=outfile)


else:
    output = {}

    for appid in filtered:
        data: dict = {}
        if args.extract_only:
            data = {
                "id": appid,
                "priority": wishlist[appid][1],
                "date_added": wishlist[appid][0],
            }
        else:
            data = get_cached(app_key(appid))
        output_fields = {}
        for field_name, field_value in data.items():
            if not wanted_fields or field_name in wanted_fields:
                output_fields[field_name] = field_value
        if wanted_fields and "link" in wanted_fields:
            output_fields["link"] = f"https://store.steampowered.com/app/{appid}"
        output[appid] = output_fields

    print(json.dumps(output, indent=4, ensure_ascii=False), file=outfile)
