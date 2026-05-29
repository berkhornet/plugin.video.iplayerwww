# -*- coding: utf-8 -*-

import sys
import os
import re
from datetime import datetime

import requests
from requests.packages import urllib3
#Below is required to get around an ssl issue
urllib3.disable_warnings()
import urllib
import html
import codecs
import time

import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin

try:
    import cookielib
except:
    import http.cookiejar
    cookielib = http.cookiejar

         
def log_message(message, level=xbmc.LOGINFO):
    """
    Logs a message to the Kodi log file.
    
    :param message: The text to log
    :param level: Kodi log level (default: LOGINFO)
    """
    try:
        if not isinstance(message, str):
            message = str(message)
        xbmc.log(f"[BBC iPlayer] {message}", level)
    except Exception as e:
        xbmc.log(f"[BBC iPlayer] Logging failed: {e}", xbmc.LOGERROR)


def strip_before(text: str, marker: str) -> str:
    """Remove all characters before the first occurrence of marker."""
    if not marker:
        raise ValueError("Marker string cannot be empty.")
    
    index = text.find(marker)
    if index == -1:
        return text  # Marker not found, return original string
    return text[index:]
 
 
def strip_after(text: str, marker: str) -> str:
    """
    Removes everything after the first occurrence of `marker` in `text`.
    If marker is not found, returns the original text.
    """
    if not isinstance(text, str) or not isinstance(marker, str):
        raise TypeError("Both text and marker must be strings.")
    if marker == "":
        raise ValueError("Marker cannot be an empty string.")

    index = text.find(marker)
    if index != -1:
        return text[:index]  # Keep everything before marker
    return text  # Marker not found, return original


def custom_select_image(images):
    if not images:
        return 'DefaultFolder.png'
    return(images.get('promotional_with_logo')
           or images.get('promotionalWithLogo') # Recommendations
           or images.get('promotional')
           or images.get('standard')
           or images.get('default') # Recommendations
           or images.get('portrait')
           or 'DefaultFolder.png').replace('{recipe}', '832x468') 


def create_af3_style_episode_header(subtitle, title, debug, itemtype):
    """
    Creates an AF3 style "Episode Header" from different iPlayer episode "subtitle" formats
    
    Ref.        Input subtitle Format     Input Title Format   Output Format           Watching    Recommendations  Highlights
    ----        ---------------------     ------------------   -------------           --------    ---------------  ----------
    Format 1    Series N: NN. EpisodeTitle                     NxNN. EpisodeTitle          Yes             Yes
    Format 2    Series N: London                               Nx00. EpisodeTitle          Yes
    Format 3    Series N: Episode N                            NxNN. Episode N                             Yes
    Format 4    Episode N                                      1xNN. Episode N             Yes
    Format 5    N. EpisodeTitle                                1xNN. EpisodeTitle                          Yes
    Format 5.1  Text: N. EpisodeTitle                          1xNN. EpisodeTitle                                       Yes
    Format 5.2  Text                                           Text                                                     Yes
    Format 6    None                      ShowTitle            1x01. ShowTitle                             Yes
    Format 7    MovieTitle or tagline     MovieTitle           MovieTitle or tagline       Yes             Yes
    """
    
    color_white = "[COLOR white]"
    color_end = "[/COLOR]"
    
    if debug == True:
        log_message('create_af3_style_episode_header: subtitle = ' + str(subtitle))
        log_message('create_af3_style_episode_header: title = ' + str(title))
   
    # process Format 7
    if itemtype == 'movie':
        if debug == True:
            log_message('create_af3_style_episode_header: Processing Format 7 for title = ' + title)        
        af3_episode_header = "[B]" + title + "[/B][CR]" 
        af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
        if debug == True:
            log_message('create_af3_style_episode_header: Format 7 output = ' + af3_episode_header_colour)        
        return af3_episode_header_colour    
    
    # process Format 6
    if subtitle == 'None':
        if debug == True:
            log_message('create_af3_style_episode_header: Processing Format 6 for subtitle = ' + subtitle)
        af3_episode_header = "[B]" + '1x01. ' + title + "[/B][CR]" 
        af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
        if debug == True:
            log_message('create_af3_style_episode_header: Format 6 output = ' + af3_episode_header_colour)          
        return af3_episode_header_colour
   
    # process Format 4
    if subtitle.startswith("Episode"):
        if debug == True:
            log_message('create_af3_style_episode_header: Processing Format 4 for subtitle = ' + subtitle)
        series_nr = "1"
        episode_1 = subtitle.replace('Episode ','')
        if len(episode_1) == 1:
            episode_nr = '0' + episode_1
        else:
            episode_nr = episode_1           
        af3_episode_header = "[B]" + series_nr + 'x' + episode_nr + '. ' + 'Episode ' + episode_1 + "[/B][CR]"
        af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
        if debug == True:
            log_message('create_af3_style_episode_header: Format 4 output = ' + af3_episode_header_colour)          
        return af3_episode_header_colour
        
    # process Format 5
    if "Series" not in subtitle and subtitle != 'None':
        if debug == True:
            log_message('create_af3_style_episode_header: Processing Format 5 for subtitle = ' + subtitle)

        positionofcolon = subtitle.find(':') # Format 5.1
        if positionofcolon > 0:
            af3_episode_header = "[B]" + subtitle + "[/B][CR]"
            af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
            if debug == True:
                log_message('create_af3_style_episode_header: Format 5.1 output = ' + af3_episode_header_colour)         
            return af3_episode_header_colour
        
        positionofperiod = subtitle.find('.')
        episode_1 = subtitle[:positionofperiod]        
        countofslash = subtitle.count('/') # subtitle probably a date 

        if positionofperiod == -1 and countofslash < 2: # Format 5.2
            af3_episode_header = "[B]" + subtitle + "[/B][CR]"
            af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
            if debug == True:
                log_message('create_af3_style_episode_header: Format 5.2 output = ' + af3_episode_header_colour)         
            return af3_episode_header_colour
                
        series_nr = '1'
        
        if countofslash == 2: # subtitle probably a date
            episode_nr = '00'
            episode_title = subtitle            
        elif positionofperiod == 1:
            episode_nr = '0' + episode_1
        else:
            episode_nr = episode_1
        episode_title = subtitle[positionofperiod + 2:]
        af3_episode_header = "[B]" + series_nr + "x" + episode_nr + ". " + episode_title + "[/B][CR]"
        af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
        if debug == True:
            log_message('create_af3_style_episode_header: Format 5 output = ' + af3_episode_header_colour)         
        return af3_episode_header_colour
    
    # debug message for Formats 1 2 and 3
    if debug == True:
        log_message('create_af3_style_episode_header: Processing Formats  1 2 and 3 for subtitle = ' + subtitle)
        
    # reformat subtitle if input is Format 3
    index = subtitle.find('Episode') # returns -1 if not found
    if index > 1:
        if debug == True:
            log_message('create_af3_style_episode_header: Processing Format 3 for subtitle = ' + subtitle)
        d0 = strip_before(subtitle,'Episode')
        d1 = subtitle.replace('Episode ','')
        d2 = d1 + '.'
        subtitle = d2 + ' ' + d0
    
    # get series number
    t1 = subtitle[7:] # remove "Series " from start of description
    series_nr = strip_after(t1,":")
    
    # get episode number
    t2 = t1.find(" ")
    t3 = t1[t2+1:]
    t4 = strip_after(t3,".")
    try: # obtain episode number if possible, otherwise set to 0
        episode_nr = int(t4)
        if debug == True:
            log_message('create_af3_style_episode_header: Processing Formats 1 and 3 for subtitle = ' + subtitle)
    except Exception: # Format 2
        episode_nr = 0
        if debug == True:
            log_message('create_af3_style_episode_header: Processing Format 2 for subtitle = ' + subtitle)
    episode_nr_pad = f"{episode_nr:02d}"
    episode_nr_pad_str = str(episode_nr_pad)
    
    # get episode title
    t5 = strip_before(t1,".")
    episode_title = t5[2:]
    
    # create AF3 style episode header
    af3_episode_header = "[B]" + str(series_nr) + "x" + episode_nr_pad_str + ". " + episode_title + "[/B][CR]" 
    af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
    if debug == True:
        log_message('create_af3_style_episode_header: Format 1/2/3 output = ' + af3_episode_header_colour)

    return af3_episode_header_colour

# BBC-010: START def get_episode_data
def get_episode_data(subtitle, title, debug, itemtype):
    """
    Creates an AF3 style "Episode Header" from different iPlayer episode "subtitle" formats
    
    Ref.        Input subtitle Format     Input Title Format   Output Format           Watching    Recommendations  Highlights
    ----        ---------------------     ------------------   -------------           --------    ---------------  ----------
    Format 1    Series N: NN. EpisodeTitle                     NxNN. EpisodeTitle          Yes             Yes
    Format 2    Series N: London                               Nx00. EpisodeTitle          Yes
    Format 3    Series N: Episode N                            NxNN. Episode N                             Yes
    Format 4    Episode N                                      1xNN. Episode N             Yes
    Format 5    N. EpisodeTitle                                1xNN. EpisodeTitle                          Yes
    Format 5.1  Text: N. EpisodeTitle                          1xNN. EpisodeTitle                                       Yes
    Format 5.2  Text                                           Text                                                     Yes
    Format 6    None                      ShowTitle            1x01. ShowTitle                             Yes
    Format 7    MovieTitle or tagline     MovieTitle           MovieTitle or tagline       Yes             Yes
    """
    
    color_white = "[COLOR white]"
    color_end = "[/COLOR]"
    
    isEpisode = False
    
    if debug == True:
        log_message('get_episode_data: subtitle = ' + str(subtitle))
        log_message('get_episode_data: title = ' + str(title))
   
    # process Format 7
    if itemtype == 'movie':
        if debug == True:
            log_message('get_episode_data: Processing Format 7 for title = ' + title) 
        isEpisode = True            
        return isEpisode, subtitle, "", ""    
    
    # process Format 6
    if subtitle == 'None':
        if debug == True:
            log_message('get_episode_data: Processing Format 6 for subtitle = ' + subtitle)
        return isEpisode, "", "", ""               
   
    # process Format 4
    if subtitle.startswith("Episode"):
        if debug == True:
            log_message('get_episode_data: Processing Format 4 for subtitle = ' + subtitle)
        series_nr = "1"
        episode_1 = subtitle.replace('Episode ','')
        if len(episode_1) == 1:
            episode_nr = '0' + episode_1
        else:
            episode_nr = episode_1           
        af3_episode_header = "[B]" + series_nr + 'x' + episode_nr + '. ' + 'Episode ' + episode_1 + "[/B][CR]"
        af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
        if debug == True:
            log_message('get_episode_data: Format 4 output = ' + af3_episode_header_colour)            
        return isEpisode, "", "", ""   
        
    # process Format 5
    if "Series" not in subtitle and subtitle != 'None':
        if debug == True:
            log_message('get_episode_data: Processing Format 5 for subtitle = ' + subtitle)

        positionofcolon = subtitle.find(':') # Format 5.1
        if positionofcolon > 0:
            af3_episode_header = "[B]" + subtitle + "[/B][CR]"
            af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
            if debug == True:
                log_message('get_episode_data: Format 5.1 output = ' + af3_episode_header_colour)         
            return isEpisode, '', '', ''
        
        positionofperiod = subtitle.find('.')
        episode_1 = subtitle[:positionofperiod]        
        countofslash = subtitle.count('/') # subtitle probably a date 

        if positionofperiod == -1 and countofslash < 2: # Format 5.2
            af3_episode_header = "[B]" + subtitle + "[/B][CR]"
            af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
            if debug == True:
                log_message('get_episode_data: Format 5.2 output = ' + af3_episode_header_colour)         
            return isEpisode, '', '', ''
                
        series_nr = '1'
        
        if countofslash == 2: # subtitle probably a date
            episode_nr = '00'
            episode_title = subtitle            
        elif positionofperiod == 1:
            episode_nr = '0' + episode_1
        else:
            episode_nr = episode_1
        episode_title = subtitle[positionofperiod + 2:]
        af3_episode_header = "[B]" + series_nr + "x" + episode_nr + ". " + episode_title + "[/B][CR]"
        af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
        if debug == True:
            log_message('get_episode_data: Format 5 output = ' + af3_episode_header_colour)         
        return isEpisode, "", "", ""   
    
    # debug message for Formats 1 2 and 3
    if debug == True:
        log_message('get_episode_data: Processing Formats  1 2 and 3 for subtitle = ' + subtitle)
        
    # reformat subtitle if input is Format 3
    index = subtitle.find('Episode') # returns -1 if not found
    if index > 1:
        if debug == True:
            log_message('get_episode_data: Processing Format 3 for subtitle = ' + subtitle)
        d0 = strip_before(subtitle,'Episode')
        d1 = subtitle.replace('Episode ','')
        d2 = d1 + '.'
        subtitle = d2 + ' ' + d0
    
    # get series number
    t1 = subtitle[7:] # remove "Series " from start of description
    series_nr = strip_after(t1,":")
    
    # get episode number
    t2 = t1.find(" ")
    t3 = t1[t2+1:]
    t4 = strip_after(t3,".")
    try: # obtain episode number if possible, otherwise set to 0
        episode_nr = int(t4)
        if debug == True:
            log_message('get_episode_data: Processing Formats 1 and 3 for subtitle = ' + subtitle)
    except Exception: # Format 2
        episode_nr = 0
        if debug == True:
            log_message('get_episode_data: Processing Format 2 for subtitle = ' + subtitle)
    episode_nr_pad = f"{episode_nr:02d}"
    episode_nr_pad_str = str(episode_nr_pad)
    
    # get episode title
    t5 = strip_before(t1,".")
    episode_title = t5[2:]
    
    # create AF3 style episode header
    af3_episode_header = "[B]" + str(series_nr) + "x" + episode_nr_pad_str + ". " + episode_title + "[/B][CR]" 
    af3_episode_header_colour = f"{color_white}{af3_episode_header}{color_end}"
    if debug == True:
        log_message('get_episode_data: Format 1/2/3 output = ' + af3_episode_header_colour)
    isEpisode = True
    return isEpisode, episode_title, str(series_nr), episode_nr_pad_str    
# BBC-010: END def get_episode_data
    
    
# BBC-010: START functions to get data from the TMDb
def search_tmdb(category, name):
    
    """
    Search TMDb for a TV show or movie and return (tmdb_id, type) if exact match is found.
    category: 'tv' or 'movie'
    """
    
    API_KEY = "e92d7c9d19df047c576ee8724f174e07"  # Replace with your TMDb API key
    BASE_URL = "https://api.themoviedb.org/3"
    
    if not name or not isinstance(name, str):
        raise ValueError("Name must be a non-empty string.")

    try:
        response = requests.get(
            f"{BASE_URL}/search/{category}",
            params={"api_key": API_KEY, "query": name.strip()},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        for result in data.get("results", []):
            title_field = "name" if category == "tv" else "title"
            if result.get(title_field, "").strip().lower() == name.strip().lower():
                return result.get("id"), ("tvshow" if category == "tv" else "movie")

        return None, None

    except requests.exceptions.RequestException as e:
        print(f"Network/API error: {e}")
        return None, None
        

def get_episode_info(tv_id, season_number, episode_number, language="en-US"):

    """
    Fetch episode details from TMDb API.

    :param api_key: Your TMDb API key (string)
    :param tv_id: TMDb TV show ID (int or string)
    :param season_number: Season number (int or string)
    :param episode_number: Episode number (int or string)
    :param language: Language code (default: "en-US")
    :return: dict with episode details or dict with error info
    """
    url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{season_number}/episode/{episode_number}"
    params = {
        "api_key": 'e92d7c9d19df047c576ee8724f174e07',
        "language": language
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # TMDb error handling
        if "status_code" in data and data["status_code"] != 1:
            return {"error": data.get("status_message", "Unknown error")}

        # Return structured episode info
        return {
            "title": data.get("name"),
            "air_date": data.get("air_date"),
            "episode_number": data.get("episode_number"),
            "season_number": data.get("season_number"),
            "overview": data.get("overview"),
            "vote_average": data.get("vote_average"),
            "vote_count": data.get("vote_count")
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Network or request error: {e}"}
    except ValueError:
        return {"error": "Error parsing JSON response."}       


def get_movie_info(movie_id):

    """
    Fetch movie details from TMDB API by movie ID.
    """
    API_KEY = "e92d7c9d19df047c576ee8724f174e07"  # Replace with your TMDB API key
    BASE_URL = "https://api.themoviedb.org/3"
    
    try:
        # Build the request URL
        url = f"{BASE_URL}/movie/{movie_id}"
        params = {
            "api_key": API_KEY,
            "language": "en-US"
        }

        # Send GET request
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses

        # Parse JSON response
        data = response.json()

        # Extract relevant fields safely
        movie_info = {
            "title": data.get("title"),
            "tagline": data.get("tagline"),
            "release_date": data.get("release_date"),
            "runtime": data.get("runtime"),
            "genres": [g["name"] for g in data.get("genres", [])],
            "overview": data.get("overview"),
            "poster_url": f"https://image.tmdb.org/t/p/w500{data['poster_path']}" if data.get("poster_path") else None
        }

        return movie_info

    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
    except ValueError:
        print("Error parsing JSON response.")
    except Exception as e:
        print(f"Unexpected error: {e}")

    return None

    
def get_first_english_backdrop(show_title) -> str:
    
    """
    Fetch the first English backdrop URL for a TV Show or Movie from TMDB.

    Args:
        show_title : The title of the TV Show or Movie.

    Returns:
        str: Full URL of the first English backdrop, or None if not found.
    """
    
    api_key = "e92d7c9d19df047c576ee8724f174e07"
    
    # establish if title is a TV Show or Movie
    tmdb_id, tmdb_type = search_tmdb('tv', show_title) # try to get tmdb_id for TV Show
    if tmdb_id == None:
        tmdb_id, tmdb_type = search_tmdb('movie', show_title)  # if not found try to get tmdb_id for Movie
        if tmdb_id == None: # no TV Show or Movie with title
            return None         
    
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("API key must be a non-empty string.")
        
    if tmdb_type == 'tvshow':
        endpoint_type = 'tv'
    else:
        endpoint_type = 'movie'        

    base_url = "https://api.themoviedb.org/3"
    endpoint = f"{base_url}/{endpoint_type}/{tmdb_id}/images"    
    params = {"api_key": api_key}

    try:
        response = requests.get(endpoint, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching data from TMDB: {e}")
        return None

    data = response.json()

    # Filter backdrops with English text
    backdrops = data.get("backdrops", [])
    english_backdrops = [
        b for b in backdrops if b.get("iso_639_1") == "en"
    ]

    if not english_backdrops:
        return None

    # TMDB image base URL (w1280 is a good size for backdrops)
    image_base = "https://image.tmdb.org/t/p/w1280"
    return image_base + english_backdrops[0]["file_path"]
     
# BBC-010: END functions to get data from the TMDb


# BBC-010: START def of CheckAutoplay_ListWatching and AddMenuEntry_ListWatching
def CheckAutoplay_ListWatching(showtitle, episode_title, season, episode, episode_fanart, name, url, iconimage, description, aired=None, resume_time="", total_time="", context_mnu=None):
    ADDON = xbmcaddon.Addon(id='plugin.video.iplayerwww')
    if ADDON.getSetting('streams_autoplay') == 'true':
        mode = 202
    else:
        mode = 122
    AddMenuEntry_ListWatching(showtitle, episode_title, season, episode, episode_fanart, name, url, mode, iconimage, description, '', aired=aired,
                 resume_time=resume_time, total_time=total_time, context_mnu=context_mnu)


def AddMenuEntry_ListWatching(show_title, episode_title, season, episode, episode_fanart, name, url, mode, iconimage, description='', subtitles_url='', aired=None, resolution=None,
                 resume_time='', total_time='', episode_id='', stream_id='', context_mnu=None, replay_chan_id=''):
    
    """Adds a new line to the Kodi list of playables.
    It is used in multiple ways in the plugin, which are distinguished by modes.
    """

    from .ipwww_common import utf8_quote_plus
        
    # START get data from TMDb
    tmdb_id, tmdb_type = search_tmdb('tv', show_title) # try to get tmdb_id for tvshow
    if tmdb_id == None:
        tmdb_id, tmdb_type = search_tmdb('movie', show_title)  # if not found try to get tmdb_id for tvshow
        if tmdb_id == None:
            description = "Movie: No plot information available."        
        else: 
            movie_info = get_movie_info(tmdb_id) # get plot for movie using tmdb_id          
    else: # we have tvshow tmdb_id              
        episode_info = get_episode_info(tmdb_id, int(season), int(episode))  # get plot for tvshow using tmdb_id     
    # END get data from TMDb
        
    if not iconimage:
        # BBC-001: Use iPlayer artwork 
        # iconimage="DefaultFolder.png"
        iconimage=fanartpath
    listitem_url = ''.join((
        sys.argv[0],
        "?url=", utf8_quote_plus(url),
        "&mode=", str(mode),
        "&name=", utf8_quote_plus(name),
        "&iconimage=", utf8_quote_plus(iconimage),
        "&description=", utf8_quote_plus(description),
        "&subtitles_url=", utf8_quote_plus(subtitles_url),
        "&episode_id=", utf8_quote_plus(episode_id),
        "&stream_id=", utf8_quote_plus(stream_id),
        "&resume_time=", resume_time,
        "&total_time=", total_time,
        "&replay_chan_id=", replay_chan_id))
    if mode in (101,203,113,213):
        listitem_url = listitem_url + "&time=" + str(time.time())
    if aired:
        ymd = aired.split('-')
        date_string = ymd[2] + '/' + ymd[1] + '/' + ymd[0]
    else:
        date_string = ""

    # Modes 201-299 will create a new playable line, otherwise create a new directory line.
    if mode in (201, 202, 203, 204, 205, 211, 212, 213, 214):
        isFolder = False
    # Mode 119 is not a folder, but it is also not a playable.
    elif mode == 119:
        isFolder = False
    else:
        isFolder = True

    listitem = xbmcgui.ListItem(label=name, label2=description)

    info_tag = listitem.getVideoInfoTag()
    
    listitem.setArt({'icon':'DefaultFolder.png', 'thumb':iconimage})
    listitem.setArt({'fanart': ''})
    
    if tmdb_type == 'tvshow':
        info_tag.setTvShowTitle(show_title)
        info_tag.setSeason(int(season))
        info_tag.setEpisode(int(episode))
        info_tag.setTitle(episode_title)
        info_tag.setPlot(episode_info['overview'])
        info_tag.setPlotOutline(episode_info['overview'])
        info_tag.setPremiered(episode_info['air_date'])
        info_tag.setMediaType("episode")
        info_tag.setDuration(int(total_time)) 
        
    elif tmdb_type == 'movie':
        info_tag.setTitle(show_title)
        info_tag.setPlot(movie_info['overview'])
        info_tag.setPlotOutline(movie_info['overview'])
        info_tag.setPremiered(movie_info['release_date'])
        info_tag.setTagLine(movie_info['tagline'])
        info_tag.setMediaType("movie")
        info_tag.setDuration(int(total_time))
        #listitem.setArt({'fanart': iconimage}) # don't know why this is needed
          
    else:
        info_tag.setTitle(name)
        info_tag.setPlot(description)
        info_tag.setPlotOutline(description)
        info_tag.setMediaType("video") 
        info_tag.setDuration(int(total_time))    
        if aired:
            info_tag.setPremiered(aired)
            info_tag.setDate(date_string)      

    if resume_time:
        info_tag.setResumePoint(float(resume_time), float(total_time))

    if context_mnu:
        listitem.addContextMenuItems(context_mnu)

    video_streaminfo = {'codec': 'h264'}
    if not isFolder:
        info_tag.setPath(url)
        listitem.setProperty('inputstream', 'inputstream.adaptive')
        listitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')

    # Mode 119 is not a folder, but it is also not a playable.
    if mode == 119:
        listitem.setProperty("IsPlayable", 'false')
    else:
        listitem.setProperty("IsPlayable", str(not isFolder).lower())
    listitem.setProperty("IsFolder", str(isFolder).lower())
    listitem.setProperty("Property(Addon.Name)", "iPlayer WWW")
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
                                url=listitem_url, listitem=listitem, isFolder=isFolder)

    return True     
# BBC-010: END def of CheckAutoplay_ListWatching and AddMenuEntry_ListWatching
