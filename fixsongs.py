import os
import shutil
import hashlib
import argparse
import re
import glob
import json
import Levenshtein
from titlecase import titlecase
from collections import defaultdict
from pathlib import Path
from archivefile import ArchiveFile


DISCID = r"(?P<DiscID>[A-Za-z0-9]+)"
DISCIDUPPER = r"(?P<DiscID>[A-Z0-9-]+)"
TRACKNO = r"(?P<TrackNo>\d+)"
DISCID_TRACKNO = DISCID + r"-" + TRACKNO

ARTIST = r"(0\d\d?\s|1\d\s)?(?P<Artist>[^-]+)"
ARTISTNONUM = r"(0\d\d?\s|1\d\s)?(?P<Artist>[^-0-9]+)"
TITLE = r"(?P<Title>[^-]+)"

ARTISTWDASH = r"(?P<Artist>.+?)"
TITLEWDASH = r"(?P<Title>.+?)"

NUMBERS = r"\d+"
DASH = r"\s*-\s*"
OPTDASH = r"(\s+-?\s*|\s*-?\s+|-)"
DASHSTRICT = r"\s+-\s+"

# "SC8101-01 -01 - My Way.zip" ANTIPATTERN
D_N_NUM_T = re.compile(rf"^{DISCID_TRACKNO}{DASHSTRICT}\d\d{DASH}{TITLE}$")
# "SC8101-01 - 01 - Sinatra, Frank - My Way.zip"
D_N_NUM_A_T = re.compile(
    rf"^{DISCID_TRACKNO}{OPTDASH}{NUMBERS}{DASH}{ARTIST}{DASH}{TITLE}$"
)
# "SC8101-01-01 - Sinatra, Frank - My Way.zip"
D_N_N_A_T = re.compile(rf"^{DISCID_TRACKNO}-{NUMBERS}{OPTDASH}{ARTIST}{DASH}{TITLE}$")
# "SC8101-01-01-01 - Sinatra, Frank - My Way.zip"
D_N_N_N_A_T = re.compile(
    rf"^{DISCID_TRACKNO}-{NUMBERS}-{NUMBERS}{DASH}{ARTIST}{DASH}{TITLE}$"
)
# "SC8101-01 - Sinatra, Frank - My Way.zip"
D_N_A_T = re.compile(rf"^{DISCID_TRACKNO}{OPTDASH}{ARTIST}{DASH}{TITLE}$")
# "Sinatra, Frank - My Way - SC8101-01.zip"
A_T_D_N = re.compile(rf"^{ARTIST}{DASH}{TITLE}{DASH}{DISCID_TRACKNO}$")
# "sf252-02.zip" ANTIPATTERN
D_N = re.compile(rf"^{DISCID_TRACKNO}$")
# "02-Your Song.zip" ANTIPATTERN
N_T = re.compile(rf"^{NUMBERS}{DASH}{TITLE}$")
# "Sinatra, Frank - My Way.zip"
A_T = re.compile(rf"^{ARTIST}{DASH}{TITLE}$")
# CBE3-16 - 03 - Eddie Fisher - Oh! My Pa-Pa.cdg
D_N_NUM_A_T_WDASH = re.compile(
    rf"^{DISCID_TRACKNO}{DASHSTRICT}\d\d{DASHSTRICT}{ARTISTWDASH}{DASHSTRICT}{TITLEWDASH}$"
)
# Cbe2-28 - Third Eye Blind - Semi-Charmed Life
D_N_A_T_WDASH = re.compile(
    rf"^{DISCID_TRACKNO}{DASHSTRICT}{ARTISTWDASH}{DASHSTRICT}{TITLEWDASH}$"
)
# Cbe2-28-09 - Third Eye Blind - Semi-Charmed Life
D_N_N_A_T_WDASH = re.compile(
    rf"^{DISCID_TRACKNO}-{NUMBERS}{DASHSTRICT}{ARTISTWDASH}{DASHSTRICT}{TITLEWDASH}$"
)
# "15 - Super Duper - Stone, Joss"
NUM_A_T = re.compile(rf"^{NUMBERS}{DASHSTRICT}{ARTIST}{DASHSTRICT}{TITLE}$")
# System Of A Down - Prison Song - G11249
A_T_D = re.compile(rf"^{ARTISTNONUM}{DASH}{TITLE}{DASH}{DISCIDUPPER}$")
# "SPC018 - 07 - Creed  - One Last Breath"
D__N_A_T = re.compile(
    rf"{DISCID}{DASHSTRICT}\d\d{DASHSTRICT}{ARTIST}{DASHSTRICT}{TITLE}$"
)
# CBE314 - 01 - Do The Hokey Pokey.cdg ANTIPATTERN
D__NUM_T = re.compile(rf"^{DISCID}[-0-9]+{DASHSTRICT}\d\d{DASHSTRICT}{TITLE}$")

D__A_T = re.compile(rf"^{DISCID}[-0-9]+{DASHSTRICT}{ARTIST}{DASHSTRICT}{TITLE}$")

# CBE113 - 02 - Duet (Hill - Mcgraw) - It's Your Love
D_NUM_A_T = re.compile(
    rf"^{DISCID}{DASHSTRICT}{NUMBERS}{DASHSTRICT}{ARTISTWDASH}{DASHSTRICT}{TITLE}$"
)

# ASK-65A-02 - Keys, Alicia - Karma
D_N_NUM_A_T_LOOSE = re.compile(
    rf"^{DISCIDUPPER}-{TRACKNO}{DASH}{NUMBERS}{DASH}{ARTIST}{DASH}{TITLE}$"
)

# ASK-65A-02 - Keys, Alicia - Karma
D_N_A_T_LOOSE = re.compile(
    rf"^{DISCIDUPPER}-{TRACKNO}{DASH}{ARTISTNONUM}{DASH}{TITLE}$"
)


# Ordered
all_templates = [
    D_N_NUM_T,
    D_N_NUM_A_T,
    D_N_N_A_T,
    D_N_N_N_A_T,
    D_N_A_T,
    A_T_D_N,
    D_N,
    N_T,
    A_T,
    D_N_NUM_A_T_WDASH,
    D_N_A_T_WDASH,
    D_N_N_A_T_WDASH,
    NUM_A_T,
    A_T_D,
    D__N_A_T,
    D__NUM_T,
    D__A_T,
    D_NUM_A_T,
    D_N_NUM_A_T_LOOSE,
    D_N_A_T_LOOSE,
]


def get_global_varname(val):
    if val == "" or val is None:
        return val
    for global_name, global_val in globals().items():
        if val == global_val:
            return global_name
    return val


class SongEntry:
    def __init__(
        self,
        discid,
        trackno,
        artist,
        title,
        template,
        file_ext,
        current_file_name,
        new_file_name,
        current_dir,
    ):
        self.discid = discid
        self.trackno = trackno
        self.artist = artist.strip(" ") if artist else None
        self.title = title.strip(" ") if title else None
        self.template = template
        self.file_ext = file_ext
        self.current_file_name = current_file_name
        self.new_file_name = new_file_name
        self.current_dir = current_dir

    def __str__(self):
        return f" discid: {self.discid}, trackno: {self.trackno}, artist: {self.artist}, title: {self.title}, template: {get_global_varname(self.template)}, current file name: {self.current_file_name}, new file name: {self.new_file_name}, current dir: {self.current_dir}"


def normalize_artist_name(name):
    name = name.lower()
    name = clean_words(name)
    name = name.replace("-", " ")
    name = fix_last_comma_first(name)
    name = fix_artist_the(name)
    return name


def normalize_song_title(title):
    title = title.lower()
    title = clean_words(title)
    title = title.replace("-", " ")
    title = fix_song_the(title)
    return title


def fix_last_comma_first(name):
    # Split the name by comma
    parts = name.split(",")

    if len(parts) == 2:
        last_name = parts[0].strip()
        first_name_and_others = parts[1].strip()

        # Handle cases where 'and' is present
        if " and " in first_name_and_others:
            first_name, other_names = first_name_and_others.split(" and ", 1)
            first_name = first_name.strip()
            other_names = other_names.strip()
            # Construct the corrected name
            return f"{first_name} {last_name} and {other_names}".strip()
        else:
            # Handle cases without 'and'
            if first_name_and_others == "the":
                return name
            first_name = first_name_and_others
            return f"{first_name} {last_name}".strip()

    return name


def fix_artist_the(name):
    new_name = name
    new_name = new_name.removesuffix(", the")
    new_name = new_name.removesuffix(" the")
    new_name = new_name.removeprefix("the ")
    if new_name != name:
        return new_name + ", the"
    return name


def fix_song_the(name):
    if name.endswith(", the"):
        return "the " + name.removesuffix(", the")
    elif name.endswith(" the"):
        return "the " + name.removesuffix(" the")
    return name


def remove_the(name):
    if name.endswith(", the"):
        return name.removesuffix(", the")
    elif name.endswith(" the"):
        return name.removesuffix(" the")
    elif name.startswith("the "):
        return name.removeprefix("the ")
    return name


def clean_words(words):
    words = words.rstrip(",")
    words = replace_underscores_with_spaces(words)
    words = remove_duplicate_spaces(words)
    words = replace_special_chars(words)
    words = remove_apostrophes(words)
    return words


def remove_duplicate_spaces(text):
    return re.sub(" +", " ", text).strip()


def replace_special_chars(text):
    return (
        text.replace("’", "'")
        .replace("`", "'")
        .replace("&", "and")
        .replace("$", "s")
        .replace("!", "")
        .replace(".", "")
    )


def remove_apostrophes(text):
    text = f" {text} "  # Add spaces to ensure replacements only affect whole words
    text = text.replace("in' ", "ing ")
    text = text.replace("'", "")
    return text.strip()


def replace_underscores_with_spaces(text):
    return text.replace("_", " ")


WVOCAL = re.compile(
    r"(\(vocal\)|\(vocals\)|\(wvocal\)|\(wvocals\)|\(w-vocal\)|\(w-vocals\)|wvocal|wvocals|w-vocal|w-vocals)",
    re.IGNORECASE,
)


def fix_artist_wvocal(entry):
    artist_novocals = re.sub(WVOCAL, "", entry.artist).strip()
    title_novocals = re.sub(WVOCAL, "", entry.title).strip()
    if artist_novocals != entry.artist or title_novocals != entry.title:
        entry.artist = artist_novocals
        entry.title = title_novocals + " (wvocals)"
    return entry


WDUET = re.compile(r"(\(duet version\)|\(duet\)| duet )", re.IGNORECASE)


def fix_artist_duet(entry):
    artist_noduet = re.sub(WDUET, "", entry.artist).strip()
    title_noduet = re.sub(WDUET, "", entry.title).strip()
    if artist_noduet != entry.artist or title_noduet != entry.title:
        entry.artist = artist_noduet
        entry.title = title_noduet + " (duet)"
    return entry


WCHRISTMAS = re.compile(r"(\(christmas\))", re.IGNORECASE)


def fix_artist_christmas(entry):
    artist_nochristmas = re.sub(WCHRISTMAS, "", entry.artist).strip()
    title_nochristmas = re.sub(WCHRISTMAS, "", entry.title).strip()
    if artist_nochristmas != entry.artist or title_nochristmas != entry.title:
        entry.artist = artist_nochristmas
        entry.title = title_nochristmas + " (christmas)"
    return entry


def fix_songs_are_artists(song_book):
    updated_song_book = {}
    artist_keys = song_book.keys()
    for artist, entries in song_book.items():
        most_songs = 0
        songs_are_artist = True
        for entry in entries:
            norm_artist = normalize_artist_name(entry.title)
            norm_artist_the = norm_artist + ", the"
            found = ""
            if norm_artist in artist_keys:
                found = norm_artist
            if norm_artist_the in artist_keys:
                found = norm_artist_the
            else:
                songs_are_artist = False
                updated_song_book[artist] = entries
                break
            most_songs = max(
                len(song_book[artist]),
                len(song_book[found]),
            )
        if most_songs == len(song_book[artist]):
            updated_song_book[artist] = entries
        elif songs_are_artist:
            for entry in list(entries):
                song_artist = found
                entry.title = entry.artist
                entry.artist = song_artist
                if song_artist not in updated_song_book:
                    updated_song_book[song_artist] = []
                updated_song_book[song_artist].append(entry)
                print(f"should be Artist: {song_artist} Song: {artist}")
    return updated_song_book


def merge_similar_artists(song_book):
    def clean_artist(artist):
        return remove_the(artist)

    cleaned_artists = {artist: clean_artist(artist) for artist in song_book.keys()}
    artist_set = set(song_book.keys())
    updated_song_book = {}
    while artist_set:
        artist = artist_set.pop()
        same_artists = [artist]
        clean_artist_name = cleaned_artists[artist]
        # Use a list to avoid modifying the set during iteration
        to_check = list(artist_set)
        for other_artist in to_check:
            clean_other_artist_name = cleaned_artists[other_artist]
            max_length = max(len(clean_artist_name), len(clean_other_artist_name))
            min_length = min(len(clean_artist_name), len(clean_other_artist_name))
            length_diff = max_length - min_length
            distance_threshold = 0.2 * min_length
            if length_diff > distance_threshold:
                continue
            if " and " in clean_other_artist_name:
                continue
            titles_artist = {entry.title for entry in song_book[artist]}
            min_songs = min(len(song_book[artist]), len(song_book[other_artist]))
            titles_other_artist = {entry.title for entry in song_book[other_artist]}
            songs_in_common = len(titles_artist.intersection(titles_other_artist))
            if songs_in_common / min_songs < 0.3:
                continue
            words1 = clean_other_artist_name.split()
            words2 = clean_artist_name.split()
            reversed_words2 = words2[::-1]
            is_flipped = words1 == reversed_words2
            if is_flipped:
                same_artists.append(other_artist)
                artist_set.remove(other_artist)
            elif (
                Levenshtein.distance(clean_artist_name, clean_other_artist_name)
                <= distance_threshold
            ):
                same_artists.append(other_artist)
                artist_set.remove(other_artist)
        combined_songs = set()
        max_artist = max(same_artists, key=lambda a: len(song_book[a]), default=artist)
        for similar_artist in same_artists:
            combined_songs.update(song_book[similar_artist])
        for entry in combined_songs:
            entry.artist = max_artist
        if len(same_artists) >= 2:
            print(f"combining {max_artist} < {same_artists}", flush=True)
        updated_song_book[max_artist] = combined_songs
    return updated_song_book


def clean_song_book(song_book):
    lenX = len(song_book)
    print(f"song book has {lenX} artists", flush=True)
    # Remove artist with no songs
    updated_song_book = {key: value for key, value in song_book.items() if value}
    lenY = len(updated_song_book)
    print(f"removed {lenX - lenY} empty artists", flush=True)
    # Check for missing ", the"
    for artist in list(updated_song_book.keys()):
        variant_artist = artist + ", the"
        if variant_artist in updated_song_book:
            for entry in updated_song_book[artist]:
                entry.artist = entry.artist + ", the"
            updated_song_book[variant_artist] = (
                updated_song_book[artist] + updated_song_book[variant_artist]
            )
            del updated_song_book[artist]
    lenX = len(updated_song_book)
    print(f"removed {lenY - lenX} , the artists", flush=True)
    # Check for songs that are artists
    updated_song_book = fix_songs_are_artists(updated_song_book)
    lenY = len(updated_song_book)
    print(f"removed {lenX - lenY} switched artists", flush=True)
    # Merge artist names that are very similar
    updated_song_book = merge_similar_artists(updated_song_book)
    lenX = len(updated_song_book)
    print(f"removed {lenY - lenX} similar artists", flush=True)
    print(f"updated song book has {len(updated_song_book.keys())} artists", flush=True)
    print(
        f"song count final {sum(len(songs) for songs in updated_song_book.values())}",
        flush=True,
    )
    # update file names
    for artist in updated_song_book:
        for entry in updated_song_book[artist]:
            entry.new_file_name = make_clean_file_name(entry)
    return updated_song_book


valid_extensions = {
    ".wmv",
    ".wav",
    ".mp3",
    ".cdg",
    ".zip",
    ".rar",
    ".mp4",
    ".avi",
    ".mpg",
    ".bin",
    ".scn",
}


def is_music(file_path):
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    return ext in valid_extensions


def is_template_ini(file_path):
    return os.path.basename(file_path).lower() == "template.ini"


def make_clean_file_name(entry):
    discid = (
        entry.discid
        if entry.discid is not None
        else "XX"
        + entry.artist.strip()[:1].replace(" ", "")
        + entry.title.strip()[:1].replace(" ", "")
        + "0"
    )
    trackno = entry.trackno if entry.trackno is not None else "01"
    entry.discid = discid.upper()
    entry.trackno = trackno
    return f"{discid.upper().strip()}-{trackno.strip()} - {titlecase(entry.artist).strip()} - {titlecase(entry.title).strip()}"


# file_path is the original path, file_name may have been modified from original
def make_entry_from_template(file_path, file_name):
    dir_name = os.path.dirname(file_path)
    text, ext = os.path.splitext(file_name)
    text = os.path.basename(text)
    cleaned = clean_words(text)
    for template in all_templates:
        match = re.match(template, cleaned)
        if match:
            if (
                not match.groupdict().get("Artist")
                or not match.groupdict().get("Artist").strip()
                or not match.groupdict().get("Title")
                or not match.groupdict().get("Title").strip()
            ):
                break
            entry = SongEntry(
                discid=match.groupdict().get("DiscID"),
                trackno=match.groupdict().get("TrackNo"),
                artist=match.group("Artist").strip(),
                title=match.group("Title").strip(),
                template=template,
                file_ext=ext,
                current_file_name=text,
                new_file_name=cleaned,
                current_dir=dir_name,
            )
            # if entry.artist.startswith('22'):
            #     print(entry, flush=True)
            #     exit()
            clean_file_name = make_clean_file_name(entry)
            if clean_file_name.startswith("XX"):
                clean_file_name = clean_file_name[11:]
            if len(file_name) / len(clean_file_name) < 0.75:
                break
            return entry
    return None


def make_broken_entry(file_path, file_name):
    dir_name = os.path.dirname(file_path)
    text, ext = os.path.splitext(file_name)
    text = os.path.basename(text)
    cleaned = clean_words(text)
    return SongEntry(
        discid=None,
        trackno=None,
        artist=None,
        title=None,
        template=None,
        file_ext=ext,
        current_file_name=text,
        new_file_name=cleaned,
        current_dir=dir_name,
    )


def eval_templates(file_path):
    file_name = os.path.basename(file_path)
    entry = None
    entry = make_entry_from_template(file_path, file_name)
    if entry is None:
        entry = make_broken_entry(file_path, file_name)
    return entry


def read_song_book_from_dir(root_dir):
    song_book = defaultdict(list)
    broken_song_book = defaultdict(list)
    random_files = []
    ini_files = []
    for file_path in glob.iglob(f"{root_dir}/**", recursive=True):
        if not os.path.isfile(file_path):
            continue
        if is_template_ini(file_path):
            ini_files.append(file_path)
            continue
        if not is_music(file_path):
            random_files.append(file_path)
            continue
        entry = eval_templates(file_path)
        if entry.artist:
            entry = fix_artist_wvocal(entry)
            entry = fix_artist_duet(entry)
            entry = fix_artist_christmas(entry)
            entry.artist = normalize_artist_name(entry.artist.strip())
            entry.title = normalize_song_title(entry.title.strip())
            song_book[entry.artist].append(entry)
            print(f"parsed {make_clean_file_name(entry)}", flush=True)
        else:
            broken_song_book[""].append(entry)
            print(f"could not parse {entry.new_file_name}", flush=True)
    return (song_book, broken_song_book)


def compute_similar_suffix(song1, song2):
    # Normalize the titles by stripping leading and trailing whitespace
    song1 = song1.strip()
    song2 = song2.strip()
    # Get the minimum length of the two song titles
    min_length = min(len(song1), len(song2))
    max_length = max(len(song1), len(song2))
    if song1[:min_length] == song2[:min_length] and min_length > 8 and min_length / max_length > .5:
        return True
    return False

def remove_similar_songs(songs):
    cleaned_songs = set()
    for song in songs:
        song = song.removesuffix("(remix)")
        song = song.removesuffix("(duet)")
        song = song.removesuffix("(wvocals)")
        song = song.removesuffix("(radio version)")
        song = song.removesuffix("[sc]")
        song = song.removesuffix("(mpx)")
        song = song.strip()
        if not any(
            compute_similar_suffix(remove_the(song), remove_the(other_song)) or 
            Levenshtein.distance(remove_the(song), remove_the(other_song)) <= 1 + 0.14 * max(len(remove_the(song)), len(remove_the(other_song)))
            for other_song in cleaned_songs
        ):
            cleaned_songs.add(song)
    return cleaned_songs

def write_latex_songbook_to_file(artist_song_dict, output_file_path):
    with open(output_file_path, 'w') as file:
        # Sort artists alphabetically
        sorted_artists = sorted(artist_song_dict.keys())
        for artist in sorted_artists:
            file.write(f'\\artistsection{{{titlecase(artist)}}}\n')
            file.write('\\begin{songlist}\n')
            # Sort songs alphabetically for each artist
            sorted_songs = sorted(artist_song_dict[artist])
            for song in sorted_songs:
                file.write(f'\\item {titlecase(song)}\n')
            file.write('\\end{songlist}\n\n')

def compute_file_hash(file_path, chunk_size=4096):
    """Compute the SHA-256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def rename_and_rearchive(entry, root_dir, delete=False):
    old_path = Path(entry.current_dir) / f"{entry.current_file_name}{entry.file_ext}"

    # Determine artist directory or fallback for badly named files
    artist_dir = (
        Path(root_dir) / entry.artist[0].upper() / titlecase(entry.artist.strip())
        if entry.artist
        else Path(root_dir) / "#Badly Named"
    )

    new_path = artist_dir / f"{entry.new_file_name}{entry.file_ext}"
    new_path_fallback = Path(root_dir) / "#Broken Archive" / f"{entry.current_file_name}{entry.file_ext}"
    temp_dir = Path(root_dir) / "#Temp Folder Delete Me" / entry.new_file_name

    if not entry.new_file_name.startswith("XX") and old_path == new_path:
        return

    # Create necessary directories
    for path in [new_path_fallback.parent, new_path.parent, temp_dir]:
        path.mkdir(parents=True, exist_ok=True)

    if entry.new_file_name.startswith("XX"):
        entry.trackno = "01"
        entry.new_file_name = make_clean_file_name(entry)
        new_path = artist_dir / f"{entry.new_file_name}{entry.file_ext}"
        for count in range(1, 11):
            if not new_path.exists():
                break
            if compute_file_hash(old_path) == compute_file_hash(new_path):
                print(f"Exact file hash duplicate: {old_path} and {new_path}, not copying.", flush=True)
                handle_delete_original(old_path, new_path, delete)
                return
            entry.trackno = str(int(entry.trackno) + 1).zfill(2)
            entry.new_file_name = make_clean_file_name(entry)
            new_path = artist_dir / f"{entry.new_file_name}{entry.file_ext}"
        else:
            print(f"Error: too many file conflicts for {new_path}", flush=True)
            return

    # Process archives (.zip, .rar)
    if entry.file_ext in [".zip", ".rar"]:
        process_archive(old_path, new_path, new_path_fallback, temp_dir)
    else:
        shutil.copy2(old_path, new_path)
        print(f"Copied:\n {old_path} to\n {new_path}\n\n", flush=True)

    handle_delete_original(old_path, new_path, delete)


def process_archive(old_path, new_path, new_path_fallback, temp_dir):
    """Process archive files by decompressing, renaming contents, and re-archiving."""
    try:
        with ArchiveFile(old_path) as archive:
            archive.extractall(destination=temp_dir)

            # Rename files inside the archive
            for member in archive.get_members():
                if member.is_file:
                    old_file_path = temp_dir / member.name
                    new_file_name = f"{new_path.stem}{old_file_path.suffix}"
                    new_file_path = temp_dir / new_file_name
                    old_file_path.rename(new_file_path)

            # Re-archive the files
            with ArchiveFile(new_path, "w") as new_archive:
                for file in temp_dir.iterdir():
                    if file.is_file():
                        new_archive.write(file, arcname=file.name)

        print(f"Copied:\n {old_path} to\n {new_path}\n\n", flush=True)

    except Exception as e:
        print(f"Error: {e}. Bad archive file: {old_path}", flush=True)
        print(
            f"Copying bad archive from {old_path} to {new_path_fallback}.", flush=True
        )
        shutil.copy2(old_path, new_path_fallback)

    finally:
        clean_up_temp_dir(temp_dir)


def clean_up_temp_dir(temp_dir):
    """Clean up temporary files and directory."""
    for file in temp_dir.iterdir():
        try:
            file.unlink()
        except PermissionError as e:
            print(f"Permission error when deleting {file}: {e}", flush=True)

    try:
        temp_dir.rmdir()
    except OSError as e:
        print(f"Error when removing temp directory {temp_dir}: {e}", flush=True)


def handle_delete_original(old_path, new_path, delete=False):
    """Delete the original file after re-archiving if the delete flag is set."""
    if not delete:
        return
    try:
        if old_path == new_path:
            print(f"Not deleting same path: {new_path} to {old_path}", flush=True)
            return
        if os.path.exists(old_path):
            os.remove(old_path)
            print(f"Deleted original file: {old_path}", flush=True)
        else:
            print(f"File not found: {old_path}", flush=True)
    except Exception as e:
        print(f"Error deleting file {old_path}: {e}", flush=True)


def remove_empty_dirs(path):
    # Traverse the directory tree from the bottom up
    print("Removing empty directories", flush=True)
    for dirpath, dirnames, filenames in os.walk(path, topdown=False):
        for dirname in dirnames:
            dir_to_check = os.path.join(dirpath, dirname)
            # Check if the directory is empty
            if not os.listdir(dir_to_check):
                # Remove the empty directory
                os.rmdir(dir_to_check)
                print(f"Removed empty directory: {dir_to_check}", flush=True)


def run_fix_songs(folder_path, new_path, delete=False):
    song_book, broken_song_book = read_song_book_from_dir(folder_path)
    song_book = clean_song_book(song_book)

    # Rename and rearchive valid song entries
    for artist in sorted(song_book):
        for entry in song_book[artist]:
            rename_and_rearchive(entry, Path(new_path), delete)

    # Handle broken songs (use appropriate key from broken_song_book)
    if "" in broken_song_book:
        for entry in broken_song_book[""]:
            rename_and_rearchive(entry, Path(new_path), delete)

    # Remove empty directories
    remove_empty_dirs(new_path)

    # Flatten the song_book dictionary: artist -> set of song titles
    flattened_dict = {artist: {entry.title for entry in song_book[artist]} for artist in song_book}

    # Clean up the song titles by removing similar entries
    for artist in flattened_dict:
        flattened_dict[artist] = remove_similar_songs(flattened_dict[artist])

    # Write the flattened dictionary to a JSON file with titlecase applied to both artist and titles
    songbook_path = Path(new_path) / "#Song Book"
    songbook_path.mkdir(parents=True, exist_ok=True)
    json_output_path = songbook_path / "songbook.json"
    # Sort both artists and titles
    sorted_data = {
        titlecase(artist): sorted([titlecase(title) for title in titles])
        for artist, titles in sorted(flattened_dict.items())  # Sort artists
    }
    # Write to the JSON file
    with open(json_output_path, "w") as json_file:
        json.dump(sorted_data, json_file, indent=4)

    latex_output_path = songbook_path / "songbook.tex"
    write_latex_songbook_to_file(flattened_dict, latex_output_path)
    

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Fix songs in the Karaoke song library."
    )
    parser.add_argument(
        "folder_path",
        nargs="?",
        default="/Volumes/Seagate Portable Drive/Karaoke Song Library",
        help="Path to the folder containing the original song library.",
    )
    parser.add_argument(
        "new_path",
        nargs="?",
        default="/Volumes/Seagate Portable Drive/Karaoke Song Library Fixed",
        help="Path to the new folder where the fixed song library will be saved.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the original file after renaming and rearchiving.",
    )
    args = parser.parse_args()

    # Use the parsed arguments
    folder_path = args.folder_path
    new_path = args.new_path

    # Run the main song-fixing logic
    print(f"Delete original is {args.delete}")
    run_fix_songs(folder_path, new_path, args.delete)


if __name__ == "__main__":
    main()
