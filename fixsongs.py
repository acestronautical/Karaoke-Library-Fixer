import os
import shutil
import random
import string
import argparse
import re
import glob
import json
import Levenshtein
from titlecase import titlecase
from collections import defaultdict
from pathlib import Path
from archivefile import ArchiveFile
from enum import Enum

DID = r"(?P<DiscID>[A-Za-z0-9]+)"
DIDUPPER = r"(?P<DiscID>[A-Z0-9-]+)"
TNO = r"(?P<TrackNo>\d+)"
DID_TNO = DID + r"-" + TNO

ART = r"(0\d\d?\s|1\d\s)?(?P<Artist>[^-]+)"
ARTNONUM = r"(0\d\d?\s|1\d\s)?(?P<Artist>[^-0-9]+)"
TITLE = r"(?P<Title>[^-]+)"

ARTWDASH = r"(?P<Artist>.+?)"
TITLEWDASH = r"(?P<Title>.+?)"

NUMBERS = r"\d+"
DASH = r"\s*-\s*"
OPTDASH = r"(\s+-?\s*|\s*-?\s+|-)"
DASHSTRICT = r"\s+-\s+"

# ANTIPATTERN "SC8101-01 -01 - My Way.zip"
D_N_NUM_T = re.compile(rf"^{DID_TNO}{DASHSTRICT}\d\d{DASH}{TITLE}$")
# "SC8101-01 - 01 - Sinatra, Frank - My Way.zip"
D_N_NUM_A_T = re.compile(rf"^{DID_TNO}{OPTDASH}{NUMBERS}{DASH}{ART}{DASH}{TITLE}$")
# "SC8101-01-01 - Sinatra, Frank - My Way.zip"
D_N_N_A_T = re.compile(rf"^{DID_TNO}-{NUMBERS}{OPTDASH}{ART}{DASH}{TITLE}$")
# "SC8101-01-01-01 - Sinatra, Frank - My Way.zip"
D_N_N_N_A_T = re.compile(rf"^{DID_TNO}-{NUMBERS}-{NUMBERS}{DASH}{ART}{DASH}{TITLE}$")
# "SC8101-01 - Sinatra, Frank - My Way.zip"
D_N_A_T = re.compile(rf"^{DID_TNO}{OPTDASH}{ART}{DASH}{TITLE}$")
# "Sinatra, Frank - My Way - SC8101-01.zip"
A_T_D_N = re.compile(rf"^{ART}{DASH}{TITLE}{DASH}{DID_TNO}$")
# ANTIPATTERN "sf252-02.zip"
D_N = re.compile(rf"^{DID_TNO}$")
# ANTIPATTERN "02-Your Song.zip"
N_T = re.compile(rf"^{NUMBERS}{DASH}{TITLE}$")
# "Sinatra, Frank - My Way.zip"
A_T = re.compile(rf"^{ART}{DASH}{TITLE}$")
# CBE3-16 - 03 - Eddie Fisher - Oh! My Pa-Pa.cdg
D_N_NUM_A_T_WDASH = re.compile(rf"^{DID_TNO}{DASHSTRICT}\d\d{DASHSTRICT}{ARTWDASH}{DASHSTRICT}{TITLEWDASH}$")
# Cbe2-28 - Third Eye Blind - Semi-Charmed Life
D_N_A_T_WDASH = re.compile(rf"^{DID_TNO}{DASHSTRICT}{ARTWDASH}{DASHSTRICT}{TITLEWDASH}$")
# Cbe2-28-09 - Third Eye Blind - Semi-Charmed Life
D_N_N_A_T_WDASH = re.compile(rf"^{DID_TNO}-{NUMBERS}{DASHSTRICT}{ARTWDASH}{DASHSTRICT}{TITLEWDASH}$")
# "15 - Super Duper - Stone, Joss"
NUM_A_T = re.compile(rf"^{NUMBERS}{DASHSTRICT}{ART}{DASHSTRICT}{TITLE}$")
# System Of A Down - Prison Song - G11249
A_T_D = re.compile(rf"^{ARTNONUM}{DASH}{TITLE}{DASH}{DIDUPPER}$")
# "SPC018 - 07 - Creed  - One Last Breath"
D__N_A_T = re.compile(rf"{DID}{DASHSTRICT}\d\d{DASHSTRICT}{ART}{DASHSTRICT}{TITLE}$")
# ANTIPATTERN CBE314 - 01 - Do The Hokey Pokey.cdg
D__NUM_T = re.compile(rf"^{DID}[-0-9]+{DASHSTRICT}\d\d{DASHSTRICT}{TITLE}$")
# CBE-314-010-901 - Childrens Songs - Do The Hokey Pokey.cdg
D__A_T = re.compile(rf"^{DID}[-0-9]+{DASHSTRICT}{ART}{DASHSTRICT}{TITLE}$")
# CBE113 - 02 - Duet (Hill - Mcgraw) - It's Your Love
D_NUM_A_T = re.compile(rf"^{DID}{DASHSTRICT}{NUMBERS}{DASHSTRICT}{ARTWDASH}{DASHSTRICT}{TITLE}$")
# ASK-65A-02 - Keys, Alicia - Karma
D_N_NUM_A_T_LOOSE = re.compile(rf"^{DIDUPPER}-{TNO}{DASH}{NUMBERS}{DASH}{ART}{DASH}{TITLE}$")
# ASK-65A-02 - Keys, Alicia - Karma
D_N_A_T_LOOSE = re.compile(rf"^{DIDUPPER}-{TNO}{DASH}{ARTNONUM}{DASH}{TITLE}$")


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
        fallback_file_name,
        current_dir,
    ):
        self.artist = artist.strip(" ") if artist else None
        self.title = title.strip(" ") if title else None
        self.template = template
        self.file_ext = file_ext.lower()
        self.current_file_name = current_file_name
        self.fallback_file_name = fallback_file_name
        self.current_dir = current_dir
        self.trackno = str(int(trackno)).zfill(2) if trackno else "01"
        if discid is None:
            discid = "XX" + create_short_uuid()
        self.discid = discid.upper()

    def old_path(self):
        return Path(self.current_dir) / f"{self.current_file_name}{self.file_ext}"

    def bump_trackno(self):
        self.trackno = str(int(self.trackno) + 1).zfill(2)

    def new_file_name(self):
        if self.title and self.artist and self.trackno and self.discid:
            return f"{self.discid.strip()}-{self.trackno.strip()} - {titlecase(self.artist).strip()} - {titlecase(self.title).strip()}"
        else:
            return self.fallback_file_name

    def new_file_name_wext(self):
        return f"{self.new_file_name()}{self.file_ext}"

    def __lt__(self, other):
        if self.trackno and other.trackno:
            return self.trackno < other.trackno
        else:
            return self.title < other.title

    def __str__(self):
        return f" discid: {self.discid}, trackno: {self.trackno}, artist: {self.artist}, title: {self.title}, template: {get_global_varname(self.template)}, current file name: {self.current_file_name}, new file name: {self.fallback_file_name}, current dir: {self.current_dir}"


def name_cdg_to_mp3(songs: list[SongEntry]) -> None:
    # Create a dictionary to map base names of .mp3 files (without extension) to their discids
    mp3s = {entry.old_path().stem: entry.discid for entry in songs if entry.file_ext == ".mp3"}

    for entry in songs:
        # Check if the current entry is a .cdg file
        if entry.file_ext == ".cdg":
            # Create the base name for the .cdg file (without extension)
            base_name = entry.old_path().stem  # Remove .cdg extension

            # Check if the base name matches an existing .mp3 base name
            if base_name in mp3s:
                entry.discid = mp3s[base_name]
            else:
                print(f"Failed to match .cdg with .mp3 for {entry.current_file_name}, copying anyways")


def normalize_artist(name):
    name = name.lower()
    name = clean_words(name)
    name = name.replace("-", " ")
    name = fix_last_comma_first(name)
    name = fix_the(name, Mode.ARTIST)
    return name.strip()


def normalize_title(title):
    title = title.lower()
    title = clean_words(title)
    title = title.replace("-", " ")
    title = fix_the(title, Mode.TITLE)
    return title.strip()


def fix_last_comma_first(name):
    parts = name.split(",")
    if len(parts) == 2:
        last_name = parts[0].strip()
        first_name_and_others = parts[1].strip()
        if " and " in first_name_and_others:
            first_name, other_names = first_name_and_others.split(" and ", 1)
            first_name = first_name.strip()
            other_names = other_names.strip()
            return f"{first_name} {last_name} and {other_names}".strip()
        else:
            if first_name_and_others == "the":
                return name
            first_name = first_name_and_others
            return f"{first_name} {last_name}".strip()
    return name


class Mode(Enum):
    ARTIST = 1
    TITLE = 2
    REMOVE = 3


def fix_the(name, mode: Mode):
    new_name = name
    new_name = new_name.removesuffix(", the")
    new_name = new_name.removesuffix(" the")
    new_name = new_name.removeprefix("the ")
    if new_name == name:
        return name
    elif mode == Mode.ARTIST:
        return new_name + ", the"
    elif mode == Mode.TITLE:
        return "the " + new_name
    elif mode == Mode.REMOVE:
        return new_name


def clean_words(words):
    words = words.rstrip(",")
    words = words.replace("_", " ")  # replace underscores with spaces
    words = re.sub(" +", " ", words).strip()  # remove duplicate spaces
    # replace special characters
    words = words.replace("’", "'").replace("`", "'").replace("!", "").replace(".", "")
    words = words.replace("&", "and").replace("$", "s")
    # remove apostrophes
    words = f" {words} "  # Add spaces to ensure replacements only affect whole words
    words = words.replace("in' ", "ing ")
    words = words.replace("'", "")
    return words.strip()


# Compiling the patterns once
PATTERNS = {
    "wvocals": re.compile(
        r"\(wvocal\)|(\(vocal\)|\(vocals\)|\(wvocals\)|\(w-vocal\)|\(w-vocals\)|wvocals|wvocal|w-vocals|w-vocal|w vocal)",
        re.IGNORECASE,
    ),
    "duet": re.compile(r"(\(duet version\)|\(duet\)| duet )", re.IGNORECASE),
    "christmas": re.compile(r"(\(christmas\))", re.IGNORECASE),
}


def fix_artist_suffix(entry, pattern, suffix):
    artist_clean = re.sub(pattern, "", entry.artist).strip()
    title_clean = re.sub(pattern, "", entry.title).strip()
    if artist_clean != entry.artist or title_clean != entry.title:
        entry.artist = artist_clean
        entry.title = title_clean + f" ({suffix})"
    return entry


def fix_all_artist_flags(entry):
    entry = fix_artist_suffix(entry, PATTERNS["wvocals"], "wvocals")
    entry = fix_artist_suffix(entry, PATTERNS["duet"], "duet")
    entry = fix_artist_suffix(entry, PATTERNS["christmas"], "christmas")
    return entry


def fix_song_artist_flipped(song_book):
    updated_song_book = {}
    artist_keys = song_book.keys()
    for artist, entries in song_book.items():
        most_songs = 0
        songs_are_artist = True
        for entry in entries:
            norm_artist = normalize_artist(entry.title)
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


def merge_similar_typo_artists(song_book):
    def clean_artist(artist):
        return fix_the(artist, Mode.REMOVE)

    cleaned_artists = {artist: clean_artist(artist) for artist in song_book.keys()}
    artist_set = set(song_book.keys())
    updated_song_book = {}
    while artist_set:
        artist = artist_set.pop()
        same_artists = [artist]
        clean_name = cleaned_artists[artist]
        to_check = list(artist_set)  # List to avoid modifying the set during iteration
        for other_artist in to_check:
            clean_other = cleaned_artists[other_artist]
            # Check if length difference exceeds threshold
            if abs(len(clean_name) - len(clean_other)) > 0.2 * min(len(clean_name), len(clean_other)):
                continue
            # Check for song title overlap
            titles_artist = {entry.title for entry in song_book[artist]}
            titles_other = {entry.title for entry in song_book[other_artist]}
            min_songs = min(len(titles_artist), len(titles_other))
            common_songs = len(titles_artist.intersection(titles_other))
            if common_songs / min_songs < 0.3:
                continue
            if clean_other.split() == clean_name.split()[::-1]:
                same_artists.append(other_artist)
                artist_set.remove(other_artist)
            elif Levenshtein.distance(clean_name, clean_other) <= 0.2 * len(clean_name):
                same_artists.append(other_artist)
                artist_set.remove(other_artist)
        combined_songs = {song for artist in same_artists for song in song_book[artist]}
        max_artist = max(same_artists, key=lambda a: len(song_book[a]), default=artist)
        for entry in combined_songs:
            entry.artist = max_artist
        if len(same_artists) > 1:
            print(f"combining {max_artist} < {same_artists}", flush=True)
        updated_song_book[max_artist] = combined_songs
    return updated_song_book


def fix_artist_missing_the(song_book):
    for artist in list(song_book.keys()):
        variant_artist = f"{artist}, the"
        if variant_artist in song_book:
            for entry in song_book[artist]:
                entry.artist += ", the"
            song_book[variant_artist].extend(song_book[artist])
            del song_book[artist]
    return song_book


def clean_song_book(song_book, flip=True, merge=True):
    original_count = len(song_book)
    print(f"Song Book has {original_count} artists", flush=True)
    print(f"Song Book has: {sum(len(songs) for songs in song_book.values())} songs", flush=True)
    updated_song_book = {artist: songs for artist, songs in song_book.items() if songs}
    updated_song_book = fix_artist_missing_the(updated_song_book)
    if flip:
        updated_song_book = fix_song_artist_flipped(updated_song_book)
    if merge:
        updated_song_book = merge_similar_typo_artists(updated_song_book)
    final_count = len(updated_song_book)
    print(f"Updated Song Book has {final_count} artists", flush=True)
    print(f"Updated Song Book has: {sum(len(songs) for songs in updated_song_book.values())} songs", flush=True)
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


def make_entry_from_template(file_path):
    file_name = os.path.basename(file_path)
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
                fallback_file_name=cleaned,
                current_dir=dir_name,
            )
            clean_file_name = entry.fallback_file_name
            # Adjust file name based on certain conditions
            if clean_file_name.startswith("XX"):
                clean_file_name = clean_file_name[14:]
            # Break if the file name reduction is too large
            if len(file_name) / len(clean_file_name) < 0.75:
                break
            return entry
    return None


def make_broken_entry(file_path):
    file_name = os.path.basename(file_path)
    dir_name = os.path.dirname(file_path)
    text, ext = os.path.splitext(file_name)
    cleaned = clean_words(text)
    return SongEntry(
        discid=None,
        trackno=None,
        artist=None,
        title=None,
        template=None,
        file_ext=ext,
        current_file_name=text,
        fallback_file_name=cleaned,
        current_dir=dir_name,
    )


def eval_templates(file_path):
    entry = make_entry_from_template(file_path)
    if entry is None:
        entry = make_broken_entry(file_path)
    return entry


def read_song_book_from_dir(root_dir):
    song_book = defaultdict(list)
    broken_song_book = defaultdict(list)
    for file_path in glob.iglob(f"{root_dir}/**", recursive=True):
        if not os.path.isfile(file_path) or not is_music(file_path):
            continue
        entry = eval_templates(file_path)
        if entry.artist:
            entry = fix_all_artist_flags(entry)
            entry.artist = normalize_artist(entry.artist)
            entry.title = normalize_title(entry.title)
            song_book[entry.artist].append(entry)
            print(f"parsed {entry.new_file_name()}", flush=True)
        else:
            broken_song_book[""].append(entry)
            print(f"could not parse {entry.fallback_file_name}", flush=True)
    return song_book, broken_song_book


def compute_similar_suffix(song1, song2):
    song1 = song1.strip()
    song2 = song2.strip()
    min_length = min(len(song1), len(song2))
    max_length = max(len(song1), len(song2))
    if min_length > 8 and min_length / max_length > 0.5 and song1[:min_length] == song2[:min_length]:
        return True
    return False


def remove_similar_songs(songs):
    cleaned_songs = set()
    for song in songs:
        song = song.removesuffix("(remix)").removesuffix("(duet)")
        song = song.removesuffix("(wvocals)").removesuffix("(radio version)")
        song = song.removesuffix("[sc]").removesuffix("(mpx)")
        song = song.strip()
        if not any(
            compute_similar_suffix(fix_the(song, Mode.REMOVE), fix_the(other_song, Mode.REMOVE))
            or Levenshtein.distance(fix_the(song, Mode.REMOVE), fix_the(other_song, Mode.REMOVE))
            <= 1 + 0.14 * max(len(fix_the(song, Mode.REMOVE)), len(fix_the(other_song, Mode.REMOVE)))
            for other_song in cleaned_songs
        ):
            cleaned_songs.add(song)
    return cleaned_songs


def write_latex_songbook_to_file(artist_song_dict, output_file_path):
    with open(output_file_path, "w") as file:
        # Write pre-content
        with open("songbook-pre.txt", "r") as pre_file:
            file.write(pre_file.read())

        # Sort artists alphabetically
        sorted_artists = sorted(artist_song_dict.keys())
        for artist in sorted_artists:
            file.write(f"\\artistsection{{{titlecase(artist)}}}\n")
            file.write("\\begin{songlist}\n")

            # Sort songs alphabetically for each artist
            sorted_songs = sorted(artist_song_dict[artist])
            for song in sorted_songs:
                file.write(f"\\item {titlecase(song)}\n")
            file.write("\\end{songlist}\n\n")

        # Write post-content
        with open("songbook-post.txt", "r") as post_file:
            file.write(post_file.read())


def create_short_uuid(length=6):
    # Define the character set: letters (uppercase and lowercase) and digits
    characters = string.ascii_letters + string.digits
    # Generate a random 6-character string
    short_uuid = ''.join(random.choices(characters, k=length))
    return short_uuid


def rename_and_rearchive(entry, root_dir, delete=False):
    old_path = entry.old_path()
    artist_dir = (
        Path(root_dir) / entry.artist[0].upper() / titlecase(entry.artist.strip()) if entry.artist else Path(root_dir) / "#Badly Named"
    )
    new_path = artist_dir / entry.new_file_name_wext()
    new_path_fallback = Path(root_dir) / "#Broken Archive" / entry.new_file_name_wext()
    temp_dir = Path(root_dir) / "#Temp Folder Delete Me" / entry.new_file_name()

    if old_path == new_path or str(old_path).lower() == str(new_path).lower():
        return

    # Create necessary directories
    if new_path.exists():
        print(f"\nAlready Exists:\n {old_path} vs\n {new_path}", flush=True)
    else:
        for path in [new_path_fallback.parent, new_path.parent, temp_dir]:
            path.mkdir(parents=True, exist_ok=True)
        try:
            # Process archives (.zip, .rar)
            if entry.file_ext in [".zip", ".rar"] and not new_path.name == old_path.name:
                process_archive(old_path, new_path, new_path_fallback, temp_dir, entry)
            else:
                if not delete:
                    shutil.copy2(old_path, new_path)
                    print(f"\nCopied:\n {old_path} to\n {new_path}", flush=True)
                else:
                    print(f"\nMoved:\n {old_path} to\n {new_path}", flush=True)
                    old_path.rename(new_path)
        except Exception as e:
            print(f"Error: {e}")
            return

    handle_delete_original(old_path, new_path, delete)


def process_archive(old_path, new_path, new_path_fallback, temp_dir, entry):
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
        print(f"\nCopied and renamed contents:\n {old_path} to\n {new_path}", flush=True)
    except Exception as e:
        print(f"Error: {e}. Bad archive file: {old_path}", flush=True)
        print(f"Copying bad archive from {old_path} to {new_path_fallback}.", flush=True)
        shutil.copy2(old_path, new_path_fallback)


def remove_temp_directory(root_dir: Path):
    # Convert dir_path to a Path object if it's not already one
    temp_dir = root_dir / "#Temp Folder Delete Me"
    if temp_dir.exists() and temp_dir.is_dir():
        shutil.rmtree(temp_dir)
        print(f"Removed directory: {temp_dir}")
    else:
        print(f"Directory does not exist: {temp_dir}")


def handle_delete_original(old_path, new_path, delete=False):
    """Delete the original file after re-archiving if the delete flag is set."""
    if not delete:
        return
    if str(old_path).lower() == str(new_path).lower():
        print(f"Not deleting same path: {new_path} to {old_path}", flush=True)
        return
    try:
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


def run_fix_songs(args):
    folder_path = args.folder_path
    new_path = args.new_path
    song_book, broken_song_book = read_song_book_from_dir(folder_path)
    for artist in sorted(song_book):
        name_cdg_to_mp3(song_book[artist])
    song_book = clean_song_book(song_book, args.flip, args.merge)

    for artist in sorted(song_book):
        for entry in sorted(song_book[artist]):
            rename_and_rearchive(entry, Path(new_path), args.delete)

    if "" in broken_song_book:
        for entry in broken_song_book[""]:
            rename_and_rearchive(entry, Path(new_path), args.delete)

    # Remove directories
    remove_temp_directory(Path(new_path))
    remove_empty_dirs(new_path)

    # make latex and json catalogs
    flattened_dict = {artist: {entry.title for entry in song_book[artist]} for artist in song_book}
    for artist in flattened_dict:
        flattened_dict[artist] = remove_similar_songs(flattened_dict[artist])
    songbook_path = Path(new_path) / "#Song Book"
    songbook_path.mkdir(parents=True, exist_ok=True)
    website_path = songbook_path / "website"
    website_path.mkdir(parents=True, exist_ok=True)

    # Copy contents of a folder (source_folder_path) to the songbook_path
    source_folder_path = Path("website")  # Update this path
    for item in source_folder_path.iterdir():
        if item.is_file():  # Only copy files
            shutil.copy(item, website_path)
        elif item.is_dir():  # If it's a directory, copy its contents
            shutil.copytree(item, website_path / item.name, dirs_exist_ok=True)

    json_output_path = website_path / "songbook.json"
    sorted_data = {
        titlecase(artist): sorted([titlecase(title) for title in titles])
        for artist, titles in sorted(flattened_dict.items())  # Sort artists
    }
    with open(json_output_path, "w") as json_file:
        json.dump(sorted_data, json_file, indent=4)
    latex_output_path = songbook_path / "songbook.tex"
    write_latex_songbook_to_file(flattened_dict, latex_output_path)


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Fix songs in the Karaoke song library.")
    parser.add_argument(
        "folder_path",
        nargs="?",
        default="new-sample-lib",
        help="Path to the folder containing the original song library.",
    )
    parser.add_argument(
        "new_path",
        nargs="?",
        default="new-sample-lib",
        help="Path to the new folder where the fixed song library will be saved.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        default=False,
        help="Delete the original file after renaming and rearchiving.",
    )
    parser.add_argument(
        "--flip",
        action="store_true",
        default=False,
        help="Attempt to switch artist and title",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        default=False,
        help="Attempt to merge mispelled artists",
    )
    args = parser.parse_args()
    # Run the main song-fixing logic
    run_fix_songs(args)


if __name__ == "__main__":
    main()
