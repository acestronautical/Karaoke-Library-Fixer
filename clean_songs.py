import re
from collections import defaultdict
import Levenshtein

def normalize_artist_name(name):
    name = clean_words(name)
    name = fix_last_comma_first(name)
    name = fix_artist_the(name)
    return name

def normalize_song_title(title):
    title = clean_words(title)
    title = fix_song_the(title)

def fix_last_comma_first(name):
    parts = name.split(',')
    if len(parts) == 2:
        if parts[1] == " the":
            return name
        last_name = parts[0].strip()
        first_name = parts[1].strip()
        if " and " in first_name or " and " in last_name:
            return name
        return f"{first_name} {last_name}".strip()
    return name

def fix_artist_the(name):
    if not name.endswith(", the") and name.endswith(" the"):
        return name.removesuffix(" the") + ", the"
    if name.startswith("the "):
        return name.removeprefix("the ") + ", the"
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
    words = words.rstrip(',')
    words = remove_duplicate_spaces(words)
    words = replace_common_apostrophe_issues(words)
    words = replace_special_chars(words)
    return words

def remove_duplicate_spaces(text):
    return re.sub(' +', ' ', text).strip()

def replace_special_chars(text):
    return text.replace('’', "'").replace('&', 'and')

def replace_common_apostrophe_issues(text):
    replacements = {
        " im ": " I'm ",
        " youre ": " you're ",
        " your ": " you're ",
        " lets ": " let's ",
        " you'r ": " you're ",
        " isnt ": " isn't ",
        " wont ": " won't ",
        " cant ": " can't ",
        " dont ": " don't ",
        " didnt ": " didn't ",
        " wasnt ": " wasn't ",
        " couldnt ": " couldn't ",
        " shouldnt ": " shouldn't ",
        " wouldnt ": " wouldn't ",
        " arent ": " aren't ",
        " hasnt ": " hasn't ",
        " havent ": " haven't ",
        " hadnt ": " hadn't ",
        " doesnt ": " doesn't ",
        " wasnt ": " wasn't ",
        " ive ": " I've ",
        " id ": " I'd ",
        " ill ": " I'll ",
        " whos ": " who's ",
        " whats ": " what's ",
        " wheres ": " where's ",
        " whens ": " when's ",
        " whys ": " why's ",
        " hows ": " how's ",
        " theres ": " there's ",
        " heres ": " here's ",
        " fallin' ": " falling ",
        " nothin'": " nothing ",
        " takin' ": " taking "
    }
    text = f" {text} "  # Add spaces to ensure replacements only affect whole words
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text.strip()

def title_case(text):
    exceptions = {"a", "an", "and", "as", "at", "but", "by", "for", "if", "in", "nor", "of", "on", "or", "so", "to", "up", "yet", "is"}
    def capitalize_word(word, is_first_word=False):
        if is_first_word or word.lower() not in exceptions:
            return word.capitalize()
        else:
            return word.lower()
    words = text.split()
    if not words:
        return text 
    title_cased_words = [capitalize_word(words[0].lower(), is_first_word=True)] + [capitalize_word(word.lower()) for word in words[1:]]
    title_cased_text = ' '.join(title_cased_words)
    return title_cased_text

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
        if not any(
            compute_similar_suffix(song, other_song) or 
            Levenshtein.distance(song, other_song) <= 1 + 0.14 * max(len(song), len(other_song))
            for other_song in cleaned_songs
        ):
            cleaned_songs.add(song)
    return cleaned_songs

def merge_similar_artists(songbook):
    def clean_artist(artist):
        return remove_the(artist)
    cleaned_artists = {artist: clean_artist(artist) for artist in songbook.keys()}
    artist_set = set(songbook.keys())
    updated_songbook = defaultdict(set)
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
            songs_in_common = songbook[artist].intersection(songbook[other_artist])
            len_songs_in_common = len(songs_in_common)
            if len_songs_in_common < 1:
                continue
            words1 = clean_other_artist_name.split()
            words2 = clean_artist_name.split()
            reversed_words2 = words2[::-1]
            is_flipped = words1 == reversed_words2
            if is_flipped:
                same_artists.append(other_artist)
                artist_set.remove(other_artist)
            elif Levenshtein.distance(clean_artist_name, clean_other_artist_name) <= distance_threshold:
                same_artists.append(other_artist)
                artist_set.remove(other_artist)
        combined_songs = set()
        max_artist = max(same_artists, key=lambda a: len(songbook[a]), default=artist)
        for similar_artist in same_artists:
            combined_songs.update(songbook[similar_artist])
        if len(same_artists) >= 2:
            print(f"combining {max_artist} < {same_artists}")
        updated_songbook[max_artist] = combined_songs
    return updated_songbook

def fix_songs_are_artists(songbook):
    updated_songbook = {}
    artist_keys = songbook.keys()
    for artist, songs in songbook.items():
        songs_are_artist = True
        for song in list(songs):
            if not (normalize_artist_name(song) in artist_keys):
                songs_are_artist = False
                updated_songbook[artist] = songs
                break
        if songs_are_artist:
            for song in list(songs):
                song_artist = normalize_artist_name(song)
                if song_artist not in updated_songbook:
                    updated_songbook[song_artist] = set()
                updated_songbook[song_artist].add(fix_song_the(artist))
                # print(f"should be Artist: {song_artist} Song: {artist}")
    return updated_songbook

def clean_songbook(songbook):
    lenX = len(songbook)
    print(f"songbook has {lenX} artists")
    # Remove artist with no songs
    updated_songbook = {key: value for key, value in songbook.items() if value}
    lenY = len(updated_songbook)
    print(f"removed {lenX - lenY} empty artists")
    # Check for missing ", the"
    for artist in list(updated_songbook.keys()):
        variant_artist = artist + ", the"
        if variant_artist in updated_songbook:
            updated_songbook[variant_artist].update(updated_songbook[artist])
            del updated_songbook[artist]
    lenX = len(updated_songbook)
    print(f"removed {lenY - lenX} , the artists")
    # Check for songs that are artists
    updated_songbook = fix_songs_are_artists(updated_songbook)
    lenY = len(updated_songbook)
    print(f"removed {lenX - lenY} switched artists")
    # Merge artist names that are very similar
    updated_songbook = merge_similar_artists(updated_songbook)
    lenX = len(updated_songbook)
    print(f"removed {lenY - lenX} similar artists")
    # Remove similar songs for each artist
    for artist in updated_songbook:
        updated_songbook[artist] = remove_similar_songs(updated_songbook[artist])
    print(f"updated songbook has {len(updated_songbook.keys())} artists")
    print(f"song count final {sum(len(songs) for songs in updated_songbook.values())}")
    return updated_songbook

#Change this to read file names from drive
# def read_songbook_from_file(file_path):
#     songbook = defaultdict(set)
#     with open(file_path, 'r') as file:
#         text = file.read().strip()
#     lines = text.split('\n')
#     current_artist = None
#     for line in lines:
#         if line.lower().startswith('artist: '):
#             artist_name = line[len('artist: '):].strip()
#             artist_name = artist_name.lower()
#             current_artist = normalize_artist_name(artist_name)
#             if current_artist not in songbook:
#                 songbook[current_artist] = set()
#         elif line.lower().startswith('song title: '):
#             if current_artist:
#                 song_title = line[len('song title: '):].strip()
#                 song_title = song_title.lower()
#                 song_title = clean_words(song_title)
#                 song_title = fix_song_the(song_title)
#                 songbook[current_artist].add(song_title)
#     print(f"song count initial {sum(len(songs) for songs in songbook.values())}")
#     return songbook

#Change this to write files to drive
# def write_songbook_to_file(artist_song_dict, output_file_path):
#     with open(output_file_path, 'w') as file:
#         # Sort artists alphabetically
#         sorted_artists = sorted(artist_song_dict.keys())
#         for artist in sorted_artists:
#             file.write(f'Artist: {title_case(artist)}\n')
#             # Sort songs alphabetically for each artist
#             sorted_songs = sorted(artist_song_dict[artist])
#             for song in sorted_songs:
#                 file.write(f'Song Title: {title_case(song)}\n')
#             file.write('\n')  # Add a blank line between artists

def write_latex_songbook_to_file(artist_song_dict, output_file_path):
    with open(output_file_path, 'w') as file:
        # Sort artists alphabetically
        sorted_artists = sorted(artist_song_dict.keys())
        for artist in sorted_artists:
            file.write(f'\\artistsection{{{title_case(artist)}}}\n')
            file.write(f'\\begin{{songlist}}\n')
            # Sort songs alphabetically for each artist
            sorted_songs = sorted(artist_song_dict[artist])
            for song in sorted_songs:
                file.write(f'\\item {title_case(song)}\n')
            file.write(f'\\end{{songlist}}\n\n')

# test_input_file_path = 'scraped_test.txt'
# test_output_file_path = 'cleaned_songs_test.txt'
# test_songbook_input = read_songbook_from_file(test_input_file_path)
# test_songbook_input = clean_songbook(test_songbook_input)
# write_songbook_to_file(test_songbook_input, test_output_file_path)

input_file_path = 'scraped.txt'
output_file_path = 'cleaned_songs.txt'
output_latex_path = 'cleaned_songs.tex.txt'
songbook = read_songbook_from_file(input_file_path)
songbook = clean_songbook(songbook)
write_songbook_to_file(songbook, output_file_path)
write_latex_songbook_to_file(songbook, output_latex_path)
