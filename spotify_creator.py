import pandas as pd
from urllib.parse import urlencode
from dotenv import load_dotenv
import os
import base64
from requests import post, get
from selenium import webdriver
import time
import json


### Loads all env variables
load_dotenv()
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")

## Main function handles control loop
def main():
    auth = get_authorization()
    token = get_token(auth)
    user_id = get_user_id(token)

    opt_str = """What would you like to do? \n 
    1. Create Playlist From CSV \n
    2. Create a Playlist \n
    3. Quit  \n
    Enter 1, 2, or 3\n"""
    user_input = input(opt_str)
    while user_input != "3":
        if user_input == "1":
            create_from_csv(token, user_id)
        elif user_input == "2":
            create_playlist(token, user_id)
        user_input = input(opt_str)

# this opens a browser that the user can sign into and then stores the auth code
def get_authorization():

    auth_headers = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "user-library-read playlist-modify-private playlist-modify-public"
    }

    # Here chrome webdriver is used
    driver = webdriver.Chrome()    

    # Open the URL
    url = "https://accounts.spotify.com/authorize?" + urlencode(auth_headers)
    driver.get(url)

    # Wait for the user to finish with the browser
    while True:
        try:
            # Try to get the current URL
            current_url = driver.current_url
            if "code=" in current_url:
                break
            time.sleep(1)  # Sleep for a bit to not hammer the CPU
        except Exception as e:
            # If an error occurred, the window was probably closed
            print("Browser window was closed")
            break

    # Store the final URL (the URL of the window when it was closed)
    final_url = current_url
    _, _, auth_code = final_url.partition("code=")

    # Now get the same range from the original string
    start_index = final_url.index("code=") + len("code=")
    auth_code = final_url[start_index:]

    # Make sure we quit the driver to close everything properly
    driver.quit()
    
    return auth_code

# this takes the auth code and gets a session token
def get_token(auth_code):
    auth_string = CLIENT_ID + ":" + CLIENT_SECRET
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": auth_code, 
        "redirect_uri": REDIRECT_URI
    }
    result = post(url, headers=headers, data=data)
    token = result.json()["access_token"]
    return token

# This function use the token to get the spotify user id 
def get_user_id(token):
    user_headers = user_header(token,"application/json")
    user_results = get("https://api.spotify.com/v1/me", headers=user_headers)
    return user_results.json()['id']

# This functions calls the create playlist function and then also asks the user for a csv file of songs to add
def create_from_csv(token, user_id):
    name = create_playlist(token, user_id)
    path_to_csv = input("Enter path to csv example /csvs/myplay.csv: ")  
    df = pd.read_csv(path_to_csv) 
    uri_list = get_uri_list(df, name, token)
    add_to_playlist(token, name, uri_list)

# This function creates the playlist and asks for a name and description
def create_playlist(token, user_id):
    name, desc = get_playlist_info()
    
    url = f"https://api.spotify.com/v1/users/{user_id}/playlists"
    print(url)
    headers = user_header(token,"application/json")

    data = {
        "name": name,
        "description": desc,
        "public": True
    }

    result = post(url, headers=headers, data= (json.dumps(data)))
    return name


## adds a list of tracks of their URI id to the playlist given
def add_to_playlist(token, playlist_name, tracks):
    id = get_play_list_id(token, playlist_name)
    url = f"https://api.spotify.com/v1/playlists/{id}/tracks"
    headers = user_header(token,"application/json")

    chunks = [tracks[x:x+100] for x in range(0, len(tracks), 100)]
    for lists in chunks:
        print(lists)
        data = {
            "uris": lists,
            "position": 0
        }
        result = post(url, headers=headers, data=json.dumps(data))
        
    return

## gets the id of a playlist
def get_play_list_id(token, name):
    url = "https://api.spotify.com/v1/me/playlists"

    headers = user_header(token,"application/json")

    result = get(url, headers=headers)
    playlists = result.json()
    for playlist in playlists['items']:
        if playlist['name'] == name:
            return playlist['id']

# This asks the users input for playlist info
def get_playlist_info():
    name = input("Enter playlist name: ")
    desc = input("Enter description for playlist: ")
    return name, desc 

# This does a look up on all the song names in the df and returns spotfies URI for each song
def get_uri_list(df, file_name,token):
    user_headers = user_header(token,"application/json")
      
    user_params = {
        "limit": 1
    }

    uri_list = []
    counter = 0
    for song in df["Name"]:
        tracks = get(f"https://api.spotify.com/v1/search?q=%2520track%3A{song}%2520&type=track&limit=2", params=user_params, headers=user_headers)        
        items = tracks.json()['tracks']['items']
        if len(items) >= 1:
            uri = items[0]['uri']
            print(uri , str(counter) + "/" + str(len(df["Name"])))
            uri_list.append(uri)
            counter+= 1
        # if counter > 5:
        #     break
    with open(f'uri_{file_name}.json', 'w') as jsonfile:
        json.dump(uri_list, jsonfile)

    return uri_list

def user_header(token, content_type):
    return {
        "Authorization": "Bearer " + token,
        "Content-Type": content_type
    }

if __name__ == "__main__":
    main()