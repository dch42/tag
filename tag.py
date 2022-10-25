#! /usr/bin/env python3
"""Tag a folder of flac files by passing Discogs release ID"""

import sys
import os
import argparse
import pickle
import discogs_client
from mutagen.flac import FLAC
from mutagen.mp3 import MP3

EXTENSIONS = [".FLAC"]


def parse_args(args):
    """Define and parse args"""
    parser = argparse.ArgumentParser(description="Tag a directory of FLAC files from Discogs release ID")
    parser.add_argument("-i", type=str, required=True, help="path to dir for tagging")
    parser.add_argument("-r", type=str, required=True, help="Discogs release id")
    return parser.parse_args()


def sanitize_id(id_str):
    """Remove unneeded chars from discogs id"""
    id_str = id_str.replace("r", "").replace("[", "").replace("]", "")
    return id_str


def get_token():
    """Fetch or create token pkl file for authentication"""

    token_file = "./.discogs_token.pkl"

    def pickle_token(token_file):
        """Write input to token pickle"""
        token_input = " "
        while not token_input.isalpha():
            token_input = input("Please enter your Discogs personal access token: ")
            if len(token_input) != 40:
                token_input = ""
                print(
                    "\033[91m[INVALID ENTRY]\033[00m\
Token must be string of 40 alphabetical characters. Please try again.\n"
                )
        with open(token_file, "wb") as token_pkl:
            pickle.dump(token_input, token_pkl)

    def load_pkl(token_file):
        """Load token from pickle file"""

        try:
            with open(f"{token_file}", "rb") as file:
                token = pickle.load(file)
                return token
        except (pickle.UnpicklingError, EOFError) as err:
            print(f"[ERROR] {err}:\n Something is wrong with token file, try again...")
            pickle_token(token_file)
            load_pkl(token_file)

    while not os.path.isfile(token_file):
        pickle_token(token_file)

    token = load_pkl(token_file)

    return token


class Album:
    """
    Album data and associated file paths
    ...
    Attributes
    ----------
    artist : str
        album artist
    title : string
        album title
    year : int
        year of release
    genres : list
        list of musical genres
    tracklist : list
        list of tracks
    files : list
        list of associated files
    """

    def __init__(self, artist, title, year, genres, files, tracklist):
        self.artist = artist
        self.title = title
        self.year = year
        self.genres = genres
        self.tracklist = tracklist
        self.files = files


def create_file_list(album_dir):
    """Walk dir files and spit out list of audio files"""
    file_list = []
    for root, dirs, files in os.walk(album_dir, topdown=True):
        for filename in sorted(files):
            if filename.upper().endswith(tuple(EXTENSIONS)):
                audio_file = os.path.join(root, filename)
                file_list.append(audio_file)
    return file_list


def create_album(rid, directory):
    """Build album object with data from Discogs and local dir"""

    album_data = (
        f"{d.release(rid).artists[0].name}",
        f"{d.release(rid).title}",
        f"{d.release(rid).title,d.release(rid).year}",
        f"{d.release(rid).genres}",
        [],
        [],
    )

    files = create_file_list(directory)

    for i, (v1, v2) in enumerate(zip(d.release(rid).tracklist, files)):
        album_data[-1].append(f"{v1.title}")
        album_data[-2].append(f"{v2}")

    album = Album(*(album_data))

    return album

    # cover = d.release(rid).images[0]['uri']


def tag_tracks(album):
    """Tag files using data pulled from supplied Discogs release id"""
    for i, (v1, v2) in enumerate(zip(album.files, album.tracklist)):
        audio = FLAC(v1[i])
        audio["TITLE"] = f"{v2[i]}"
        audio["ALBUM"] = f"{album.title}"
        audio["ARTIST"] = f"{album.artist}"
        audio["DATE"] = f"{album.year}"
        audio["GENRE"] = f"{album.genres[0]}"
        audio["TRACKNUMBER"] = f"{i+1}"
        audio.save()
        print(f"Tagged track {i+1} of {len(album.tracklist)}")


if __name__ == "__main__":
    TOKEN = get_token()
    args = parse_args(sys.argv[1:])
    release_id, directory = sanitize_id(args.r), args.i
    d = discogs_client.Client("Tag/0.1", user_token=TOKEN)
    album = create_album(release_id, directory)
    tag_tracks(album)
